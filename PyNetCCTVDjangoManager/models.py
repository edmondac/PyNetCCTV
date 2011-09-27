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
    
    def __unicode__(self):
        return "Snapshot: %s => %s" %(self.camera, self.timestamp)


##############
#FOR LATER
#
#from django.core.files import File
#result = urllib.urlretrieve(url)
#s = Snapshot()
#s.camera = ...
#s.image.save(a_filename, File(open(result[0])))

