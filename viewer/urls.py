from django.urls import path
from . import views

urlpatterns = [
    path("", views.upload_page, name="upload"),
    path("upload/", views.upload_files, name="upload_files"),
    path("viewer/", views.viewer_page, name="viewer_page"),
    path("api/schema/", views.api_schema, name="api_schema"),
    path("api/query/", views.api_query, name="api_query"),
    path("api/export/", views.api_export, name="api_export"),
    path("api/clear/", views.api_clear_session, name="api_clear_session"),
]
