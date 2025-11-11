from django.urls import path
from rest_framework.routers import format_suffix_patterns
from . import views

urlpatterns = [
    path('get_avg_temp/<int:id>', views.AvgTemp.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
