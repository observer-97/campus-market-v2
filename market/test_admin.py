import io
import tempfile
from pathlib import Path
from PIL import Image
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.admin.models import LogEntry
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command, CommandError
from django.test import TestCase, override_settings
from .models import Product, Favorite

class AdminTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser('manager', '', 'Manager2026!')
        self.user = get_user_model().objects.create_user('student', password='Student2026!')
        self.product = Product.objects.create(owner=self.user, title='后台测试教材', description='课堂测试', price=20, category='study', contact='演示联系')
        self.data = {'owner': self.user.pk, 'title': '后台更新教材', 'description': '更新描述', 'price': '33', 'category': 'study', 'contact': '更新联系', '_save': '保存', 'status': 'approved', 'review_revision': '1'}

    def test_login_and_regular_user_denied(self):
        self.assertRedirects(self.client.get('/admin/'), '/admin/login/?next=/admin/')
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/market/product/').status_code, 302)
        self.assertEqual(self.client.post(f'/admin/market/product/{self.product.pk}/change/', self.data).status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.price, 20)
        self.client.logout()
        response = self.client.post('/admin/login/?next=/admin/', {'username': 'manager', 'password': 'Manager2026!', 'next': '/admin/'})
        self.assertRedirects(response, '/admin/')
        self.assertContains(self.client.get('/admin/'), '校园二手平台管理')

    def test_admin_edit_search_favorite_delete_audit(self):
        self.client.force_login(self.admin)
        self.assertContains(self.client.get('/admin/market/product/?q=教材&category__exact=study'), '后台测试教材')
        self.assertEqual(self.client.post(f'/admin/market/product/{self.product.pk}/change/', self.data).status_code, 302)
        self.assertContains(self.client.get(f'/products/{self.product.pk}/'), '更新联系')
        self.assertTrue(LogEntry.objects.filter(object_id=str(self.product.pk), action_flag=2).exists())
        self.assertEqual(self.client.post('/admin/market/favorite/add/', {'user': self.user.pk, 'product': self.product.pk, '_save': '保存'}).status_code, 302)
        self.client.force_login(self.user)
        self.assertContains(self.client.get('/favorites/'), '后台更新教材')
        self.client.force_login(self.admin)
        self.client.post(f'/admin/market/product/{self.product.pk}/delete/', {'post': 'yes'})
        self.assertFalse(Product.objects.filter(pk=self.product.pk).exists())
        self.assertEqual(Favorite.objects.count(), 0)

    def test_staff_needs_model_permissions(self):
        self.user.is_staff = True
        self.user.save()
        self.client.force_login(self.user)
        self.assertEqual(self.client.get('/admin/market/product/').status_code, 403)
        self.user.user_permissions.add(Permission.objects.get(codename='view_product'))
        self.assertEqual(self.client.get('/admin/market/product/').status_code, 200)
        self.assertEqual(self.client.post(f'/admin/market/product/{self.product.pk}/change/', self.data).status_code, 403)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code, 403)

    def test_admin_image_validation_and_existing_image(self):
        self.client.force_login(self.admin)
        buffer = io.BytesIO()
        Image.new('RGB', (10, 10), 'green').save(buffer, 'PNG')
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent, prefix='.test-admin-') as media, override_settings(MEDIA_ROOT=media):
            response = self.client.post('/admin/market/product/add/', {**self.data, 'image': SimpleUploadedFile('valid.png', buffer.getvalue(), content_type='image/png')})
            self.assertEqual(response.status_code, 302)
            product = Product.objects.get(title='后台更新教材')
            original = product.image.name
            self.assertEqual(self.client.post(f'/admin/market/product/{product.pk}/change/', {**self.data, 'price': '40'}).status_code, 302)
            product.refresh_from_db()
            self.assertEqual(product.image.name, original)
            self.assertTrue(Path(product.image.path).is_file())
            fake = SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')
            self.assertEqual(self.client.post('/admin/market/product/add/', {**self.data, 'image': fake}).status_code, 200)
            self.assertEqual(Product.objects.count(), 2)

    def test_admin_initialization_does_not_elevate_or_reset(self):
        with self.assertRaises(CommandError):
            call_command('init_admin', username='student', stdout=io.StringIO())
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_staff)
        original = self.admin.password
        call_command('init_admin', username='manager', stdout=io.StringIO())
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.password, original)
        call_command('init_admin', username='new_manager', stdout=io.StringIO())
        created = get_user_model().objects.get(username='new_manager')
        self.assertTrue(created.is_superuser and created.is_staff and created.is_active)
