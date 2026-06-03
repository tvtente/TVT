import datetime
import logging

from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.core.exceptions import SuspiciousFileOperation
from django.utils.html import strip_tags 
from django.utils.translation import get_language, activate, deactivate 

from site_settings.models import SiteConfiguration # For pagination settings
from posts.models import Post
from pages.models import Page
from .models import Image # For images specifically in the gallery app
from django.utils.translation import gettext

logger = logging.getLogger(__name__)


def _safe_file_url(file_field):
    if not file_field:
        return ''
    try:
        return file_field.url
    except (ValueError, OSError, SuspiciousFileOperation):
        return ''

# Helper function to get a truncated description (remains the same)
def get_truncated_description(text, max_length=200):
    """Safely truncates and cleans text for description display."""
    if not text:
        return ""
    stripped_text = strip_tags(str(text)) 
    if len(stripped_text) > max_length:
        return stripped_text[:max_length] + "..."
    return stripped_text

def gallery_view(request):
    """
    Collects images from the Image model and featured images from Posts and Pages,
    normalizes their data, sorts them, and displays them in a paginated gallery.
    """
    gallery_items_data = [] # This list will hold uniform dictionaries for the template
    current_lang = get_language() # Get current language for consistent data retrieval
    seen_image_urls = set()

    def add_gallery_item(image_url, title, description, detail_url, date, item_type):
        if not image_url or image_url in seen_image_urls:
            return

        seen_image_urls.add(image_url)
        gallery_items_data.append({
            'image_url': image_url,
            'title': title,
            'description': get_truncated_description(description),
            'detail_url': detail_url,
            'date': date,
            'type': item_type,
        })

    # --- Get all images from the gallery.Image model ---
    # Log the number of objects found before processing
    logger.debug(f"Collecting images from gallery.Image model. Found {Image.objects.count()} objects.")
    for img_obj in Image.objects.all():
        # Ensure image has a file attached before trying to get its URL
        img_url = _safe_file_url(img_obj.image)
        # get_absolute_url() needs to be correctly defined in Image model
        detail_url = img_obj.get_absolute_url() 
        logger.debug(f"Processing Image (ID: {img_obj.pk}): URL={img_url}, DetailURL={detail_url}, Title={img_obj.title}")

        add_gallery_item(
            image_url=img_url,
            title=img_obj.title,
            description=img_obj.description,
            detail_url=detail_url,
            date=img_obj.uploaded_at, # Use uploaded_at for sorting
            item_type='Image',
        )
    
    # --- Get featured images from posts.Post model ---
    posts_with_images = (
        Post.objects.language(current_lang)
        .filter(status='published')
        .prefetch_related('translations')
        .order_by('-published_date')
    )
    
    logger.debug("Collecting translated featured images from posts.Post model.")
    for post_obj in posts_with_images:
        featured_image = post_obj.get_featured_image()
        if not featured_image:
            continue

        post_img_url = _safe_file_url(featured_image)
        if not post_img_url:
            continue
        post_detail_url = post_obj.get_absolute_url()
        post_published_date = post_obj.published_date 
        
        # Use get_language()/activate/deactivate for language-specific fields like title/description from other models
        # It ensures we grab the translation in the CURRENT language for uniform data collection.
        old_lang = get_language()
        activate(current_lang) 
        
        add_gallery_item(
            image_url=post_img_url,
            title=post_obj.safe_translation_getter('title', any_language=True),
            description=(
                post_obj.safe_translation_getter('summary', any_language=True)
                or post_obj.safe_translation_getter('meta_description', any_language=True)
                or post_obj.safe_translation_getter('content', any_language=True)
            ),
            detail_url=post_detail_url,
            date=post_published_date,
            item_type='Post',
        )
        activate(old_lang) # Restore original language context

    # --- Get featured images from pages.Page model (asset FK-based) ---
    try:
        pages_with_images = Page.objects.filter(status='published').order_by('-updated_at')
        logger.debug(f"Collecting featured images from pages.Page model. Found {pages_with_images.count()} objects.")
        for page_obj in pages_with_images:
            page_image = page_obj.get_featured_image(current_lang)
            page_img_url = _safe_file_url(page_image)
            if not page_img_url:
                continue
            page_detail_url = page_obj.get_absolute_url()
            page_updated_at = page_obj.updated_at

            old_lang = get_language()
            activate(current_lang)
            add_gallery_item(
                image_url=page_img_url,
                title=page_obj.title, # Modeltranslation handles this
                description=page_obj.get_abstract(current_lang) or page_obj.content,
                detail_url=page_detail_url,
                date=page_updated_at,
                item_type='Page',
            )
            activate(old_lang) # Restore original language context
    except Exception as e:
        logger.warning(f"Error collecting featured images from Pages: {e}.")


    # --- Sort the combined list by date (newest first) ---
    # Ensure 'date' key always exists with a valid datetime object for sorting.
    # Handle cases where `date` might be None, placing them at the end.
    gallery_items_data.sort(key=lambda x: x.get('date') if x.get('date') is not None else datetime.min, reverse=True)
    
    # --- Apply Pagination ---
    try:
        site_config = SiteConfiguration.get_solo()
        gallery_items_per_page = site_config.gallery_items_per_page
    except SiteConfiguration.DoesNotExist:
        gallery_items_per_page = 9 # Fallback value
        logger.warning("SiteConfiguration not found. Using default gallery pagination (9 items).")
    
    paginator = Paginator(gallery_items_data, gallery_items_per_page)
    page_number = request.GET.get('page')

    try:
        images_on_page = paginator.get_page(page_number)
    except PageNotAnInteger:
        images_on_page = paginator.get_page(1)
    except EmptyPage:
        # If the page number is out of range, get the last page, or an empty list if no items
        if paginator.num_pages > 0:
            images_on_page = paginator.get_page(paginator.num_pages)
        else:
            images_on_page = [] # No pages to display if paginator has 0 pages
    
    logger.info(f"Gallery view accessed. Showing page {getattr(images_on_page, 'number', 0)} of {getattr(images_on_page, 'paginator.num_pages', 0)} images.")
    breadcrumbs = [
        {"url": "/", "label": gettext("Home")},
        {"url": "", "label": gettext("Gallery")},
    ]
    context = {
        'images': images_on_page, # Passed to template as 'images'
        "breadcrumbs": breadcrumbs,
    }

    return render(request, 'gallery/gallery_page.html', context)

# NEW: View for individual image detail (basic placeholder)
def image_detail_view(request, pk):
    """ Displays details for a single image from the gallery. """
    image = get_object_or_404(Image, pk=pk)
    context = {
        'image': image,
        'translatable_object': image,
    }
    # Create this template: gallery/templates/gallery/image_detail.html
    return render(request, 'gallery/image_detail.html', context)
