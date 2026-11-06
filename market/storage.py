"""Database-backed uploads for a small course demo; no runtime filesystem writes."""
import io
import uuid
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.urls import reverse
from django.utils.deconstruct import deconstructible


@deconstructible
class DatabaseImageStorage(Storage):
    def _open(self, name, mode='rb'):
        from .models import StoredImage
        try:
            row = StoredImage.objects.only('data').get(pk=name)
        except StoredImage.DoesNotExist as exc:
            raise FileNotFoundError(name) from exc
        return ContentFile(bytes(row.data), name=name)

    def _save(self, name, content):
        from .models import StoredImage
        content.seek(0)
        data = content.read(settings.PRODUCT_IMAGE_MAX_BYTES + 1)
        if len(data) > settings.PRODUCT_IMAGE_MAX_BYTES:
            raise ValidationError('图片不能超过 3 MB。')
        try:
            image = Image.open(io.BytesIO(data))
            fmt = image.format
            if fmt not in {'JPEG', 'PNG', 'WEBP'} or image.width * image.height > 20_000_000:
                raise ValueError('Unsupported image')
            image.verify()
        except Exception as exc:
            raise ValidationError('请上传有效的 JPEG、PNG 或 WebP 图片。') from exc
        suffix, mime = {'JPEG': ('.jpg', 'image/jpeg'), 'PNG': ('.png', 'image/png'), 'WEBP': ('.webp', 'image/webp')}[fmt]
        key = uuid.uuid4().hex + suffix
        StoredImage.objects.create(name=key, data=data, content_type=mime, size=len(data))
        return key

    def exists(self, name):
        from .models import StoredImage
        return StoredImage.objects.filter(pk=name).exists()

    def delete(self, name):
        from .models import StoredImage
        StoredImage.objects.filter(pk=name).delete()

    def size(self, name):
        from .models import StoredImage
        return StoredImage.objects.values_list('size', flat=True).get(pk=name)

    def url(self, name):
        return reverse('database_image', kwargs={'name': name})
