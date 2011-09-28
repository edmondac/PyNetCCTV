from django.conf.urls.defaults import *

urlpatterns = patterns('PyNetCCTVDjangoManager.views',
    (r'^$', 'index'),
    (r'^index.html$', 'index'),
    (r'^montage.html$', 'montage'),
    (r'^snapshots.html$', 'snapshots'),
    )
