from django.urls import path
from . import views

urlpatterns = [
    path('data_all/', views.data_all, name='data_all'),
    path('add_device', views.add_device, name='add_device'),
]