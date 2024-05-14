from celery import Celery
from django.conf import settings
from django.core.mail import send_mail
# from django.shortcuts import render
from django.template import loader, RequestContext
import os
from django_redis import get_redis_connection
# os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'DailyFresh.settings')
app = Celery("celery_tasks.tasks", broker="redis://127.0.0.1:6379/0")
# app = Celery("celery_tasks.tasks", broker="redis://127.0.0.1:6379/0")
from goods.models import *

# app = Celery("celery_tasks.tasks", broker="redis://127.0.0.1:6379/0")
@app.task
# 发送激活邮件
def send_register_active_email(to_email, username, token):
    """定义task功能"""
    subject = "天天生鲜欢迎信息"
    message = ""
    html_message = (
         "<h1>%s, 欢迎成为天天生鲜注册会员<h1>"
            "请点击下面链接激活账户<br/>"
            '<a href="http://127.0.0.1:8000/user/active/%s">'
            "http://127.0.0.1:8000/user/active/%s</a>" % (username, token, token)
    )
    sender = settings.EMAIL_FROM
    receiver = [to_email]
    send_mail(
        subject,
        message=message,
        from_email=sender,
        recipient_list=receiver,
        html_message=html_message,
    )


@app.task
def generate_static_index_html():
    types = GoodsType.objects.all()
    # 获取首页轮播商品信息
    goods_banners = IndexTypeGoodsBanner.objects.all().order_by("index")
    # 获取首页促销活动信息
    promotion_banners = IndexPromotionBanner.objects.all().order_by("index")
    # 获取首页分类商品展示信息
    for type in types:
        image_banners = IndexTypeGoodsBanner.objects.filter(
            type=type, display_type=1
        ).order_by("index")
        # 获取type种类首页分类商品的图片展示信息
        title_banners = IndexTypeGoodsBanner.objects.filter(
            type=type, display_type=0
        ).order_by("index")

        # 动态给type对象增加属性，分别保存首页分类商品的图片展示信息和文字展示信息
        type.image_banners = image_banners
        type.title_banners = title_banners
    context = {
       "types": types,
       "good_banners": goods_banners,
       "promotion_banners": promotion_banners,
    }
    temp = loader.get_template("static_index.html")
    static_index_html = temp.render(context)
    save_path = os.path.join(settings.BASE_DIR, "static\\index.html")
    with open(save_path, "w") as f:
        f.write(static_index_html)
