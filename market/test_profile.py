from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Product, Profile

class ProfileTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user('profile_seller', password='Seller2026!')
        self.other = get_user_model().objects.create_user('visitor', password='Visitor2026!')
        self.product = Product.objects.create(owner=self.owner, title='公开教材', description='教材描述', price=20, category='study', contact='非在售不应公开联系', status='approved')
        self.url = f'/users/{self.owner.pk}/'

    def test_private_default_and_opt_in(self):
        self.assertContains(self.client.get(self.url), '尚未公开')
        self.assertNotContains(self.client.get(self.url), '公开教材')
        self.client.force_login(self.owner)
        self.assertContains(self.client.get('/center/', follow=True), '公开教材')
        self.client.post('/center/settings/', {'is_public': 'on', 'bio': '欢迎来看我的闲置', 'user': self.other.pk})
        self.assertTrue(Profile.objects.get(user=self.owner).is_public)
        self.assertFalse(Profile.objects.filter(user=self.other).exists())
        self.client.logout()
        self.assertContains(self.client.get(self.url), '欢迎来看我的闲置')
        self.assertContains(self.client.get(self.url), '公开教材')
        self.client.force_login(self.owner)
        self.client.post('/center/settings/', {'bio': '已关闭'})
        self.client.logout()
        self.assertNotContains(self.client.get(self.url), '公开教材')

    def test_sale_history_filters_market_and_relisting_review(self):
        Profile.objects.create(user=self.owner, is_public=True)
        self.client.force_login(self.owner)
        self.client.post(f'/products/{self.product.pk}/state/', {'state': 'sold'})
        self.assertEqual(self.product.history.count(), 2)
        self.client.logout()
        self.assertNotContains(self.client.get('/'), '公开教材')
        self.assertContains(self.client.get(self.url + '?state=sold'), '公开教材')
        self.assertNotContains(self.client.get(self.url + '?state=available'), '公开教材')
        self.assertNotContains(self.client.get(f'/products/{self.product.pk}/'), '非在售不应公开联系')
        self.client.force_login(self.owner)
        self.client.post(f'/products/{self.product.pk}/state/', {'state': 'offline'})
        self.assertEqual(self.product.history.count(), 3)
        self.assertContains(self.client.get(self.url + '?state=offline'), '公开教材')
        self.client.post(f'/products/{self.product.pk}/state/', {'state': 'available'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, 'pending')
        self.client.logout()
        self.assertNotContains(self.client.get(self.url), '公开教材')

    def test_state_permission_and_private_review(self):
        url = f'/products/{self.product.pk}/state/'
        self.assertEqual(self.client.post(url, {'state': 'sold'}).status_code, 302)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(url, {'state': 'sold'}).status_code, 404)
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(self.client.post(url, {'state': 'fake'}).status_code, 400)
        self.product.status = 'rejected'
        self.product.save()
        self.client.post(url, {'state': 'sold'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_status, 'available')
        Profile.objects.create(user=self.owner, is_public=True)
        self.client.logout()
        self.assertNotContains(self.client.get(self.url), '公开教材')

    def test_withdraw_retains_history(self):
        self.client.force_login(self.owner)
        self.client.post(f'/products/{self.product.pk}/delete/')
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_status, 'offline')
        self.assertEqual(self.product.history.count(), 2)
        self.assertContains(self.client.get('/center/', follow=True), '已下架')
