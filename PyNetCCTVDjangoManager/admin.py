from PyNetCCTVDjangoManager.models import Camera
from django.contrib import admin

class CameraAdmin(admin.ModelAdmin):
    list_display=["name","interval"]

admin.site.register(Camera, CameraAdmin)

