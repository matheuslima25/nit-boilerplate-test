from django.conf.urls import include
from django.urls import path
from nitapi.router.api_v1 import api_v1_urls

api_urls = [
    path('v1/', include((api_v1_urls, 'api_v1_urls'), namespace='v1')),
]
