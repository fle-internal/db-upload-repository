# Create your tasks here
from __future__ import absolute_import, unicode_literals
from celery import shared_task
import os
import pandas
import pytz
from datetime import datetime
from sqlalchemy import create_engine
from django.utils import timezone

from .views import latest_db_path
from .models import FacilitySummary, Project


@shared_task
def create_report(project_code):
    project = Project.objects.get(project_code=project_code)
    directory = latest_db_path(project_code)
    summaries = []
    if os.path.exists(directory):
        files = os.listdir(directory)
        for file_name in files:
            file_path = os.path.join(directory, file_name)
            if os.path.isfile(file_path) and file_name.endswith('sqlite3'):
                stats = os.stat(file_path)
                last_sync = datetime.fromtimestamp(stats.st_mtime)
                last_sync = timezone.make_aware(last_sync, pytz.utc)
                db_path = 'sqlite:///' + file_path
                try:
                    db_engine = create_engine(db_path)
                    collections = pandas.read_sql_table(
                        'kolibriauth_collection', db_engine)
                    facility_name = collections[collections.kind ==
                                                'facility'].iloc[0]['name']
                    facility_id = collections[collections.kind ==
                                              'facility'].iloc[0]['id']
                    session_logs = pandas.read_sql_table(
                        'logger_contentsessionlog', db_engine)
                    time_content_sessions = session_logs['time_spent'].sum()
                    num_content_sessions = session_logs['time_spent'].count()
                    try:
                        previous_summary = FacilitySummary.objects.filter(
                            facility_id=facility_id,
                            project=project).latest('generated')
                    except FacilitySummary.DoesNotExist:
                        previous_summary = None
                    summary, created = FacilitySummary.objects.get_or_create(
                        facility_id=facility_id,
                        last_sync=last_sync,
                        project=project,
                        defaults={
                            "facility_name": facility_name,
                            "num_content_sessions": num_content_sessions,
                            "time_content_sessions": time_content_sessions,
                        })
                    summaries.append(created)
                    if previous_summary and created:
                        previous_summary.next_summary = summary
                        previous_summary.save()
                except:
                    print('{file_name} was malformed'.format(
                        file_name=file_name))
    return sum(summaries)
