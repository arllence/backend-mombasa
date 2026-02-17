from django.contrib import admin
from django.urls import path, include, re_path
from django.conf.urls.static import static, serve
from django.conf import settings

API_VERSION = 'api/v1/'

urlpatterns = [
    # path('admin/', admin.site.urls),
    path(API_VERSION, include('acl.urls')),
    path(API_VERSION, include('mms.urls')),
    path(API_VERSION, include('trs.urls')),
    path(API_VERSION, include('srrs.urls')),
    path(API_VERSION, include('asa.urls')),
    path(API_VERSION, include('ams.urls')),
    path(API_VERSION, include('sls.urls')),
    path(API_VERSION, include('intranet.urls')),
    path(API_VERSION, include('dbmanager.urls')),
    path(API_VERSION, include('fms.urls')),
    path(API_VERSION, include('cms.urls')),
    path(API_VERSION, include('mhd.urls')),
    path(API_VERSION, include('smr.urls')),
    path(API_VERSION, include('system_directory.urls')),
    path(API_VERSION, include('ict_helpdesk.urls')),
    path(API_VERSION, include('ipass.urls')),
    path(API_VERSION, include('invoice_tracking.urls')),
    path(API_VERSION, include('ctp.urls')),
    path(API_VERSION, include('security_helpdesk.urls')),
    path(API_VERSION, include('expenditure.urls')),
    path(API_VERSION, include('radiology.urls')),
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),

] 
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


if settings.DEBUG:
    adminurl = [
        path('admin/', admin.site.urls),
    ]
    urlpatterns += adminurl