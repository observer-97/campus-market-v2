from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Product, ProductHistory

@receiver(pre_save, sender=Product)
def before_product_save(sender, instance, **kwargs):
    fields = ['title', 'description', 'price', 'contact', 'image', 'category', 'status', 'sale_status']
    old = sender.objects.filter(pk=instance.pk).first() if instance.pk else None
    instance._record_history = old is None or any(str(getattr(old, name)) != str(getattr(instance, name)) for name in fields)

@receiver(post_save, sender=Product)
def record_product_history(sender, instance, raw=False, **kwargs):
    if not raw and getattr(instance, '_record_history', False):
        ProductHistory.objects.create(product=instance, title=instance.title, status=instance.status, sale_status=instance.sale_status)
