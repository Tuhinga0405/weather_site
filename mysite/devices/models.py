from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model() #Нужно, чтобы при замене на кастомную модель, все было ок

class Device(models.Model):
    id = models.PositiveBigIntegerField(primary_key=True)
    owner_id = models.ForeignKey(User, on_delete=models.CASCADE, null=True)

class Data(models.Model):
    device = models.ForeignKey(
            Device,
            on_delete=models.CASCADE,   # аналог ondelete="CASCADE"
            related_name="data"         # удобно для обратного доступа: device.data.all()
        )
    date = models.DateTimeField()
    temp = models.FloatField()
    pressure = models.FloatField()
    humidity = models.FloatField()
    wind_speed = models.FloatField(null=True)
    wind_direction = models.CharField(max_length=20, null=True)
    uv = models.FloatField()

