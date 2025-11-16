import requests as rq
from .plots import Plot_d 
from django.db.models import Count, Q
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

@login_required
def plots(request, id):
    plots = Plot_d(url="http://localhost:8000/plots_data/", id = id)    
    avg_temp = plots.make_avg_temp_plot()
    roza = plots.make_roza()
    return render(request, "devices/plot.html", {"avg_temp":avg_temp, "roza":roza})


@login_required
def get_plots(request):
    # devices = Device.objects.annotate(num_of_rows=Count("data")).filter(owner_id = request.user.id).filter(data__isnull = False)
    devices = Device.objects.all().annotate(num=Count("data")).filter(owner_id = request.user.id)

    return render(request, 'devices/get_plots.html', {"devices":devices})
