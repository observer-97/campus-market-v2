from django.http import Http404, HttpResponse
from django.views.decorators.http import require_safe
from .models import StoredImage, Product


@require_safe
def database_image(request, name):
    image = StoredImage.objects.filter(pk=name).first()
    if image is None:
        raise Http404
    products = Product.objects.filter(image=name)
    visible = products.filter(status=Product.Status.APPROVED).exists()
    if request.user.is_authenticated:
        visible = visible or request.user.has_perm('market.view_product') or products.filter(owner=request.user).exists()
    if not visible:
        raise Http404
    response = HttpResponse(bytes(image.data), content_type=image.content_type)
    response['Content-Length'] = image.size
    response['Cache-Control'] = 'private, no-store'
    response['X-Content-Type-Options'] = 'nosniff'
    return response
