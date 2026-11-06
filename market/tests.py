import io
import json
import tempfile
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from market.forms import ProductForm
from market.models import Product, Favorite
from market.ml import load_model

class FlowTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user('owner', password='StrongOwner2026!')
        self.other = get_user_model().objects.create_user('other', password='StrongOther2026!')
        self.product = Product.objects.create(owner=self.owner, title='高数教材', description='同济高等数学上下册，课堂学习用', price='20', category='study', contact='演示联系', status=Product.Status.APPROVED)
        self.payload = {'title': '羽毛球拍', 'description': '两支球拍附拍套，用于体育社团训练', 'price': '35', 'category': 'sports', 'contact': '测试联系'}
    def test_registration_login_logout(self):
        response = self.client.post('/register/', {'username': 'new_student', 'password1': 'BookCampus2026!', 'password2': 'BookCampus2026!'})
        self.assertRedirects(response, '/')
        self.assertTrue(get_user_model().objects.get(username='new_student').check_password('BookCampus2026!'))
        self.assertRedirects(self.client.post('/logout/'), '/')
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.post('/login/', {'username': 'new_student', 'password': 'BookCampus2026!'}), '/')
        self.assertEqual(self.client.get('/logout/').status_code, 405)
    def test_publish_search_filter_and_detail(self):
        self.assertEqual(self.client.get('/publish/').status_code, 302)
        self.client.force_login(self.owner)
        response = self.client.post('/publish/', self.payload)
        product = Product.objects.get(title='羽毛球拍')
        self.assertRedirects(response, f'/products/{product.pk}/')
        self.assertEqual(product.owner, self.owner)
        self.assertEqual(product.status, Product.Status.PENDING)
        self.assertNotContains(self.client.get('/?q=球拍&category=sports'), '羽毛球拍')
        product.status = Product.Status.APPROVED
        product.save()
        self.assertContains(self.client.get('/?q=球拍&category=sports'), '羽毛球拍')
        self.assertNotContains(self.client.get('/?q=球拍&category=study'), '羽毛球拍')
        self.assertContains(self.client.get(f'/products/{product.pk}/'), '测试联系')
        self.assertContains(self.client.get('/mine/'), '羽毛球拍')
    def test_favorites_and_owner_permission(self):
        self.client.force_login(self.other)
        url = f'/products/{self.product.pk}/favorite/'
        self.client.post(url)
        self.assertEqual(Favorite.objects.count(), 1)
        self.assertContains(self.client.get('/favorites/'), '高数教材')
        self.client.post(url)
        self.assertEqual(Favorite.objects.count(), 0)
        self.assertEqual(self.client.post(f'/products/{self.product.pk}/delete/').status_code, 404)
        self.assertTrue(Product.objects.filter(pk=self.product.pk).exists())
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(f'/products/{self.product.pk}/delete/').status_code, 405)
        self.client.post(f'/products/{self.product.pk}/delete/')
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_status, Product.SaleStatus.OFFLINE)
    def test_actual_model_endpoint(self):
        self.client.force_login(self.owner)
        response = self.client.post('/api/predict/', json.dumps({'title': '羽毛球拍', 'description': '体育课训练用双人球拍，附拍套'}), content_type='application/json')
        self.assertEqual(response.status_code, 200, response.content)
        model, meta = load_model()
        actual = model.predict(['羽毛球拍 体育课训练用双人球拍，附拍套'])[0]
        self.assertEqual(response.json()['category'], actual)
        self.assertEqual(response.json()['algorithm'], meta['algorithm'])
    def test_prediction_errors(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.post('/api/predict/', '{}', content_type='application/json').status_code, 400)
        self.assertEqual(self.client.post('/api/predict/', 'null', content_type='application/json').status_code, 400)
        with patch('market.views.classify', side_effect=FileNotFoundError()):
            response = self.client.post('/api/predict/', json.dumps({'title': '书', 'description': '学习用'}), content_type='application/json')
            self.assertEqual(response.status_code, 503)
            self.assertIn('模型不可用', response.json()['error'])
        response = self.client.post('/api/predict/', json.dumps({'title': '🧊', 'description': '🧊'}), content_type='application/json')
        self.assertEqual(response.status_code, 503)
    def test_upload_price_and_csrf(self):
        self.assertFalse(ProductForm({**self.payload, 'price': '0'}).is_valid())
        fake = SimpleUploadedFile('evil.png', b'<script>alert(1)</script>', content_type='image/png')
        self.assertFalse(ProductForm(self.payload, {'image': fake}).is_valid())
        buffer = io.BytesIO()
        Image.new('RGB', (20, 20), 'green').save(buffer, 'PNG')
        image = SimpleUploadedFile('valid.png', buffer.getvalue(), content_type='image/png')
        self.assertTrue(ProductForm(self.payload, {'image': image}).is_valid())
        with tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent.parent, prefix='.test-') as media_dir, override_settings(MEDIA_ROOT=media_dir):
            self.client.force_login(self.owner)
            uploaded = SimpleUploadedFile('saved.png', buffer.getvalue(), content_type='image/png')
            self.assertEqual(self.client.post('/publish/', {**self.payload, 'image': uploaded}).status_code, 302)
            product = Product.objects.get(title=self.payload['title'])
            self.assertTrue(Path(product.image.path).is_file())
            self.assertContains(self.client.get(f'/products/{product.pk}/'), product.image.url)
        large = SimpleUploadedFile('large.png', buffer.getvalue() + b'0' * (5 * 1024 * 1024), content_type='image/png')
        self.assertFalse(ProductForm(self.payload, {'image': large}).is_valid())
        from django.test import Client
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.owner)
        self.assertEqual(client.post('/publish/', self.payload).status_code, 403)
    def test_demo_idempotent_and_empty_state(self):
        self.assertContains(self.client.get('/?q=不存在商品'), '这里暂时还没有好物')
        call_command('init_demo', stdout=io.StringIO())
        demo = get_user_model().objects.get(username='demo_student')
        demo.set_password('ChangedPassword2026!')
        demo.save()
        count = Product.objects.count()
        call_command('init_demo', stdout=io.StringIO())
        demo.refresh_from_db()
        self.assertEqual(count, Product.objects.count())
        self.assertTrue(demo.check_password('ChangedPassword2026!'))

