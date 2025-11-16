from .models import Data
from rest_framework import serializers


class DataSerializer(serializers.HyperlinkedModelSerializer):
    class Meta:
        model = Data
        fields = [ "device_id","date", "temp", "pressure", "humidity", "wind_speed","wind_direction", "uv"]
