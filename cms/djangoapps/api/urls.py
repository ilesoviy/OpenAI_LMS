"""
URLs for the Studio API app
"""


from django.conf.urls import include
from django.urls import path

app_name = 'cms.djangoapps.api'

urlpatterns = [
    path('v1/', include('cms.djangoapps.api.v1.urls', namespace='v1')),
]
