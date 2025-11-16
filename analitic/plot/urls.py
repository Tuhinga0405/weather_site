from django.urls import path
from rest_framework.routers import format_suffix_patterns
from . import views

urlpatterns = [
    path('plots_data/<int:id>', views.PlostData.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
