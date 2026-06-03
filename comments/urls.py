from django.urls import path

from . import views


app_name = "comments"


urlpatterns = [
    path("<int:comment_id>/translate/", views.translate_comment_view, name="translate_comment"),
    path("<int:comment_id>/suggest-translation/", views.suggest_comment_translation_view, name="suggest_comment_translation"),
]
