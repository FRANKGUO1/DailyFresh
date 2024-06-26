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
from django.contrib import admin
from django.urls import path, re_path, include
from user.views import RegisterView, ActiveView, LoginView, UserInfoView, UserOrderView, AddressView, LogoutView

urlpatterns = [
    path("register", RegisterView.as_view(), name="register"),
    re_path("active/(?P<token>.*)$", ActiveView.as_view(), name="active"),
    path("login", LoginView.as_view(), name="login"),
    path("logout", LogoutView.as_view(), name="logout"),
    path("", UserInfoView.as_view(), name="user"),
    path("order/<int:page>", UserOrderView.as_view(), name="order"),
    path("address", AddressView.as_view(), name="address"),
]
