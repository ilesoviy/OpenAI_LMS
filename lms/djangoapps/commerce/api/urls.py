"""
API URLs.
"""


from django.urls import include, path

app_name = 'commerce'
urlpatterns = [
    path('v0/', include('lms.djangoapps.commerce.api.v0.urls')),
    path('v1/', include('lms.djangoapps.commerce.api.v1.urls')),
]
