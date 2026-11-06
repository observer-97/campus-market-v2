from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.contrib import admin
from .models import Product, Profile, Conversation, ChatMessage, DemoOrder, DemoWallet, WalletEntry


class OfflineTradingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user('offline_seller')
        self.buyer = User.objects.create_user('offline_buyer')
        self.other = User.objects.create_user('offline_outsider')
        Profile.objects.create(user=self.seller, campus='jiang', is_public=True)
        self.product = Product.objects.create(owner=self.seller, title='线下面交教材', description='功能验证商品', price='35.50', category='study', contact='演示联系', status='approved')
        self.chat = Conversation.objects.create(product=self.product, buyer=self.buyer, seller=self.seller)
        self.legacy = DemoOrder.objects.create(conversation=self.chat, product=self.product, buyer=self.buyer, seller=self.seller, title=self.product.title, amount_cents=3550, product_revision=1, campus='jiang', meeting_place='旧地点', state='paid')
        self.client.force_login(self.buyer)

    def test_no_payment_ui_or_wallet_created_when_browsing(self):
        for url in ['/trades/', f'/chats/{self.chat.pk}/', f'/products/{self.product.pk}/']:
            r = self.client.get(url)
            self.assertEqual(r.status_code, 200)
            for action in ['value="pay"', 'value="confirm"', 'value="refund"', '/trades/grant/', '/propose/']:
                self.assertNotContains(r, action)
        self.assertContains(self.client.get('/trades/'), '线下验货')
        self.assertEqual(DemoWallet.objects.count(), 0)
        self.assertEqual(WalletEntry.objects.count(), 0)

    def test_legacy_operations_gone_without_mutations(self):
        for user in [self.buyer, self.seller]:
            self.client.force_login(user)
            for action in ['accept', 'pay', 'confirm', 'refund', 'cancel']:
                self.assertEqual(self.client.post(f'/orders/{self.legacy.pk}/action/', {'action': action, 'received': 'on'}).status_code, 410)
            self.assertEqual(self.client.post('/trades/grant/').status_code, 410)
            self.assertEqual(self.client.post(f'/chats/{self.chat.pk}/propose/', {'campus': 'jiang', 'meeting_place': '新地点'}).status_code, 410)
        self.legacy.refresh_from_db()
        self.assertEqual(self.legacy.state, 'paid')
        self.assertEqual(DemoOrder.objects.count(), 1)
        self.assertEqual(DemoWallet.objects.count(), 0)
        self.assertEqual(WalletEntry.objects.count(), 0)

    def test_legacy_history_private_and_read_only(self):
        self.assertContains(self.client.get(f'/orders/{self.legacy.pk}/'), '历史模拟记录')
        self.assertNotContains(self.client.get(f'/orders/{self.legacy.pk}/'), 'order-actions')
        self.client.force_login(self.other)
        for url in [f'/orders/{self.legacy.pk}/', f'/chats/{self.chat.pk}/']:
            self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.post(f'/orders/{self.legacy.pk}/action/', {'action': 'pay'}).status_code, 404)
        self.assertNotContains(self.client.get('/trades/'), self.product.title)

    def test_both_participants_share_location_and_messages_escape(self):
        for user in [self.buyer, self.seller]:
            self.client.force_login(user)
            self.assertEqual(self.client.post(f'/chats/{self.chat.pk}/meeting/', {'campus': 'jiang', 'meeting_place': '南区操场北入口 <script>bad()</script>'}).status_code, 302)
        self.assertEqual(ChatMessage.objects.count(), 2)
        r = self.client.get(f'/chats/{self.chat.pk}/')
        self.assertContains(r, '将军路校区')
        self.assertContains(r, '&lt;script&gt;')
        self.assertNotContains(r, '<script>bad()')
        self.assertEqual(DemoOrder.objects.count(), 1)

    def test_location_validation_permissions_and_csrf(self):
        for values in [{'campus': 'fake', 'meeting_place': '地点'}, {'campus': 'jiang', 'meeting_place': ' '}, {'campus': 'jiang', 'meeting_place': '字' * 201}]:
            self.client.post(f'/chats/{self.chat.pk}/meeting/', values)
        self.assertEqual(ChatMessage.objects.count(), 0)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(f'/chats/{self.chat.pk}/meeting/', {'campus': 'jiang', 'meeting_place': '地点'}).status_code, 404)
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(self.buyer)
        self.assertEqual(strict.post(f'/chats/{self.chat.pk}/meeting/', {'campus': 'jiang', 'meeting_place': '地点'}).status_code, 403)
        self.assertEqual(ChatMessage.objects.count(), 0)

    def test_legacy_paid_order_does_not_lock_listing_or_owner_states(self):
        self.assertContains(self.client.get('/'), self.product.title)
        self.assertEqual(self.client.post(f'/products/{self.product.pk}/state/', {'state': 'sold'}).status_code, 404)
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(f'/products/{self.product.pk}/edit/').status_code, 200)
        self.client.post(f'/products/{self.product.pk}/state/', {'state': 'sold'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_status, 'sold')
        self.assertContains(self.client.get('/center/', follow=True), '已售出')
        self.assertTrue(self.product.history.filter(sale_status='sold').exists())
        self.assertNotContains(self.client.get('/'), self.product.title)
        self.client.post(f'/products/{self.product.pk}/delete/')
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_status, 'offline')
        self.assertTrue(DemoOrder.objects.filter(pk=self.legacy.pk).exists())

    def test_chat_security_empty_input_and_reuse(self):
        self.client.post(f'/chats/{self.chat.pk}/', {'body': ' '})
        self.client.post(f'/chats/{self.chat.pk}/', {'body': '字' * 2001})
        self.assertEqual(ChatMessage.objects.count(), 0)
        self.client.post(f'/chats/{self.chat.pk}/', {'body': '明天下午见'})
        self.client.post(f'/products/{self.product.pk}/chat/')
        self.client.post(f'/products/{self.product.pk}/chat/')
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(ChatMessage.objects.count(), 1)
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(f'/chats/{self.chat.pk}/', {'body': '越权'}).status_code, 404)

    def test_admin_historical_orders_read_only_wallets_hidden(self):
        manager = get_user_model().objects.create_superuser('offline_admin', '', 'StrongAdmin2026!')
        self.client.force_login(manager)
        self.assertEqual(self.client.get('/admin/market/demoorder/').status_code, 200)
        self.assertEqual(self.client.post(f'/admin/market/demoorder/{self.legacy.pk}/change/', {'state': 'completed'}).status_code, 403)
        self.assertFalse(admin.site.is_registered(DemoWallet))
        self.assertFalse(admin.site.is_registered(WalletEntry))
        self.assertNotContains(self.client.get('/admin/'), '模拟余额')
