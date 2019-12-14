# !/usr/bin/env python3
# -*- coding: utf-8 -*-

from django.urls import path
from django.conf.urls import url
from . import views

urlpatterns = [
    path('index', views.index, name='index'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('getVerificationCode', views.get_verify_code, name='code'),
]