class TrainingTests(TestCase):
    def test_missing_duplicate_and_near_duplicate_cleaning(self):
        import csv
        from market.management.commands.train_model import prepare
        from django.conf import settings
        source = settings.BASE_DIR / 'data/examples.csv'
        with source.open(encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            rows = list(reader)
        rows.append({**rows[0], 'id': 'exact-copy'})
        rows.append({**rows[0], 'id': 'missing-desc', 'description': ''})
        rows.append({**rows[0], 'id': 'near-copy', 'title': rows[0]['title'] + '转让', 'group_id': 'unknown'})
        with tempfile.TemporaryDirectory(dir=settings.BASE_DIR, prefix='.test-') as folder:
            path = Path(folder) / 'fixture.csv'
            with path.open('w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            cleaned, audit = prepare(path)
        self.assertEqual(len(cleaned), 98)
        self.assertEqual({r['reason'] for r in audit['removed']}, {'exact_duplicate', 'missing_field'})
        pair = [r for r in cleaned if r['id'] in {'study-001', 'near-copy'}]
        self.assertEqual(len({r['leakage_group'] for r in pair}), 1)
    def test_cleaning_and_group_leakage(self):
        from market.management.commands.train_model import prepare
        from django.conf import settings
        rows, audit = prepare(settings.BASE_DIR / 'data/examples.csv')
        self.assertEqual(len(rows), 97)
        pair = [r for r in rows if r['group_id'] == 'study-01']
        self.assertEqual(len({r['leakage_group'] for r in pair}), 1)
        report = json.loads((settings.BASE_DIR / 'artifacts/evaluation.json').read_text(encoding='utf-8'))
        splits = report['splits']
        for a, b in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
            self.assertFalse(set(splits[a]['groups']) & set(splits[b]['groups']))
