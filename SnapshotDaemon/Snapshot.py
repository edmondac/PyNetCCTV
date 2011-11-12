import ConfigParser
import logging
import logging.handlers
from PyNetCCTVDjangoManager.models import Camera as DjangoCamera
from PyNetCCTVDjangoManager.models import Snapshot as DjangoSnapshot
from django.core.files import File
import urllib
import threading
import time
import signal
import os
import sys
import subprocess
from PIL import Image
from cStringIO import StringIO
from django.core.files.base import ContentFile

# Load the configuration
config = ConfigParser.SafeConfigParser()
config.read("daemon.conf")
debug = False
if config.get("main", "debug").lower() == "true":
    debug = True
logfile = config.get("main", "logfile")
lockfile = config.get("main", "lockfile")
df_threshold = config.get("main", "diskusage")

# Set up logging
logger = logging.getLogger('pynetcctv')
hdlr = logging.handlers.RotatingFileHandler(logfile,
                                            maxBytes=10000000,
                                            backupCount=5)
formatter = logging.Formatter('%(asctime)s [%(process)d] [%(threadName)s] %(levelname)s %(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
if debug:
    logger.setLevel(logging.DEBUG)

# Classes and functions

class BaseThread(threading.Thread):
    stop = False


class HousekeepingThread(BaseThread):
    def __init__(self, df_perc=df_threshold, sleep_time=60):
        self.df_perc = df_perc
        self.sleep_time = sleep_time
        self.last_mem_info = (0,0,0)
        self.mem_info = None
        super(HousekeepingThread, self).__init__()
        self.daemon = True
        self.name = "Housekeeping"

    def run(self):
        while super(HousekeepingThread, self).stop is False:
            self.check_disk()
            if debug:
                self.check_mem()
            time.sleep(self.sleep_time)
            
    def check_mem(self):
        #import gc
        #logger.debug(str(gc.collect()))
        
        def _check(x):
            return int(os.popen('ps -p %d -o %s | tail -1' %
                                (os.getpid(), x)).read())

        self.last_mem_info = self.mem_info
        self.mem_info = (_check("rss"),
                         _check("vsz"))

        if self.last_mem_info:
            diffs = [self.mem_info[i] - self.last_mem_info[i]
                     for i in range(2)]
            
            logger.debug("Memory info: Res: %s (%s%s) Vir: %s (%s%s)" \
                             % (self.mem_info[0],
                                "+" if diffs[0] >= 0 else "",
                                diffs[0],
                                self.mem_info[1],
                                "+" if diffs[1] >= 0 else "",
                                diffs[1]))

    def check_disk(self):
        #Find the filesystem with the snapshots
        #and check its disk usage

        #First, go through the records until we find one with an image file
        #(creation is not atomic, so some records may exist in an unfinished
        # state)
        for sn in DjangoSnapshot.objects.all():
            try:
                #There is a possibility that some database records
                #might exist without files
                f = sn.image.file
            except ValueError, e:
                if str(e) == "The 'image' attribute has no file associated with it.":
                    logger.debug("Snapshot record %s has no associated file." % (sn.id))
                    continue

                else:
                    raise

            #Now we've found the path, go and check it
            self.cleanup(os.path.dirname(f.name))
            break

    def cleanup(self, path):
        #Find out the disk usage, and clean up old files as needed
        perc = self.check_df(path)
        while perc > self.df_perc:
            #Loop round, deleting 50 files each time
            logger.info("Disk usage (%s) has passed threshold (%s). " \
                            "Old snapshots will be deleted." \
                            % (perc, self.df_perc))

            self.prune(50)
            perc = self.check_df(path)

    def prune(self, no_of_files):
        oldest = DjangoSnapshot.objects.all().order_by("timestamp")[:no_of_files]
        #We have to delete them one by one, so that the file-deletion
        #stuff is called. (QuerySet.delete skips this step).
        for snap in oldest:
            logger.debug("Deleting snapshot %s (%s)" % (snap.id, snap.timestamp))
            try:
                snap.delete()
            except:
                logger.error("Error deleting snapshot %s. Details follow:" % (snap.id,),
                             exc_info=True)

        logger.info("Deleted %s oldest snapshots" % (no_of_files))

        #import pdb; pdb.set_trace()

    def check_df(self, path):
        logger.debug("Checking disk space on %s filesystem" % (path,))
        df = subprocess.Popen(["df","."], 
                              stdout=subprocess.PIPE).communicate()[0]
        perc_full = df.split('\n')[1].split()[4]
        assert perc_full[-1] == "%", "Fatal error finding disk usage"
        logger.debug("Found percentage disk usage is %s (threshold is %s%%)" % (perc_full, self.df_perc))
        return int(perc_full[:-1])


class CameraThread(BaseThread):
    def __init__(self, django_camera):
        self.dj_cam = django_camera

        #Build the snapshot URL for this camera
        self.url = "http://%s" % (self.dj_cam.username,)
        self.url += ":%s" % (self.dj_cam.password,)
        self.url += "@%s/%s" % (self.dj_cam.hostname,
                                self.dj_cam.snapshot_url)

        super(CameraThread, self).__init__()
        self.daemon = True
        self.name = "Thread:%s" % (self.dj_cam.hostname,)

    def run(self):
        while super(CameraThread, self).stop is False:
            self.take_snapshot()
            time.sleep(self.dj_cam.interval)

    def take_snapshot(self):
        dj_sn = DjangoSnapshot()
        dj_sn.camera = self.dj_cam
        dj_sn.save()  # For the timestamp

        try:
            # Download the snapshot from the camera
            logger.debug("Downloading %s" % (self.url,))
            u_fh = urllib.urlopen(self.url)
            image_data = u_fh.read()
            u_fh.close()
        except:
            logger.warning("Non-fatal error taking snapshot",
                           exc_info=True)
        else:
            # Create the main image object
            dj_sn.image.save("%s_%s.jpg" % (self.dj_cam.name,
                                            dj_sn.timestamp),
                             ContentFile(image_data))
            
            # Create the thumbnail object
            image_f = StringIO(image_data)
            size = 128, 96
            im = Image.open(image_f)
            im.thumbnail(size)
            thumb_f = StringIO()
            im.save(thumb_f, "JPEG")
            dj_sn.thumb.save("%s_%s_thumb.jpg" % (self.dj_cam.name,
                                                  dj_sn.timestamp),
                             ContentFile(thumb_f.read()))
            
            image_f.close()
            thumb_f.close()

            # Don't need dj_sn.save() as the
            # save calls to the images save the object too
            logger.debug("Snapshot taken: %s" % (dj_sn,))


# Signal handling...
def sig_handler(signum, frame):
    logger.info("Caught signal %s - terminating" % (signum,))
    BaseThread.stop = True

signal.signal(signal.SIGTERM, sig_handler)
signal.signal(signal.SIGINT, sig_handler)

# The main process...
class Daemon:
    def __init__(self, stop=False):
        print "\n\nSee %s for info\n" % (logfile,)
        if not self.lock():
            #Bug out
            print "Couldn't get the lock - aborting"
            return

        if stop:
            return

        self.threads = []
        for dc in DjangoCamera.objects.all():
            self.threads.append(CameraThread(dc))

        logger.info("Loaded %d cameras" % len(self.threads))

        logger.debug("Initialising housekeeping thread")

        self.threads.append(HousekeepingThread())

        logger.debug("Starting threads")

        for t in self.threads:
            t.start()

        logger.debug("Waiting for stop signal")

        while BaseThread.stop is False:
            time.sleep(1)

        # The threads are daemonized, so they'll exit when we do
        self.unlock()
        logger.debug("All done")

    def lock(self, force=True):
        ok = False
        if os.path.exists(lockfile):
            pid = open(lockfile).read().strip()
            if pid:
                #There is a pid in the lockfile
                if os.path.exists("/proc/%s" % (pid,)):
                    #The process with id pid is running
                    if force:
                        logger.info("Killing old process %s" % (pid,))
                        try:
                            os.kill(int(pid), signal.SIGTERM)
                            i = 0
                            while os.path.exists("/proc/%s" % (pid,)):
                                #We wait until the old process dies
                                #(otherwise we race for the lockfile)
                                time.sleep(1)
                                i += 1
                                if i > 30:
                                    logger.warning("Waited 30s for the old process to die and it didn't")
                                    break

                            if os.path.exists("/proc/%s" % (pid,)):
                                logger.warning("Sending SIGKILL to old process %s" % (pid,))
                                os.kill(int(pid), signal.SIGKILL)

                            ok = True
                        except:
                            logger.error("Error trying to kill process %s" % (pid),
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
                open(lockfile, 'w').write(str(os.getpid()))
                logger.debug("Lockfile %s locked" % (lockfile,))
            except:
                logger.error("Error locking file %s" % (lockfile,),
                             exc_info=True)
                ok = False

        return ok

    def unlock(self):
        #Clear the lock file
        open(lockfile, 'w').write("")
        logger.debug("Lockfile %s unlocked" % (lockfile,))

def test():
    for dc in DjangoCamera.objects.all():
        t = CameraThread(dc)
        t.take_snapshot()

if __name__ == "__main__":
    if sys.argv.count("test"):
        test()
    elif sys.argv.count("stop"):
        Daemon(stop=True)
    else:
        Daemon()
