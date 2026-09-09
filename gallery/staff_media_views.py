"""Staff-only JSON endpoints for the admin media library picker."""

from __future__ import annotations

import logging
import mimetypes

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from PIL import Image as PillowImage
from PIL import ImageOps, UnidentifiedImageError

from gallery.models import Image, StagedUpload

logger = logging.getLogger(__name__)

ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/jpg",
        "image/pjpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    }
)
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
PAGE_SIZE = 24
UPLOAD_ASPECT_RATIOS = {
    "16_9": 16 / 9,
    "1_1": 1,
    "9_16": 9 / 16,
}
ASPECT_RATIO_TOLERANCE = 0.015


def _matches_requested_aspect(upload, aspect_name: str) -> bool:
    """Return whether a raster upload matches one of the picker aspect ratios."""
    expected_ratio = UPLOAD_ASPECT_RATIOS.get(aspect_name)
    if expected_ratio is None:
        return True

    try:
        upload.seek(0)
        with PillowImage.open(upload) as image:
            image = ImageOps.exif_transpose(image)
            width, height = image.size
    except (AttributeError, OSError, UnidentifiedImageError, ValueError):
        return False
    finally:
        try:
            upload.seek(0)
        except (AttributeError, OSError):
            pass

    if not width or not height:
        return False
    return abs((width / height) - expected_ratio) <= ASPECT_RATIO_TOLERANCE


def _image_payload(request, image: Image) -> dict:
    return {
        "id": image.pk,
        "title": image.title,
        "slug": image.slug,
        "language": image.language,
        "description": image.description or "",
        "url": image.get_image_url(),
        "uploaded_at": image.uploaded_at.isoformat() if image.uploaded_at else "",
        "derived_from_id": image.derived_from_id,
    }


@csrf_protect
@staff_member_required
@require_http_methods(["POST"])
def stage_upload_view(request):
    upload = request.FILES.get("file")
    if not upload:
        return JsonResponse({"error": "missing_file"}, status=400)

    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        return JsonResponse({"error": "unsupported_type"}, status=400)

    if upload.size > MAX_UPLOAD_BYTES:
        return JsonResponse({"error": "file_too_large"}, status=400)

    requested_aspect = (request.POST.get("required_aspect") or "").strip()
    if requested_aspect and requested_aspect not in UPLOAD_ASPECT_RATIOS:
        return JsonResponse({"error": "invalid_aspect_request"}, status=400)
    if requested_aspect and not _matches_requested_aspect(upload, requested_aspect):
        return JsonResponse({"error": "invalid_aspect"}, status=400)

    convert_to_webp = (request.POST.get("convert_to_webp", "true") or "").lower() not in {
        "0",
        "false",
        "off",
        "no",
    }

    try:
        staged = StagedUpload.objects.create(
            file=upload,
            original_filename=getattr(upload, "name", "") or "",
            convert_to_webp=convert_to_webp,
            created_by=request.user if request.user.is_authenticated else None,
        )
    except ValidationError:
        logger.warning("Gallery staging rejected an invalid image upload.", exc_info=True)
        return JsonResponse({"error": "invalid_image"}, status=400)
    except OSError:
        logger.exception("Gallery staging could not write the uploaded image.")
        return JsonResponse({"error": "storage_error"}, status=500)

    # A staged file can be stored locally while development uses the remote
    # production MEDIA_URL.  Serve its preview through this staff-only endpoint
    # instead of returning ``staged.file.url`` (which may point to another host).
    url = request.build_absolute_uri(reverse("gallery_media:stage_preview", args=[staged.pk]))
    return JsonResponse(
        {
            "id": str(staged.pk),
            "url": url,
        },
    )


@staff_member_required
@require_http_methods(["GET"])
def stage_preview_view(request, pk):
    """Return a temporary staged image preview to the authenticated editor."""
    staged = get_object_or_404(StagedUpload, pk=pk)
    if not staged.file or not getattr(staged.file, "name", ""):
        raise Http404("Staged image not found.")
    try:
        image_file = staged.file.open("rb")
    except OSError as exc:
        raise Http404("Staged image not found.") from exc
    content_type = mimetypes.guess_type(staged.file.name)[0] or "application/octet-stream"
    response = FileResponse(image_file, content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    return response


@staff_member_required
@require_http_methods(["GET"])
def image_preview_view(request, pk):
    """Return a library image preview from the current server to an editor."""
    image = get_object_or_404(Image, pk=pk)
    if not image.image or not getattr(image.image, "name", ""):
        raise Http404("Library image not found.")
    try:
        image_file = image.image.open("rb")
    except OSError as exc:
        raise Http404("Library image not found.") from exc
    content_type = mimetypes.guess_type(image.image.name)[0] or "application/octet-stream"
    response = FileResponse(image_file, content_type=content_type)
    response["Cache-Control"] = "private, no-store"
    return response


@csrf_protect
@staff_member_required
@require_http_methods(["DELETE", "POST"])
def stage_delete_view(request, pk):
    staged = get_object_or_404(StagedUpload, pk=pk)
    staged.delete()
    return JsonResponse({"ok": True})


@staff_member_required
@require_http_methods(["GET"])
def image_list_json_view(request):
    qs = Image.objects.filter(image__isnull=False).exclude(image="").order_by("-uploaded_at")
    q = (request.GET.get("q") or "").strip()
    if q:
        qs = qs.filter(title__icontains=q)
    lang = (request.GET.get("language") or "").strip()
    if lang:
        qs = qs.filter(language=lang)

    try:
        page = max(1, int(request.GET.get("page") or 1))
    except ValueError:
        page = 1
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(page)

    return JsonResponse(
        {
            "results": [_image_payload(request, img) for img in page_obj.object_list],
            "count": paginator.count,
            "page": page_obj.number,
            "num_pages": paginator.num_pages,
            "has_next": page_obj.has_next(),
            "next_page": page_obj.next_page_number() if page_obj.has_next() else None,
        }
    )


@staff_member_required
@require_http_methods(["GET"])
def image_detail_json_view(request, pk):
    image = get_object_or_404(Image, pk=pk)
    return JsonResponse(_image_payload(request, image))
