from django.conf.urls import url
from django.conf.urls import include
from django.contrib import admin
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url(r'^accounts/logout_login/',
        auth_views.logout_then_login,
        name='logout_then_login'),
    url(r'^$', views.home_view, name='home'),
    url(r'^admin/', admin.site.urls),
    url(r'^upload/', views.upload_file),
    url(r'^uploads/$', views.root_upload_view, name='all_projects'),
    url(r'^uploads/(?P<project>[^/]+)/$',
        views.project_root_view,
        name='root_project'),
    url(r'^uploads/(?P<project>[^/]+)/latest/$',
        views.project_latest_view,
        name='project_latest'),
    url(r'^uploads/(?P<project>[^/]+)/historical/$',
        views.project_historical_view,
        name='project_historical'),
    url(r'^uploads/(?P<project>[^/]+)/latest/(?P<file_name>[^/]+)$',
        views.latest_download_view,
        name='file_latest'),
    url(r'^uploads/(?P<project>[^/]+)/historical/(?P<file_name>[^/]+)$',
        views.historical_download_view,
        name='file_historical'),
    url(r'^report/(?P<project>[^/]+)/$',
        views.ReportView.as_view(),
        name='project_report'),
    url(r'^tasks/create_report/status/(?P<task_id>[^/]+)/$',
        views.check_report_task_view,
        name='task_status'),
    url(r'^tasks/create_report/(?P<project>[^/]+)/$',
        views.create_report_view,
        name='create_report'),
]
