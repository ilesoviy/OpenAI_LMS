"""
URL definitions for the course_modes API.
"""


from django.conf.urls import include
from django.urls import path

app_name = 'common.djangoapps.course_modes.rest_api'

urlpatterns = [
    path('v1/', include('common.djangoapps.course_modes.rest_api.v1.urls', namespace='v1')),
]
