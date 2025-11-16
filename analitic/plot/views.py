from django.shortcuts import render
from django.http import request
import requests as rq
from rest_framework.response import Response
from rest_framework.views import APIView 
from .plot import DeviceMeasurments 



class PlostData(APIView):

    def get(self, request, id, format=None):
        data=dict()

        raw_data = DeviceMeasurments(url=f"http://localhost:9000/devices/get_data/{id}")
        
        data["roza"] = raw_data.roza_vetrov() 
        data["avg_temp"] = raw_data.avg_temp()
        return Response(data)
