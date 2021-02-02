"""
URLs for track app
"""


from django.conf import settings  # lint-amnesty, pylint: disable=unused-import
from django.conf.urls import url

from . import views
from .views import segmentio

urlpatterns = [
    url(r'^event$', views.user_track),
    url(r'^segmentio/event$', segmentio.segmentio_event),
]
