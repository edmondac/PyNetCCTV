from PyNetCCTVDjangoManager.models import Camera, Snapshot
from django.contrib import admin

class CameraAdmin(admin.ModelAdmin):
    list_display=["name","interval","snapshot_count"]

    def snapshot_count(self, cam):
        sn = Snapshot.objects.filter(camera=cam)
        return sn.count()

admin.site.register(Camera, CameraAdmin)
admin.site.register(Snapshot)
