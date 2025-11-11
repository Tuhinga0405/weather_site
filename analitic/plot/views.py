from django.shortcuts import render
from django.http import request
import requests as rq
from rest_framework.response import Response
from rest_framework.views import APIView 
from .plot import make_dict_from_url 



class AvgTemp(APIView):

    def get(self, request, id, format=None):
        data = make_dict_from_url(f"http://localhost:9000/devices/get_data/{id}")
        return Response(data)
