from django.urls import path

from gallery import staff_media_views

app_name = "gallery_media"

urlpatterns = [
    path("stage/", staff_media_views.stage_upload_view, name="stage"),
    path("stage/<uuid:pk>/", staff_media_views.stage_delete_view, name="stage_delete"),
    path("stage/<uuid:pk>/preview/", staff_media_views.stage_preview_view, name="stage_preview"),
    path("images/", staff_media_views.image_list_json_view, name="image_list"),
    path("images/<int:pk>/preview/", staff_media_views.image_preview_view, name="image_preview"),
    path("images/<int:pk>/", staff_media_views.image_detail_json_view, name="image_detail"),
]
