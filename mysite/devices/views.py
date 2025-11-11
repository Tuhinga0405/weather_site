import requests as rq
import plotly.io as pio
import plotly.express as px
from django.http import request
from django.shortcuts import render, redirect
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from rest_framework.views import APIView
from .models import Data, Device
from django.core.paginator import Paginator
from .forms import DeviceForm
from rest_framework import generics, mixins
from rest_framework.response import Response 
from .serializers import DataSerializer


# class DataViewSet(viewsets.ModelViewSet):
    # queryset = Data.objects.values("device_id","date", "temp").filter(device_id=2)
    # serializer_class = DataSerializer
    # permission_classes = [permissions.IsAuthenticated]
        
class DataList(APIView):

    def get(self, request, id, format=None):
        queryset = Data.objects.all().filter(device_id=id)
        serializer = DataSerializer(queryset, many=True)
        return Response(serializer.data)



@login_required
def data_all(request): 
    qs = Data.objects.filter(device__owner_id = request.user.id).select_related('device').order_by('-date')


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
def add_device(request):
    if request.method == 'POST':
        form = DeviceForm(request.POST)
        if form.is_valid():
            device_id = form.cleaned_data['id']
            device = Device.objects.get(id=device_id)
            device.owner_id = request.user  # можно присвоить сам объект User
            device.save()
            return redirect('home_page')
    else:
        form = DeviceForm()
    return render(request, 'devices/add_device.html', {'form': form})

def image(request):
    r = rq.get("http://localhost:8000/get_avg_temp/1")
    data = r.json() 
    months = data.keys()
    temps = data.values()

    fig = px.line(x=months, y=temps, title="Средняя температура по месяцам")
    plot_div = pio.to_html(fig, full_html=False)
    
    return render(request, "devices/plot.html", {"plot_div":plot_div})
