import io
import tempfile
from pathlib import Path
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings, Client
from .models import Product, Favorite

class ReviewTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user('seller', password='Seller2026!')
        self.other = get_user_model().objects.create_user('buyer', password='Buyer2026!')
        self.admin = get_user_model().objects.create_superuser('reviewer', '', 'Review2026!')
        self.data = {'title': '审核流程羽毛球拍', 'description': '双人球拍，成色较新', 'price': '35', 'category': 'sports', 'contact': '演示联系'}
        self.product = Product.objects.create(owner=self.owner, **self.data)

    def review(self, status, reason='', revision=1):
        self.client.force_login(self.admin)
        return self.client.post(f'/admin/market/product/{self.product.pk}/change/', {**self.data, 'owner': self.owner.pk, 'status': status, 'rejection_reason': reason, 'review_revision': revision, '_save': '保存'})

    def test_pending_and_rejected_are_private(self):
        Favorite.objects.create(user=self.other, product=self.product)
        for status in [Product.Status.PENDING, Product.Status.REJECTED]:
            self.product.status = status
            self.product.rejection_reason = '描述缺少瑕疵说明' if status == Product.Status.REJECTED else ''
            self.product.save()
            self.client.logout()
            self.assertNotContains(self.client.get('/?q=羽毛球拍'), self.data['title'])
            self.assertEqual(self.client.get(f'/products/{self.product.pk}/').status_code, 404)
            self.client.force_login(self.other)
            self.assertNotContains(self.client.get('/favorites/'), self.data['title'])
            self.assertEqual(self.client.post(f'/products/{self.product.pk}/favorite/').status_code, 404)
            self.client.force_login(self.owner)
            self.assertContains(self.client.get('/mine/'), self.product.get_status_display())
            self.assertContains(self.client.get(f'/products/{self.product.pk}/'), self.data['title'])
            if status == Product.Status.REJECTED:
                self.assertContains(self.client.get('/mine/'), '描述缺少瑕疵说明')

    def test_admin_approve_and_reject(self):
        self.assertEqual(self.review('approved').status_code, 302)
        self.product.refresh_from_db()
        self.assertEqual(self.product.reviewed_by, self.admin)
        self.assertIsNotNone(self.product.reviewed_at)
        self.client.logout()
        self.assertContains(self.client.get('/?q=羽毛球拍'), self.data['title'])
        self.assertContains(self.client.get(f'/products/{self.product.pk}/'), '演示联系')
        response = self.review('rejected', '   ')
        self.assertContains(response, '驳回商品时必须填写具体理由')
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.Status.APPROVED)
        self.assertEqual(self.review('rejected', '请补充瑕疵实拍').status_code, 302)
        self.client.force_login(self.owner)
        self.assertContains(self.client.get('/mine/'), '请补充瑕疵实拍')

    def test_edit_ownership_validation_and_cannot_self_approve(self):
        url = f'/products/{self.product.pk}/edit/'
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(url, self.data).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post(url, {**self.data, 'price': '0'}).status_code, 200)
        self.product.refresh_from_db()
        self.assertEqual(self.product.revision, 1)
        response = self.client.post(url, {**self.data, 'price': '42', 'description': '修改描述', 'contact': '新联系', 'owner': self.other.pk, 'status': 'approved', 'rejection_reason': '伪造理由'})
        self.assertRedirects(response, f'/products/{self.product.pk}/')
        self.product.refresh_from_db()
        self.assertEqual(self.product.owner, self.owner)
        self.assertEqual(self.product.status, Product.Status.PENDING)
        self.assertEqual(self.product.rejection_reason, '')
        self.assertEqual(self.product.price, 42)
        self.assertEqual(self.product.contact, '新联系')
        self.assertEqual(self.product.description, '修改描述')
        self.assertEqual(self.product.revision, 2)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.owner)
        self.assertEqual(csrf_client.post(url, self.data).status_code, 403)

    def test_edit_resets_approval_and_rejects_stale_review(self):
        self.review('approved')
        self.client.force_login(self.owner)
        self.client.post(f'/products/{self.product.pk}/edit/', self.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.Status.PENDING)
        self.assertIsNone(self.product.reviewed_by)
        self.assertIsNone(self.product.reviewed_at)
        self.assertContains(self.review('approved', revision=1), '卖家已提交新版本')
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.Status.PENDING)
        self.assertEqual(self.review('approved', revision=2).status_code, 302)
        self.review('rejected', '请修正描述', revision=2)
        self.client.force_login(self.owner)
        self.client.post(f'/products/{self.product.pk}/edit/', self.data)
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Product.Status.PENDING)
        self.assertEqual(self.product.rejection_reason, '')

    def test_seller_replace_preserve_remove_and_invalid_image(self):
        buffer = io.BytesIO()
        Image.new('RGB', (16, 16), 'green').save(buffer, 'PNG')
        def image():
            return SimpleUploadedFile('test.png', buffer.getvalue(), content_type='image/png')
        url = f'/products/{self.product.pk}/edit/'
        self.client.force_login(self.owner)
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent, prefix='.test-review-') as media, override_settings(MEDIA_ROOT=media):
            self.assertEqual(self.client.post(url, {**self.data, 'image': image()}).status_code, 302)
            self.product.refresh_from_db()
            original = self.product.image.name
            self.assertTrue(Path(self.product.image.path).exists())
            self.client.post(url, self.data)
            self.product.refresh_from_db()
            self.assertEqual(self.product.image.name, original)
            self.client.post(url, {**self.data, 'image': image()})
            self.product.refresh_from_db()
            replacement = self.product.image.name
            self.assertNotEqual(replacement, original)
            fake = SimpleUploadedFile('fake.png', b'not an image', content_type='image/png')
            self.assertEqual(self.client.post(url, {**self.data, 'image': fake}).status_code, 200)
            self.product.refresh_from_db()
            self.assertEqual(self.product.image.name, replacement)
            self.client.post(url, {**self.data, 'image-clear': 'on'})
            self.product.refresh_from_db()
            self.assertFalse(self.product.image)
