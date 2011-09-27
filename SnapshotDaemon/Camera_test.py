import unittest
import Snapshot
from ../PyNetCCTVDjangoManager.models import Camera as DjangoCamera

class CameraTestCase(unittest.TestCase):
    def setUp(self):
        self.dj_cam1 = DjangoCamera(name="test1",
                                    username="user",
                                    
