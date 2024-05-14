from django.shortcuts import render, redirect, reverse
from django.views.generic import View
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.conf import settings
from django_redis import get_redis_connection
# from django.urls import  reverse

from user.models import User, Address
from order.models import OrderInfo, OrderGoods
from itsdangerous import SignatureExpired
from itsdangerous.url_safe import URLSafeTimedSerializer as Serializer
from celery_tasks.tasks import send_register_active_email
from goods.models import GoodsSKU
from utils.mixin import LoginRequiredMixin
import re

# Create your views here.


class RegisterView(View):
    """注册视图类"""

    def get(self, request):
        return render(request, "register.html")

    def post(self, request):
        """进行注册处理"""
        username = request.POST.get("user_name")
        password = request.POST.get("pwd")
        email = request.POST.get("email")
        allow = request.POST.get("allow")
        # 数据校验
        if not all([username, password, email]):
            # 数据不完整
            return render(request, "register.html", {"errmsg": "用户信息不完整"})

        if not re.match(r"^[a-zA-Z0-9_-]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$", email):
            # 邮箱格式不正确
            return render(request, "register.html", {"errmsg": "邮箱格式错误"})

        if allow != "on":
            # 是否同意协议
            return render(request, "register.html", {"errmsg": "请同意协议"})

        # 校验用户名是否重复
        try:
            User.objects.get(username=username)
        except User.DoesNotExist:
            User.username = None

        if User.username:
            # 用户名存在
            return render(request, "register.html", {"errmsg": "用户名已存在"})

        # 进行业务处理：进行注册，django内置的用户认证系统
        user = User.objects.create_user(username, email, password)
        user.is_active = 0
        user.save()

        # 发送激活邮件，包含激活链接 /user/active/id
        # 加密用户的身份信息,生成激活token
        serializer = Serializer(settings.SECRET_KEY)
        info = {'confirm': user.id}
        token = serializer.dumps(info)
        # token = token.decode()

        # 异步发送邮件
        send_register_active_email.delay(email, username, token)

        # 跳转到首页
        return redirect(reverse("goods:index"))


class ActiveView(View):
    """用户激活"""

    def get(self, request, token):
        # 解密参数
        serializer = Serializer(settings.SECRET_KEY)
        try:
            info = serializer.loads(token)
            user_id = info['confirm']
            # print(user_id)

            # 根据id获取用户id
            user = User.objects.get(id=user_id)
            user.is_active = 1
            user.save()
            # 跳转登录
            return redirect(reverse("user:login"))
        except SignatureExpired as e:
            # 激活链接已过期
            return HttpResponse("激活链接已过期")


# user/login
class LoginView(View):
    """登录"""
    def get(self, request):
        # 显示登录页面
        # 判断是否记住用户名
        if "username" in request.COOKIES:
            username = request.COOKIES.get("username")
            checked = "checked"
        else:
            username = ""
            checked = ""
        return render(request, "login.html", {"username": username, "checked": checked})


    def post(self, request):
        """登录校验"""

        # 接收数据
        username = request.POST.get("username")
        password = request.POST.get("pwd")

        # 这里all是函数,用于判断可迭代对象是否为空，校验数据
        if not all([username, password]):
            return render(request, "login.html", {"errmsg": "用户名或密码不完整"})

        # 业务处理
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                # 记录登录状态 session
                login(request, user)

                # 获取登陆后要跳转的地址，默认跳转首页
                next_url = request.POST.get("next", reverse('goods:index'))
                # 利用get函数。若有next，则获取,得到的是需要跳转的页面，不是首页，如/user,/user/order,/user/cart，若无，则直接跳到首页
                response = redirect(next_url)  # HttpResponse对象

                # 判断是否记住用户名
                remember = request.POST.get("remember")
                if remember == "on":
                    response.set_cookie("username", username, max_age=24 * 3600)
                else:
                    response.delete_cookie(username)
                return response
                # 跳转到首页

            else:
                # 用户未激活
                return render(request, 'login.html', {'errmsg': "用户未激活"})
        else:
            return render(request, 'login.html', {'errmsg': "用户名或密码错误"})


