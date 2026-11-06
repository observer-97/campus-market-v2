from django.db import migrations

def baseline(apps, schema_editor):
    Product = apps.get_model('market', 'Product')
    History = apps.get_model('market', 'ProductHistory')
    for product in Product.objects.using(schema_editor.connection.alias).iterator():
        History.objects.using(schema_editor.connection.alias).create(product_id=product.pk, title=product.title, status=product.status, sale_status=product.sale_status)

class Migration(migrations.Migration):
    dependencies = [('market', '0004_product_sale_status_producthistory_profile')]
    operations = [migrations.RunPython(baseline, migrations.RunPython.noop)]
