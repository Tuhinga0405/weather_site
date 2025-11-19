from django.urls import path
from . import views
from django.contrib.auth.views import (
    LogoutView, 
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView
) 

urlpatterns = [
    path('account/registration/', views.registration, name='registration'),    
    path('', views.home_page, name="home_page"),
    path('account/sign_in/',views.sign_in, name='sign_in'),
    path('account/logout/', views.logout_view, name='logout_view'),
    path('account/password-reset', PasswordResetView.as_view(template_name='account/password-reset.html'), name='password-reset'),
    path('account/password-reset/done', PasswordResetDoneView.as_view(template_name='account/password_reset_done.html'),name='password_reset_done'), 
    path('account/password-reset/confirm/<uidb64>/<token>', PasswordResetConfirmView.as_view(template_name='account/password_reset_confirm.html'), name='password_reset_confirm'),
    path('account/password-reset/complete', PasswordResetCompleteView.as_view(template_name='account/password_reset_complete.html'), name='password_reset_complete'),
]