# user/logout
class LogoutView(View):
    """退出登录"""
    def get(self, request):
        # 清除用户session
        logout(request)
        return redirect(reverse("goods:index"))


# /user
class UserInfoView(LoginRequiredMixin, View):
    """用户中心信息页"""
    def get(self, request):
        """显示"""
        # request.user.is_authenticated是django自带的一个认证实例
        # django除了可以给模板文件传递模板变量外，还会把request.user实例也传给模板文件
        # 如果用户未登录，则传is_anonymous实例，这个实例表示False
        # 如果用户登录，则传is_authenticated实例，这个实例表示True
        # 获取用户个人信息
        user = request.user
        address = Address.objects.get_default_address(user)
        # 获取浏览记录
        con = get_redis_connection("default")  # con为StrictRedis对象
        history_key = "history_%d" % user.id
        # 获取最新五条浏览记录
        sku_ids = con.lrange(history_key, 0, 4)
        goods_li = []
        # 根据序号从数据库中读取数据
        for id in sku_ids:
            goods = GoodsSKU.objects.get(id=id)
            goods_li.append(goods)
        print(goods_li)
        # 组织上下文
        context = {
            "page": "user",
            "address": address,
            "goods_li": goods_li
        }

        return render(request, 'user_center_info.html', context)


# /user/order
class UserOrderView(LoginRequiredMixin, View):
    """用户中心订单页"""

    def get(self, request, page):
        """显示"""
        # 获取用户的订单信息
        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by("-create_time")

        # 便利获取订单商品的信息
        for order in orders:
            # 根据order_id查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 便利order_skus计算商品的小计
            for order_sku in order_skus:
                # 计算小计
                amount = order_sku.count * order_sku.price
                # 动态给order_sku增加属性amount，保存订单商品的小计
                order_sku.amount = amount
            # 保存订单状态标题
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 动态给order增加属性，保存订单商品的信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 1)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception as e:
            page = 1

        if page > paginator.num_pages:
            page = 1

        # 获取第page页的Page实例对象
        order_page = paginator.page(page)

        # todo: 进行页码的控制，页面上最多显示5个页码
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页，显示1-5页
        # 3.如果当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页的后2页
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page <= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        print(order_page)
        # 组织上下文
        context = {"order_page": order_page, "pages": pages, "page": "order"}

        return render(request, "user_center_order.html", context)


# /user/address
class AddressView(LoginRequiredMixin, View):
    """用户中心地址页"""
    def get(self, request):
        user = request.user
        address = Address.objects.get_default_address(user)

        return render(request, 'user_center_site.html', {"page": "address", "address": address})

    def post(self, request):
        """接收数据"""
        receiver = request.POST.get("receiver")
        addr = request.POST.get("addr")
        zip_code = request.POST.get("zip-code")
        phone = request.POST.get("phone")

        # 校验数据
        if not all([receiver, addr, phone]):
            return render(request, "user_center_site.html", {"errmsg":"输入数据为空"})

        # 号码格式是否匹配
        if not re.match(r"1[3,4,5,7,8]\d{9}$", phone):
            return render(request, "user_center_site.html", {"errmsg":"手机格式不正确"})

        # 业务添加
        # django自带的用户认证，对象保存用户信息
        # 获取数据库的默认地址
        # try:
        #     address = Address.objects.get(user=user, is_default=True)
        # except Address.DoesNotExist:
        #     address = None
        user = request.user
        address = Address.objects.get_default_address(user)

        # 查看是否有默认地址
        if address:
            is_default = False
        else:
            is_default = True

        Address.objects.create(
            user=user,
            receiver=receiver,
            addr=addr,
            zip_code=zip_code,
            phone=phone,
            is_default=is_default
        )
        # 仅仅是多了一个空格，这django真的无语，空格卡这么死
        return redirect(reverse("user:address"))













