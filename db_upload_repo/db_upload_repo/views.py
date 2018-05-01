import mimetypes
import os
import shutil
import sqlite3
import tempfile
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404, StreamingHttpResponse
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _
from django.views.decorators.csrf import csrf_exempt
from .forms import UploadFileForm
from datetime import datetime


def redirect_home(request):
    return HttpResponseRedirect('/')


def user_has_permission_for_project(user, project):
    if user.is_admin or user.project and user.project.project_code == project:
        return True


@login_required
def home_view(request):
    return render(request, 'home.html')


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


def project_root_db_path(project):
    return os.path.join(settings.DB_UPLOAD_BASE_DIR, project)


def latest_db_path(project):
    return os.path.join(settings.DB_UPLOAD_BASE_DIR, project, "latest")


def historical_db_path(project):
    return os.path.join(settings.DB_UPLOAD_BASE_DIR, project, "historical")


def handle_uploaded_file(f, project):

    LATEST_DB_PATH = latest_db_path(project)
    HISTORICAL_DB_PATH = historical_db_path(project)

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

    cursor.execute("SELECT id FROM morango_instanceidmodel WHERE current = 1")
    instance_id = cursor.fetchone()[0]

    latest_dest_path = os.path.join(LATEST_DB_PATH, "{}-{}.sqlite3".format(dataset_id, instance_id))
    historical_dest_path = os.path.join(HISTORICAL_DB_PATH, "{}-{}-{}.sqlite3".format(dataset_id, instance_id, datetime.now().isoformat()))
    shutil.copyfile(path, latest_dest_path)
    shutil.copyfile(path, historical_dest_path)


def get_files(directory, url_generator):
    """Returns list of files in directory"""
    if os.path.exists(directory):
        contents = os.listdir(directory)
        items = list()
        for content in contents:
            if os.path.isfile(os.path.join(directory, content)):
                stats = os.stat(os.path.join(directory, content))
                items.append({
                    "name": content,
                    "size": stats.st_size,
                    "last_modified": datetime.fromtimestamp(stats.st_mtime),
                    "url": url_generator(content),
                    "folder": False,
                })
        return items
    raise Http404('Directory does not exist')


def get_directories(directory, url_generator):
    """Returns list of directories in directory"""
    if os.path.exists(directory):
        contents = os.listdir(directory)
        items = list()
        for content in contents:
            if os.path.isdir(os.path.join(directory, content)):
                items.append({
                    "name": content,
                    "url": url_generator(content),
                    "folder": True,
                })
        return items
    raise Http404('Directory does not exist')


def show_directory_contents(request, directory_path, contents, title, back_url=None):
    if os.path.exists(directory_path):
        data = {
            'directory_files': contents,
            'title': title,
            'back_url': back_url or reverse('home'),
        }
        return render(request, 'directory.html', data)
    raise Http404('Directory does not exist')


def root_upload_view(request):
    if request.user.is_admin:
        directory_path = settings.DB_UPLOAD_BASE_DIR
        contents = get_directories(directory_path, lambda x: reverse('root_project', kwargs={'project': x}))
        return show_directory_contents(request, settings.DB_UPLOAD_BASE_DIR, contents, _('All projects'))
    return redirect_home(request)


def project_root_view(request, project):
    try:
        assert user_has_permission_for_project(request.user, project)
    except AssertionError:
        return redirect_home(request)
    contents = [
        {
            "name": _('Latest'),
            "url": reverse('project_latest', kwargs={'project': project}),
            "folder": True,
        },
        {
            "name": _('Historical'),
            "url": reverse('project_historical', kwargs={'project': project}),
            "folder": True,
        },
    ]
    return show_directory_contents(
        request,
        project_root_db_path(project),
        contents,
        _('All databases folders for project: %(project)s') % {'project': project},
        back_url=reverse('all_projects'),
    )


def project_latest_view(request, project):
    try:
        assert user_has_permission_for_project(request.user, project)
    except AssertionError:
        return redirect_home(request)
    directory_path = latest_db_path(project)
    contents = get_files(directory_path, lambda x: reverse('file_latest', kwargs={'project': project, 'file_name': x}))
    return show_directory_contents(
        request,
        directory_path,
        contents,
        _('Latest databases for project: %(project)s') % {'project': project},
        back_url=reverse('root_project', kwargs={'project': project}),
    )


def project_historical_view(request, project):
    try:
        assert user_has_permission_for_project(request.user, project)
    except AssertionError:
        return redirect_home(request)
    directory_path = historical_db_path(project)
    contents = get_files(directory_path, lambda x: reverse('file_historical', kwargs={'project': project, 'file_name': x}))
    return show_directory_contents(
        request,
        directory_path,
        contents,
        _('Historical databases for project: %(project)s') % {'project': project},
        back_url=reverse('root_project', kwargs={'project': project}),
    )


def read_file_chunkwise(file_obj):
    """Reads file in 32Kb chunks"""
    while True:
        data = file_obj.read(32768)
        if not data:
            break
        yield data


def download_file(request, file_path):
    #make sure that file exists within current directory
    if os.path.exists(file_path):
        file_name = os.path.basename(file_path)
        response = StreamingHttpResponse()
        response['Content-Disposition'] = 'attachment; filename=%s' % file_name
        # set the content-type by guessing from the filename
        response['Content-Type'] = mimetypes.guess_type(file_name)[0]
        # set the content-length to the file size
        response['Content-Length'] = os.path.getsize(file_path)
        file_obj = open(file_path)
        response.streaming_content = read_file_chunkwise(file_obj)
        return response
    else:
        raise Http404


def latest_download_view(request, project, file_name):
    try:
        assert user_has_permission_for_project(request.user, project)
    except AssertionError:
        return redirect_home(request)
    file_path = os.path.join(latest_db_path(project), file_name)
    return download_file(request, file_path)


def historical_download_view(request, project, file_name):
    try:
        assert user_has_permission_for_project(request.user, project)
    except AssertionError:
        return redirect_home(request)
    file_path = os.path.join(historical_db_path(project), file_name)
    return download_file(request, file_path)
