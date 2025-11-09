from django.urls import path
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('account/registration/', views.registration, name='registration'),    
    path('account/home_page/', views.home_page, name="home_page"),
    path('account/sign_in/',views.sign_in, name='sign_in'),
    path('account/logout/', views.logout_view, name='logout_view'),
    path('', views.main_page, name='main_page'),
]
