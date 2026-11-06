from datetime import datetime
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from .models import Product, Profile, ProductReport

class SettingsSearchReportTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user('settings_seller', password='SellerBefore2026!')
        self.buyer = User.objects.create_user('settings_buyer', password='BuyerBefore2026!')
        self.admin = User.objects.create_superuser('settings_admin', '', 'AdminBefore2026!')
        self.product = Product.objects.create(owner=self.seller, title='筛选举报教材', description='课程教材', price='20', category='study', contact='原商品公开联系', status='approved')

    def test_settings_default_contact_privacy_and_prefill(self):
        self.assertEqual(self.client.get('/account/settings/').status_code, 302)
        self.client.force_login(self.seller)
        response = self.client.post('/account/settings/', {'bio': '新的简介', 'campus': 'jiang', 'default_contact': 'private-default-123', 'is_public': 'on', 'user': self.buyer.pk})
        self.assertRedirects(response, '/account/settings/')
        self.assertEqual(Profile.objects.get(user=self.seller).default_contact, 'private-default-123')
        self.assertFalse(Profile.objects.filter(user=self.buyer).exists())
        self.assertContains(self.client.get('/publish/'), 'private-default-123')
        self.assertContains(self.client.get('/publish/'), '公开前请确认')
        self.assertNotContains(self.client.get(f'/products/{self.product.pk}/edit/'), 'private-default-123')
        self.product.refresh_from_db()
        self.assertEqual(self.product.contact, '原商品公开联系')
        self.client.logout()
        self.assertNotContains(self.client.get(f'/users/{self.seller.pk}/'), 'private-default-123')
        self.assertContains(self.client.get(f'/users/{self.seller.pk}/'), '新的简介')
        self.assertNotContains(self.client.get(f'/products/{self.product.pk}/'), 'private-default-123')

    def test_password_change_old_password_validation_session_and_login(self):
        self.client.force_login(self.seller)
        self.assertEqual(self.client.post('/account/password/', {'old_password': 'wrong', 'new_password1': 'NewCampusPassword2026!', 'new_password2': 'NewCampusPassword2026!'}).status_code, 200)
        response = self.client.post('/account/password/', {'old_password': 'SellerBefore2026!', 'new_password1': 'NewCampusPassword2026!', 'new_password2': 'NewCampusPassword2026!'})
        self.assertRedirects(response, '/account/password/done/')
        self.assertIn('_auth_user_id', self.client.session)
        self.seller.refresh_from_db()
        self.assertFalse(self.seller.check_password('SellerBefore2026!'))
        self.assertTrue(self.seller.check_password('NewCampusPassword2026!'))
        self.client.logout()
        self.assertFalse(self.client.login(username='settings_seller', password='SellerBefore2026!'))
        self.assertTrue(self.client.login(username='settings_seller', password='NewCampusPassword2026!'))
        csrf = Client(enforce_csrf_checks=True)
        csrf.force_login(self.seller)
        self.assertEqual(csrf.post('/account/settings/', {'bio': 'forged'}).status_code, 403)

    def test_price_dates_sort_and_pagination_preserve(self):
        for i in range(15):
            p = Product.objects.create(owner=self.seller, title=f'测试教材{i}', description='搜索文本', price=10+i, category='study', contact='演示', status='approved')
            Product.objects.filter(pk=p.pk).update(created_at=datetime(2026, 10, 22, 23, 59, tzinfo=ZoneInfo('Asia/Hong_Kong')))
        params = {'q': '测试教材', 'category': 'study', 'min_price': '10', 'max_price': '30', 'start_date': '2026-10-22', 'end_date': '2026-10-22', 'sort': 'price_desc'}
        response = self.client.get('/', params)
        page = response.context['page']
        self.assertEqual(page.paginator.count, 15)
        self.assertEqual([p.price for p in page], sorted([p.price for p in page], reverse=True))
        self.assertEqual(page[0].price, 24)
        for key in ['min_price=10', 'max_price=30', 'start_date=2026-10-22', 'end_date=2026-10-22', 'sort=price_desc', 'page=2']:
            self.assertContains(response, key)
        response = self.client.get('/', {**params, 'page': '2'})
        self.assertEqual(len(response.context['page']), 3)
        self.assertContains(response, 'value="30"')
        self.assertEqual(self.client.get('/', {**params, 'start_date': '2026-10-23', 'end_date': '2026-10-23'}).context['page'].paginator.count, 0)
        response = self.client.get('/', {**params, 'sort': 'price_asc', 'min_price': '20', 'max_price': '21'})
        self.assertEqual([p.price for p in response.context['page']], [20, 21])

    def test_invalid_search_inputs_show_errors(self):
        for params in [{'min_price': 'NaN'}, {'max_price': '-1'}, {'min_price': '50', 'max_price': '10'}, {'start_date': 'bad'}, {'start_date': '2026-10-23', 'end_date': '2026-10-22'}, {'sort': 'unexpected'}]:
            response = self.client.get('/', params)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.context['search_form'].errors)
            self.assertEqual(response.context['page'].paginator.count, 0)

    def test_report_submit_duplicate_and_visibility(self):
        url = f'/products/{self.product.pk}/report/'
        self.assertEqual(self.client.get(url).status_code, 302)
        self.client.force_login(self.seller)
        self.client.post(url, {'reason': 'fraud', 'details': '不能举报自己'})
        self.assertEqual(ProductReport.objects.count(), 0)
        self.client.force_login(self.buyer)
        self.assertEqual(self.client.post(url, {'reason': 'fraud', 'details': ''}).status_code, 200)
        self.assertRedirects(self.client.post(url, {'reason': 'fraud', 'details': '只有举报人看到的测试说明', 'reporter': self.seller.pk, 'state': 'resolved', 'result': '伪造'}), '/reports/')
        report = ProductReport.objects.get()
        self.assertEqual(report.reporter, self.buyer)
        self.assertEqual(report.state, 'pending')
        self.assertEqual(report.result, '')
        self.assertContains(self.client.post(url, {'reason': 'spam', 'details': '再次举报'}), '待处理举报')
        self.assertEqual(ProductReport.objects.count(), 1)
        self.assertContains(self.client.get('/reports/'), '只有举报人看到的测试说明')
        self.client.force_login(self.seller)
        self.assertNotContains(self.client.get('/reports/'), '只有举报人看到的测试说明')
        self.assertEqual(self.client.get('/admin/market/productreport/').status_code, 302)

    def test_report_admin_result_required_and_history_retained(self):
        report = ProductReport.objects.create(reporter=self.buyer, product=self.product, product_title=self.product.title, reason='fraud', details='管理员核查测试')
        url = f'/admin/market/productreport/{report.pk}/change/'
        self.client.force_login(self.admin)
        self.assertContains(self.client.post(url, {'state': 'resolved', 'result': '  ', '_save': '保存'}), '必须填写处理结果')
        self.assertEqual(self.client.post(url, {'state': 'resolved', 'result': '已核查，并联系卖家整改', '_save': '保存'}).status_code, 302)
        report.refresh_from_db()
        self.assertEqual(report.handled_by, self.admin)
        self.assertIsNotNone(report.handled_at)
        self.client.force_login(self.buyer)
        self.assertContains(self.client.get('/reports/'), '已核查，并联系卖家整改')
        self.product.delete()
        report.refresh_from_db()
        self.assertIsNone(report.product_id)
        self.assertContains(self.client.get('/reports/'), '原商品已删除')
