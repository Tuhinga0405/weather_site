from django.shortcuts import render, redirect
from django.utils.dateparse import parse_date
from django.contrib.auth.decorators import login_required
from .models import Data, Device
from django.core.paginator import Paginator
from .forms import DeviceForm
# from rest_framework import permissions, viewsets 
from rest_framework.response import Response 
from rest_framework.decorators import api_view
from .serializers import DataSerializer


# class DataViewSet(viewsets.ModelViewSet):
    # queryset = Data.objects.values("device_id","date", "temp").filter(device_id=2)
    # serializer_class = DataSerializer
    # permission_classes = [permissions.IsAuthenticated]
        
@api_view(["GET", "POST"])
def get_data(request, id):
    queryset = Data.objects.all()
    if id:
        queryset = queryset.filter(device_id=id)
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
