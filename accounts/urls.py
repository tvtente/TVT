# accounts/urls.py
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_view, name='signup'),
    path('inbox/', views.inbox_view, name='inbox'),
    path('inbox/read-all/', views.mark_all_notifications_read_view, name='mark_all_notifications_read'),
    path('inbox/<int:notification_id>/read/', views.mark_notification_read_view, name='mark_notification_read'),
    path('profile/<str:username>/follow/', views.toggle_follow_view, name='toggle_follow'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/cv/', views.profile_cv_edit_view, name='profile_cv_edit'),
    path('profile/<str:username>/print/', views.user_profile_public_print_view, name='public_profile_print'),
    path('profile/<str:username>/pdf/', views.user_profile_public_pdf_view, name='public_profile_pdf'),
    path('profile/<str:username>/', views.user_profile_public_view, name='public_profile'),
    path('directory/', views.user_directory_view, name='user_directory'),
]
