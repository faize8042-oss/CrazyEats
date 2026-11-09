from django.core.exceptions import ValidationError
from django.http import Http404

def positive_id(value):
    try:
        number = int(value)
    except (ValueError, TypeError):
        raise Http404("Invalid identifier")
    if number <= 0 or number > 9223372036854775807:
        raise Http404("Invalid identifier")
    return number

def validate_image_upload(image):
    if not image:
        return image
    if image.size > 5 * 1024 * 1024:
        raise ValidationError("Images must be 5 MB or smaller.")
    if getattr(image, "image", None) is not None:
        if image.image.format not in {"JPEG", "PNG", "WEBP"}:
            raise ValidationError("Upload a JPEG, PNG, or WebP image.")
        if image.image.width * image.image.height > 20000000:
            raise ValidationError("Images must contain no more than 20 million pixels.")
    return image
