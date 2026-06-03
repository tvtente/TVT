"""Staff-only JSON endpoints for the admin media library picker."""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods

from gallery.models import Image, StagedUpload

ALLOWED_IMAGE_CONTENT_TYPES = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    }
)
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
PAGE_SIZE = 24


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

    staged = StagedUpload.objects.create(
        file=upload,
        original_filename=getattr(upload, "name", "") or "",
        created_by=request.user if request.user.is_authenticated else None,
    )
    url = request.build_absolute_uri(staged.file.url) if staged.file else ""
    return JsonResponse(
        {
            "id": str(staged.pk),
            "url": url,
        },
    )


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
