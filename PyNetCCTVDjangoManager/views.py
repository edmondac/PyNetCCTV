from PyNetCCTVDjangoManager.models import Camera, Snapshot
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
import math

def index(request):
    n_cams = Camera.objects.count()
    n_snaps = Snapshot.objects.count()
    return render_to_response('cctv/index.html', {'cameras':n_cams, 'snapshots': n_snaps}, context_instance=RequestContext(request))

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

    image_width = "%s%%" % (100.0 / cols)

    return render_to_response('cctv/montage.html',
                              {'matrix':matrix, 
                               'image_width':image_width}, 
                              context_instance=RequestContext(request))

def snapshot(request):
    snap = get_object_or_404(Snapshot, pk=request.GET.get('snap_id'))
    return render_to_response('cctv/snapshot.html',
                              {'snap':snap}, 
                              context_instance=RequestContext(request))

def snapshots(request):
    cams = Camera.objects.all()
    #NOTE: all() is lazy, so don't worry about scale problems here with pagination
    snaps = Snapshot.objects.all().order_by('-timestamp')
    number = request.GET.get('per_page',25)
    page = request.GET.get('page',1)
    
    try:
        number = int(number)
        page = int(page)
    except ValueError:
        number = 25
        page = 1
    
    paginator = Paginator(snaps, number)
    
    try:
        objects = paginator.page(page)
    except PageNotAnInteger:
        # If page is not an integer, deliver first page.
        objects = paginator.page(1)
    except EmptyPage:
        # If page is out of range (e.g. 9999), deliver last page of results.
        objects = paginator.page(paginator.num_pages)
    #n_snaps = p.count()

    return render_to_response('cctv/snapshots.html', 
                              {'cameras':cams,
                               'objects':objects,
                               'page':page}, 
                              context_instance=RequestContext(request))

