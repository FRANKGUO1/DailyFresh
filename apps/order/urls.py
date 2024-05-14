"""DailyFresh URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.urls import path, include
from order.views import *

urlpatterns = [
    path("place", OrderPlaceView.as_view(), name="place"),  # 提交订单页面显示
    path("commit", OrderCommitView.as_view(), name="commit"),  # 订单创建
    path("check", CheckPayView.as_view(), name="check"),  # 查询支付订单结果
    path("comment/<int:order_id>", CommentView.as_view(), name="comment"),  # 查询支付订单结果
]
