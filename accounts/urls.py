


from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path('login/', auth_views.LoginView.as_view(template_name='write/login.html'),name='login'),
    path('logout/',auth_views.LogoutView.as_view(), name='logout'),
    path('settings/change_password/', auth_views.PasswordChangeView.as_view(template_name='write/change_password.html'),name='password_change'),
    path('settings/change_password/done',auth_views.PasswordChangeDoneView.as_view(template_name='write/change_password_done.html'),name='password_change_done'),
    path('account/', views.UserUpdateView.as_view(), name ='my_account'),

    
]
