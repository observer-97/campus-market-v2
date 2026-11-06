import io
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, SimpleTestCase, override_settings
from market.models import Product, StoredImage, ProductHistory
from market.storage import DatabaseImageStorage

DB_STORAGE = {'default': {'BACKEND': 'market.storage.DatabaseImageStorage'}, 'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}


def png():
    data = io.BytesIO()
    Image.new('RGB', (24, 24), 'green').save(data, format='PNG')
    return data.getvalue()


@override_settings(STORAGES=DB_STORAGE)
class CloudMediaTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user('image_owner')
        self.other = get_user_model().objects.create_user('image_other')
        self.product = Product.objects.create(owner=self.owner, title='云端图片', description='有效图片', price=10, category='study', contact='模拟')
        self.content = png()
        self.product.image.save('photo.png', ContentFile(self.content))

    def test_persists_across_storage_instances_and_restricts_pending_images(self):
        key = self.product.image.name
        self.assertEqual(StoredImage.objects.get(pk=key).size, len(self.content))
        self.assertEqual(DatabaseImageStorage().open(key).read(), self.content)
        url = self.product.image.url
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.other.is_staff = True
        self.other.save()
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).content, self.content)
        self.client.logout()
        self.product.status = 'approved'
        self.product.save()
        response = self.client.get(url)
        self.assertEqual(response.content, self.content)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        self.product.status = 'rejected'
        self.product.save()
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_invalid_oversized_and_deleted_upload(self):
        storage = DatabaseImageStorage()
        for data in [b'<svg>not a valid image</svg>', b'x' * (3 * 1024 * 1024 + 1)]:
            with self.assertRaises(ValidationError):
                storage.save('test.png', ContentFile(data))
        key = self.product.image.name
        storage.delete(key)
        self.assertFalse(storage.exists(key))
        self.assertEqual(self.client.get(storage.url(key)).status_code, 404)


@override_settings(STORAGES=DB_STORAGE)
class CloudBootstrapTests(TestCase):
    @patch.dict(os.environ, {'CAMPUS_ADMIN_USERNAME': 'course_admin_test', 'CAMPUS_ADMIN_PASSWORD': 'RandomCourse-Test-Password-2026!'})
    def test_bootstrap_idempotent_no_password_leak_or_user_review_bypass(self):
        out = io.StringIO()
        owner = get_user_model().objects.create_user('ordinary_owner')
        pending = Product.objects.create(owner=owner, title='普通待审商品', description='演示', price=12, category='study', contact='模拟')
        call_command('init_cloud_demo', stdout=out)
        self.assertEqual(Product.objects.filter(status='approved').count(), 9)
        self.assertEqual(StoredImage.objects.count(), 9)
        admin = get_user_model().objects.get(username='course_admin_test')
        before = admin.password
        count = ProductHistory.objects.count()
        changed = Product.objects.filter(status='approved').first()
        changed.status = 'rejected'
        changed.rejection_reason = '测试保留已有状态'
        changed.save()
        count = ProductHistory.objects.count()
        with patch.dict(os.environ, {'CAMPUS_ADMIN_PASSWORD': 'Changed-Env-Does-Not-Reset-2026!'}):
            call_command('init_cloud_demo', stdout=out)
        admin.refresh_from_db()
        pending.refresh_from_db()
        changed.refresh_from_db()
        self.assertEqual(admin.password, before)
        self.assertEqual(pending.status, 'pending')
        self.assertEqual(changed.status, 'rejected')
        self.assertEqual(Product.objects.count(), 10)
        self.assertEqual(StoredImage.objects.count(), 9)
        self.assertEqual(ProductHistory.objects.count(), count)
        self.assertNotIn('RandomCourse-Test-Password-2026!', out.getvalue())
        for name in ['demo_student', 'demo_seller', 'demo_buyer']:
            user = get_user_model().objects.get(username=name)
            self.assertFalse(user.is_staff)
            self.assertFalse(user.is_superuser)
            self.assertTrue(user.profile.campus)

    @patch.dict(os.environ, {'CAMPUS_ADMIN_USERNAME': 'taken_name', 'CAMPUS_ADMIN_PASSWORD': 'RandomCourse-Test-Password-2026!'})
    def test_no_elevation_of_existing_account(self):
        user = get_user_model().objects.create_user('taken_name')
        with self.assertRaises(CommandError):
            call_command('init_cloud_demo', stdout=io.StringIO())
        user.refresh_from_db()
        self.assertFalse(user.is_staff)
        self.assertEqual(Product.objects.count(), 0)


class ProductionSettingsTests(SimpleTestCase):
    def configured(self, **extra):
        env = os.environ.copy()
        for key in ['DATABASE_URL', 'DJANGO_SECRET_KEY', 'VERCEL', 'DJANGO_DEBUG']:
            env.pop(key, None)
        env.update({'VERCEL': '1', 'DJANGO_SECRET_KEY': 'test-only-random-secret-' * 4,
                    'DATABASE_URL': 'postgresql://user:password@db.example.test/course?sslmode=require',
                    'VERCEL_URL': 'sample-preview.vercel.app', 'VERCEL_PROJECT_PRODUCTION_URL': 'sample.vercel.app'})
        env.update(extra)
        command = 'import sys,json;sys.path.insert(0,".packages312");from config import settings as s;print(json.dumps([s.DEBUG,s.DATABASES["default"]["ENGINE"],s.SESSION_COOKIE_SECURE,s.STORAGES["default"]["BACKEND"],s.ALLOWED_HOSTS]))'
        return subprocess.run([sys.executable, '-c', command], cwd=Path(__file__).resolve().parents[1], env=env, capture_output=True, text=True)

    def test_secure_postgres_configuration(self):
        result = self.configured(DJANGO_DEBUG='1')
        self.assertEqual(result.returncode, 0, result.stderr)
        debug, engine, secure, storage, hosts = json.loads(result.stdout)
        self.assertFalse(debug)
        self.assertEqual(engine, 'django.db.backends.postgresql')
        self.assertTrue(secure)
        self.assertEqual(storage, 'market.storage.DatabaseImageStorage')
        self.assertIn('sample.vercel.app', hosts)
        self.assertNotIn('.vercel.app', hosts)

    def test_missing_secrets_or_database_fail_explicitly(self):
        self.assertNotEqual(self.configured(DATABASE_URL='').returncode, 0)
        self.assertNotEqual(self.configured(DJANGO_SECRET_KEY='short').returncode, 0)
        self.assertNotEqual(self.configured(DJANGO_SECRET_KEY='REPLACE_WITH_A_RANDOM_SECRET_OF_AT_LEAST_50_CHARACTERS').returncode, 0)
        self.assertNotEqual(self.configured(DATABASE_URL='sqlite:///tmp/test.sqlite3').returncode, 0)
