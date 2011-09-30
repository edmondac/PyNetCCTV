######################################################################
#Set up logging
import logging, logging.handlers
logger = logging.getLogger('pynetcctv')
logfile = "daemon.log"
hdlr = logging.handlers.RotatingFileHandler(logfile,maxBytes=100000,backupCount=5)
formatter = logging.Formatter('%(asctime)s [%(process)d] %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
#hdlr2 = logging.StreamHandler()
#logger.addHandler(hdlr2)
logger.setLevel(logging.DEBUG)

######################################################################
from PyNetCCTVDjangoManager.models import Camera as DjangoCamera
from PyNetCCTVDjangoManager.models import Snapshot as DjangoSnapshot
from django.core.files import File
import urllib
import threading
import time
import signal
import os, sys

class BaseThread(threading.Thread):
    stop = False

class CameraThread(BaseThread):
    def __init__(self, django_camera):
        self.dj_cam = django_camera

        #Build the snapshot URL for this camera
        self.url = "http://%s" %self.dj_cam.username
        self.url += ":%s" %self.dj_cam.password
        self.url += "@%s/%s" %(self.dj_cam.hostname,
                               self.dj_cam.snapshot_url)

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
            dj_sn.image.save("%s_%s.jpg" %(self.dj_cam.name,
                                           dj_sn.timestamp),
                             f_obj)
            #dj_sn.save() #Not needed as the previous line saves the object too
            logger.debug("Snapshot taken: %s" %dj_sn)
        except:
            logger.warning("Non-fatal error taking snapshot",
                           exc_info=True)

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
    lockfile = "daemon.lock"
    
    def __init__(self, stop=False):
        print "\n\nSee %s for info\n" %logfile
        if not self.lock():
            #Bug out
            print "Couldn't get the lock - aborting"
            return

        if stop:
            return
        
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

        self.unlock()
        logger.debug("All done")

    def lock(self, force=True):
        ok = False
        if os.path.exists(self.lockfile):
            pid = open(self.lockfile).read().strip()
            if pid:
                #There is a pid in the lockfile
                if os.path.exists("/proc/%s" %pid):
                    #The process with id pid is running
                    if force:
                        logger.info("Killing old process %s" %pid)
                        try:
                            os.kill(int(pid),signal.SIGTERM)
                            i = 0
                            while os.path.exists("/proc/%s" %pid):
                                #We wait until the old process dies
                                #(otherwise we race for the lockfile)
                                time.sleep(1)
                                i+=1
                                if i > 30:
                                    logger.warning("Waited 30s for the old process to die and it didn't")
                                    break

                            if os.path.exists("/proc/%s" %pid):
                                logger.warning("Sending SIGKILL to old process %s" %pid)
                                os.kill(int(pid),signal.SIGKILL)
                                
                            ok = True
                        except:
                            logger.error("Error trying to kill process %s" %(pid),
                                         exc_info=True)
                    else:
                        #We can't get the lock
                        logger.debug("Old process is still running")
                        pass
                else:
                    #The process isn't running, carry on
                    logger.debug("Old process isn't running - carry on")
                    ok = True
            else:
                #Lockfile is empty
                logger.debug("No readable pid in the lockfile - carry on")
                ok = True
        else:
            #No lockfile exists, carry on
            ok = True

        if ok:
            logger.debug("Trying to take the lockfile")
            try:
                open(self.lockfile,'w').write(str(os.getpid()))
                logger.debug("Lockfile %s locked" %self.lockfile)
            except:
                logger.error("Error locking file %s" %(self.lockfile),
                             exc_info=True)
                ok = False

        return ok

    def unlock(self):
        #Clear the lock file
        open(self.lockfile,'w').write("")
        logger.debug("Lockfile %s unlocked" %self.lockfile)

if __name__ == "__main__":
    if sys.argv.count("stop"):
        Daemon(stop=True)
    else:
        Daemon()
