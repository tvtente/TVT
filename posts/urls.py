# File: posts/urls.py
from django.urls import path
from . import views

app_name = "posts"

urlpatterns = [
    path('', views.post_list_view, name='post_list'),
    path('following/', views.following_posts_view, name='following_posts'),
    path('favorites/', views.favorite_posts_view, name='favorite_posts'),
    path('<slug:list_type>/', views.post_list_view, name='post_list_by_type'),
    
    # URL con fecha + slug
    path('<int:year>/<int:month>/<int:day>/<slug:slug>/points/', views.assign_post_points_view, name='assign_post_points'),
    path('<int:year>/<int:month>/<int:day>/<slug:slug>/favorite/', views.toggle_post_favorite_view, name='toggle_post_favorite'),
    path('<int:year>/<int:month>/<int:day>/<slug:slug>/secciones/<slug:section_slug>/', views.post_content_block_detail_view, name='post_content_block_detail'),
    path('<int:year>/<int:month>/<int:day>/<slug:slug>/', views.post_detail_view, name='post_detail'),
    path('category/<slug:category_slug>/', views.posts_by_category_view, name='posts_by_category'),
    path('tag/<slug:tag_slug>/', views.posts_by_tag_view, name='posts_by_tag'),
]
