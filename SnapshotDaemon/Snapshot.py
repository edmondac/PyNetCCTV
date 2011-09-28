######################################################################
#Set up logging
import logging, logging.handlers
logger = logging.getLogger('pynetcctv')
hdlr = logging.handlers.RotatingFileHandler('daemon.log',maxBytes=100000,backupCount=5)
formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
hdlr2 = logging.StreamHandler()
logger.addHandler(hdlr2)
logger.setLevel(logging.DEBUG)

######################################################################
from PyNetCCTVDjangoManager.models import Camera as DjangoCamera
from PyNetCCTVDjangoManager.models import Snapshot as DjangoSnapshot
from django.core.files import File
import urllib
import threading
import time
import signal

class BaseThread(threading.Thread):
    stop = False

class CameraThread(BaseThread):
    def __init__(self, django_camera):
        self.dj_cam = django_camera

        #Build the snapshot URL for this camera
        self.url = "http://%s" %self.dj_cam.username
        self.url += ":%s" %self.dj_cam.password
        self.url += "@%s/%s" %(self.dj_cam.hostname, self.dj_cam.snapshot_url)

        super(BaseThread, self).__init__()

    def run(self):
        while BaseThread.stop is False:
            self.take_snapshot()
            time.sleep(self.dj_cam.interval)

    def take_snapshot(self):
        try:
            dj_sn = DjangoSnapshot()
            dj_sn.camera = self.dj_cam
            dj_sn.save() #For the timestamp

            #Download the snapshot from the camera
            result = urllib.urlretrieve(self.url)
            f_obj = File(open(result[0]))
            dj_sn.image.save("%s_%s.jpg" %(self.dj_cam.name, dj_sn.timestamp), f_obj)
            #dj_sn.save() #Not needed as the previous line saves the object too
            logger.debug("Snapshot taken: %s" %dj_sn)
        except:
            logger.warning("Non-fatal error taking snapshot",exc_info=True)

##########################################################################
#Signal handling...

def sig_handler(signum, frame):
    logger.info("Caught signal %s - terminating" %signum)
    BaseThread.stop = True    

signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGINT, sig_handler)

##########################################################################
#The main process...
class Daemon:
    def __init__(self):
        self.cameras = []
        for dc in DjangoCamera.objects.all():
            self.cameras.append(CameraThread(dc))

        logger.info("Loaded %d cameras" %len(self.cameras))

        logger.debug("Starting threads")

        for ct in self.cameras:
            ct.start()

        logger.debug("Waiting for stop signal")
    
        while BaseThread.stop is False:
            pass

        logger.debug("Joining threads")

        for ct in self.cameras:
            ct.join()

        logger.debug("All done")

if __name__ == "__main__":
    Daemon()
