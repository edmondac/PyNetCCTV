from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext 
from PyNetCCTVDjangoManager.models import Camera, Snapshot

import math

def index(request):
    n_cams = Camera.objects.count()
    n_snaps = Snapshot.objects.count()
    return render_to_response('cctv/index.html', {'cameras':n_cams, 'snapshots': n_snaps}, context_instance = RequestContext(request))

def montage(request):
    cams = Camera.objects.all()
    n_cams = len(cams)
    sq = math.sqrt(n_cams)
    cols = math.ceil(sq)
    
    matrix = []
    row = []
    i = 0
    for c in cams:
        i += 1
        row.append(c)
        if i == cols:
            matrix.append(row)
            row = []
            i = 0

    if row:
        matrix.append(row)

    image_width = "%s%%" %(100.0/cols)

    return render_to_response('cctv/montage.html', {'matrix':matrix, 'image_width':image_width}, context_instance = RequestContext(request))

def snapshots(request):
    n_snaps = Snapshot.objects.count()
    return render_to_response('cctv/snapshots.html', {'snapshots': n_snaps}, context_instance = RequestContext(request))

