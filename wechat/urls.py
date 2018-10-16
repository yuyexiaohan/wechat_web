# coding=utf-8 
# Time : 2018/10/15 18:21 
# Author : achjiang
# File : urls.py
from django.urls import path
from . import views

app_name = 'wechat'
urlpatterns = [
    path('login/', views.login, name='login'),
    path('check-login/', views.check_login, name='check_login'),
    path('user/', views.wechat_user, name='wechat_user'),
    path('contact-list/', views.contact_ist, name='contact-list'),
    path('send-msg/', views.send_msg, name='send-msg'),
    path('get-msg/', views.get_msg, name='get-msg'),
]
