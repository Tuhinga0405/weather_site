from django.urls import path
from rest_framework.routers import format_suffix_patterns
from . import views

urlpatterns = [
    path('data_all/', views.data_all, name='data_all'),
    path('add_device', views.add_device, name='add_device'),
    path('get_data/<int:id>', views.DataList.as_view(), name = 'get_data'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
