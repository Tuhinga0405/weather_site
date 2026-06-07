from django_currentuser.middleware import get_current_user, get_current_authenticated_user
from .plots import  Plots
from django.db.models import Count, Avg
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_date
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from .models import Data, Device
from django.core.paginator import Paginator
from .forms import DeviceForm, DeviceCreateForm, DeviceUpdateForm
from rest_framework.response import Response
from serivces.calculate_data import DataForPlots
from django.http import HttpResponse
from django.template.loader import render_to_string
from serivces.report_generator import ReportGenerator
from weasyprint import HTML, CSS
import io
import json


class PlotsData(APIView):

    def get(self, request, user_id):
        raw_data = DataForPlots(user_id=user_id)

        response_data = {
            "avg_temp": raw_data.avg_temp(),
            "avg_humidity": raw_data.avg_humidity(),
            "wind_rose": raw_data.wind_rose(),
        }
        return Response(response_data)

@login_required
def data_all(request): 
    qs = (Data.objects.filter(device__owner_id = request.user.id)
          .select_related('device').order_by('date'))

    # фильтр по устройству (по id)
    device_id = request.GET.get('device')
    if device_id:
        qs = qs.filter(device_id=device_id)

    # фильтр по дате "от"
    date_from = request.GET.get('from')
    if date_from:
        parsed_from = parse_date(date_from)
        if parsed_from:
            qs = qs.filter(date__date__gte=parsed_from)

    # фильтр по дате "до"
    date_to = request.GET.get('to')
    if date_to:
        parsed_to = parse_date(date_to)
        if parsed_to:
            qs = qs.filter(date__date__lte=parsed_to)


    paginator = Paginator(qs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'devices/devices_all.html', {
        'data': page_obj,
        'page_obj': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'paginator': paginator,
    })


@login_required
def plots(request, id):

    x = Plots(user_id=request.user.id)
    avg_temp = x.avg_temp_plot(device_id=id)
    roza = x.roza_vetrov_plot(device_id=id)
    return render(request, "devices/plot.html", 
                  {"avg_temp":avg_temp, "roza": roza})


@login_required
def get_plots(request):
    devices = (Device.objects.all().annotate(num=Count("data"))
               .filter(owner_id = request.user.id))

    return render(request, 'devices/get_plots.html', {"devices":devices})


@login_required
def dashboard(request):
    return render(request, 'devices/dashboard.html')

class DeviceUpdateView(UpdateView):
    model = Device
    form_class = DeviceUpdateForm
    template_name_suffix = "_update_form"
    success_url = reverse_lazy('list_devices')

class DeviceCreateView(CreateView):
    model = Device
    form_class = DeviceCreateForm
    template_name_suffix = "_create_form"
    success_url = reverse_lazy('list_devices')

class DeviceDeleteView(DeleteView):
    model = Device
    template_name_suffix = "_confirm_delete"
    success_url = reverse_lazy('list_devices')

@login_required
def devices(request): 
    devices = Device.objects.all().order_by('id')
    return render(request, 'devices/list_devices.html', {'devices': devices})


@login_required
def reports(request):
    """Страница генерации отчётов (HTML-версия)."""
    period = request.GET.get('period', 'week')
    
    if period not in ['day', 'week', 'month', 'year']:
        period = 'week'
    
    generator = ReportGenerator(request.user.id)
    context = generator.get_report_context(period)
    
    return render(request, 'devices/reports.html', context)

@login_required
def report_pdf(request):
    """Генерация PDF-отчёта."""
    period = request.GET.get('period', 'week')
    
    if period not in ['day', 'week', 'month', 'year']:
        period = 'week'
    
    generator = ReportGenerator(request.user.id)
    context = generator.get_report_context(period)
    
    # Рендер HTML-шаблона
    html_string = render_to_string('devices/report_pdf.html', context)
    
    # Генерация PDF с явными настройками
    pdf_file = io.BytesIO()
    
    HTML(
        string=html_string,
        base_url=request.build_absolute_uri('/')  # Важно для относительных путей
    ).write_pdf(
        pdf_file,
        stylesheets=[
            CSS(string='''
                @page {
                    size: A4;
                    margin: 2cm;
                }
                body {
                    font-family: "DejaVu Sans", sans-serif;
                }
            ''')
        ],
        optimize_size=('fonts', 'images'),  # Оптимизация размера файла
        zoom=1.0  # Масштабирование
    )
    
    pdf_file.seek(0)
    
    response = HttpResponse(pdf_file, content_type='application/pdf')
    filename = f"weather_report_{period}_{context['end_date'].replace('.', '-')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response