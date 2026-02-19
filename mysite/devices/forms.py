from django import forms
from .models import Device
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.core import validators
from django.forms import ModelForm


class DeviceForm(ModelForm):
    class Meta:
        model = Device
        fields = ["id", "nickname"]
    # id = forms.IntegerField(label="ID устройства")

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


    def clean_nickname(self):
        nickname = self.cleaned_data['nickname']

        devices = Device.objects.all()

        matching_nicknames=list(filter(lambda x: x.nickname == nickname,
                                       devices))

        if matching_nicknames:
            raise ValidationError(
                _("Устройство с никнеймом: %(nickname)s уже существует"),
                code="invalid",
                params={"nickname": nickname},
            )

        return nickname

class DeviceUpdateForm(DeviceForm):
    class Meta(DeviceForm.Meta):
        fields = ["nickname"]

class DeviceCreateForm(DeviceForm):
    class Meta(DeviceForm.Meta):
        fields = ["id","nickname"]
