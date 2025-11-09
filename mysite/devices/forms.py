from django import forms
from .models import Device
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

class DeviceForm(forms.Form):
    id = forms.IntegerField(label="ID устройства")

    def clean_id(self):
        device_id = self.cleaned_data['id']
        try:
            device = Device.objects.get(id=device_id)
        except Device.DoesNotExist:
            raise ValidationError(_("Устройство с id %(id)s не существует"),
                                  params={"id": device_id})

        if device.owner_id is not None:
            raise ValidationError(_("Устройство %(id)s уже занято"),
                                  params={"id": device_id})

        return device_id