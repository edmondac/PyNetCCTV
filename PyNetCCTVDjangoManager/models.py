from django.db import models

class Camera(models.Model):
    name = models.CharField(max_length=100)
    hostname = models.CharField(max_length=100)
    username = models.CharField(max_length=100)
    password = models.CharField(max_length=100,null=True,blank=True)
    stream_url = models.CharField(max_length=100)
    snapshot_url = models.CharField(max_length=100)
    interval = models.DecimalField("Interval between snapshots (secs)", max_digits=10, decimal_places=1, default=0.5)
    
    def __unicode__(self):
        return "Camera: %s" %self.name

class Snapshot(models.Model):
    camera = models.ForeignKey(Camera)
    timestamp = models.DateTimeField(auto_now_add=True)
    image = models.ImageField(upload_to='snapshots')
    thumb = models.ImageField(upload_to='snapshots')
    
    def delete(self):
        #We want to try to delete the image file
        #on disk here too, since it's likely that
        #the delete is happening to save disk space.

        #WARNING: this method is not called if the
        #delete is done via the admin interface's
        #'delete selected objects' call. So the image
        #on disk will not be deleted in that case

        try:
            self.image.delete()
            self.thumb.delete()
        finally:
            super(Snapshot, self).delete()

    def __unicode__(self):
        return "Snapshot: %s => %s" %(self.camera, self.timestamp)

