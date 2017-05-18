import os
import shutil
import sqlite3
import tempfile
from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from .forms import UploadFileForm
from datetime import datetime

@csrf_exempt
def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            handle_uploaded_file(request.FILES['file'], form.data["project"])
            return HttpResponseRedirect('/upload/')
    else:
        form = UploadFileForm()
    return render(request, 'upload.html', {'form': form})

def handle_uploaded_file(f, project):

    LATEST_DB_PATH = os.path.join(settings.DB_UPLOAD_BASE_DIR, project, "latest")
    HISTORICAL_DB_PATH = os.path.join(settings.DB_UPLOAD_BASE_DIR, project, "historical")

    try:
        os.makedirs(LATEST_DB_PATH)
    except OSError as e:
        pass

    try:
        os.makedirs(HISTORICAL_DB_PATH)
    except OSError as e:
        pass

    path = tempfile.mktemp(prefix="dbupload-", suffix=".sqlite3")    
    with open(path, 'wb+') as destination:
        for chunk in f.chunks():
            destination.write(chunk)
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM kolibriauth_facilitydataset")
    dataset_id = cursor.fetchone()[0]
    latest_dest_path = os.path.join(LATEST_DB_PATH, "{}.sqlite3".format(dataset_id))
    historical_dest_path = os.path.join(HISTORICAL_DB_PATH, "{}-{}.sqlite3".format(dataset_id, datetime.now().isoformat()))
    shutil.copyfile(path, latest_dest_path)
    shutil.copyfile(path, historical_dest_path)
