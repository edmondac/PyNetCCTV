######################################################################
#Set up logging
import logging
logger = logging.getLogger('pynetcctv')
hdlr = logging.FileHandler('daemon.log')
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.INFO)

######################################################################
from PyNetCCTVDjangoManager.models import Camera as DjangoCamera
from PyNetCCTVDjangoManager.models import Snapshot as DjangoSnapshot
from django.core.files import File
import urllib

class Camera:
    def __init__(self, django_camera):
        self.dj_cam = django_camera

        #Build the snapshot URL for this camera
        self.url = "http://%s" %self.dj_cam.username
        self.url += ":%s" %self.dj_cam.password
        self.url += "@%s/%s" %(self.dj_cam.hostname, self.dj_cam.snapshot_url)

        self.take_snapshot()


    def take_snapshot(self):
        dj_sn = DjangoSnapshot()
        dj_sn.camera = self.dj_cam
        dj_sn.save() #For the timestamp

        #Download the snapshot from the camera
        result = urllib.urlretrieve(self.url)
        f_obj = File(open(result[0]))
        dj_sn.image.save("%s_%s.jpg" %(self.dj_cam.name, dj_sn.timestamp), f_obj)
        #dj_sn.save() #Not needed as the previous line saves the object too
        logger.info("Snapshot taken: %s" %dj_sn)

class Daemon:
    def __init__(self):
        self.cameras = []
        for dc in DjangoCamera.objects.all():
            self.cameras.append(Camera(dc))

        logger.info("Loaded %d cameras" %len(self.cameras))


if __name__ == "__main__":
    Daemon()
