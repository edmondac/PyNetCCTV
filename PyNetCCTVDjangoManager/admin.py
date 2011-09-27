from PyNetCCTVDjangoManager.models import Camera, Snapshot
from django.contrib import admin

class CameraAdmin(admin.ModelAdmin):
    list_display=["name","interval"]

admin.site.register(Camera, CameraAdmin)
admin.site.register(Snapshot)
