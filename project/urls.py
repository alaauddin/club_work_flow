"""
URL configuration for project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.urls import path, include
from app1 import admin_views

urlpatterns = [
    path('admin/', admin.site.urls),
    # Admin detail views
    path('admin/auth/user/<int:pk>/detail/', admin_views.user_detail_view, name='admin:user_detail_view'),
    path('admin/auth/user/list/', admin_views.user_list_view, name='admin:user_list_view'),
    path('admin/app1/section/<int:pk>/detail/', admin_views.section_detail_view, name='admin:section_detail_view'),
    path('admin/app1/section/list/', admin_views.section_list_view, name='admin:section_list_view'),
    path('admin/app1/serviceprovider/<int:pk>/detail/', admin_views.serviceprovider_detail_view, name='admin:serviceprovider_detail_view'),
    path('admin/app1/serviceprovider/list/', admin_views.serviceprovider_list_view, name='admin:serviceprovider_list_view'),
    path('', include('app1.urls')),
    path('accounts/', include('accounts.urls')),
]
