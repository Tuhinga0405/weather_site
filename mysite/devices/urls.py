from django.urls import path
from rest_framework.routers import format_suffix_patterns
from . import views
from rest_framework import routers


#router = routers.DefaultRouter()
#router.register(r"PlotsData", views.DataForPlots)

urlpatterns = [
    path('data_all/', views.data_all, name='data_all'),

    # в view.plots поступает device.id из html
    path('get_plots/<int:id>', views.plots, name='get_plots'),
    path('get_plots/', views.get_plots, name='get_plots'),

    path('devices/', views.devices, name='list_devices'),

    #form urls
    path('update_device/<int:pk>', views.DeviceUpdateView.as_view(), 
         name='list-devices-update'),
    path('create_device/', views.DeviceCreateView.as_view(),
         name = 'create_device'),
    path('delete_device/<int:pk>/delete/',
         views.DeviceDeleteView.as_view(),
         name='delete_device'),
    path('plots_data/<int:user_id>', views.PlotsData.as_view()),
    path('dashboard/', views.dashboard, name='dashboard')
]

urlpatterns = format_suffix_patterns(urlpatterns)
