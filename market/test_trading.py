from django.contrib.auth import get_user_model
from django.db.models import Sum
from django.test import TestCase, Client
from .models import Product, Profile, Conversation, ChatMessage, DemoOrder, DemoWallet, WalletEntry, OrderEvent
from .trading import grant_demo_balance, order_action

class TradingTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.seller = User.objects.create_user('trade_seller')
        self.buyer = User.objects.create_user('trade_buyer')
        self.other = User.objects.create_user('trade_outsider')
        Profile.objects.create(user=self.seller, campus='jiang', is_public=True)
        self.product = Product.objects.create(owner=self.seller, title='交易教材', description='演示内容', price='35.50', category='study', contact='演示', status='approved')
        self.chat = Conversation.objects.create(product=self.product, buyer=self.buyer, seller=self.seller)

    def propose(self, buyer=None, chat=None):
        self.client.force_login(buyer or self.buyer)
        self.client.post(f'/chats/{(chat or self.chat).pk}/propose/', {'campus': 'jiang', 'meeting_place': '将军路校区南区操场北入口'})
        return (chat or self.chat).orders.latest('id')

    def total(self):
        wallets = DemoWallet.objects.aggregate(v=Sum('balance_cents'))['v'] or 0
        escrow = DemoOrder.objects.filter(state='paid').aggregate(v=Sum('amount_cents'))['v'] or 0
        return wallets + escrow

    def test_complete_flow_money_conservation_and_duplicate_actions(self):
        grant_demo_balance(self.buyer)
        grant_demo_balance(self.buyer)
        self.assertEqual(DemoWallet.objects.get(user=self.buyer).balance_cents, 100000)
        order = self.propose()
        self.assertEqual(order.amount_cents, 3550)
        self.client.force_login(self.seller)
        self.assertContains(self.client.get(f'/orders/{order.pk}/'), '确认交易意愿、金额和地点')
        self.client.post(f'/orders/{order.pk}/action/', {'action': 'accept'})
        self.assertNotContains(self.client.get('/'), '交易教材')
        self.client.force_login(self.buyer)
        self.client.post(f'/orders/{order.pk}/action/', {'action': 'pay'})
        self.client.post(f'/orders/{order.pk}/action/', {'action': 'pay'})
        self.assertEqual(DemoWallet.objects.get(user=self.buyer).balance_cents, 96450)
        self.assertFalse(DemoWallet.objects.filter(user=self.seller, balance_cents__gt=0).exists())
        self.assertEqual(self.total(), 100000)
        self.client.post(f'/orders/{order.pk}/action/', {'action': 'confirm'})
        order.refresh_from_db()
        self.assertEqual(order.state, 'paid')
        self.client.post(f'/orders/{order.pk}/action/', {'action': 'confirm', 'received': 'on'})
        self.client.post(f'/orders/{order.pk}/action/', {'action': 'confirm', 'received': 'on'})
        self.assertEqual(DemoWallet.objects.get(user=self.seller).balance_cents, 3550)
        self.assertEqual(self.total(), 100000)
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_status, 'sold')
        self.assertEqual(WalletEntry.objects.filter(order=order).count(), 2)
        self.assertEqual(order.events.count(), 4)
        self.assertContains(self.client.get('/trades/'), '课堂模拟交易')
        self.assertContains(self.client.get(f'/orders/{order.pk}/'), '模拟款项已结算')

    def test_insufficient_funds_rollback_and_refund_once(self):
        order = self.propose()
        order_action(order.pk, self.seller, 'accept')
        with self.assertRaises(ValueError): order_action(order.pk, self.buyer, 'pay')
        order.refresh_from_db()
        self.assertEqual(order.state, 'accepted')
        self.assertEqual(WalletEntry.objects.filter(order=order).count(), 0)
        grant_demo_balance(self.buyer)
        order_action(order.pk, self.buyer, 'pay')
        with self.assertRaises(ValueError): order_action(order.pk, self.buyer, 'refund')
        order_action(order.pk, self.seller, 'refund')
        with self.assertRaises(ValueError): order_action(order.pk, self.seller, 'refund')
        self.assertEqual(DemoWallet.objects.get(user=self.buyer).balance_cents, 100000)
        self.assertEqual(self.total(), 100000)
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_status, 'available')
        self.assertContains(self.client.get('/'), '交易教材')

    def test_chat_permissions_and_escaped_messages(self):
        self.client.force_login(self.buyer)
        self.client.post(f'/chats/{self.chat.pk}/', {'body': '<script>alert(1)</script>'})
        self.assertContains(self.client.get(f'/chats/{self.chat.pk}/'), '&lt;script&gt;alert(1)&lt;/script&gt;')
        self.client.post(f'/chats/{self.chat.pk}/', {'body': ' '})
        self.client.post(f'/chats/{self.chat.pk}/', {'body': '字' * 2001})
        self.assertEqual(ChatMessage.objects.count(), 1)
        order = self.propose()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(f'/chats/{self.chat.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/chats/{self.chat.pk}/', {'body': '伪造'}).status_code, 404)
        self.assertEqual(self.client.get(f'/orders/{order.pk}/').status_code, 404)
        self.assertEqual(self.client.post(f'/orders/{order.pk}/action/', {'action': 'pay'}).status_code, 404)
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.buyer)
        self.assertEqual(client.post(f'/chats/{self.chat.pk}/', {'body': '缺令牌'}).status_code, 403)

    def test_multiple_buyers_only_one_can_be_accepted(self):
        first = self.propose()
        second_chat = Conversation.objects.create(product=self.product, buyer=self.other, seller=self.seller)
        second = self.propose(self.other, second_chat)
        order_action(first.pk, self.seller, 'accept')
        with self.assertRaises(ValueError): order_action(second.pk, self.seller, 'accept')
        order_action(first.pk, self.buyer, 'cancel')
        order_action(second.pk, self.seller, 'accept')
        self.assertEqual(DemoOrder.objects.filter(state='accepted').count(), 1)

    def test_price_snapshot_stale_intent_and_product_locks(self):
        order = self.propose()
        self.product.price = '40'
        self.product.save()
        with self.assertRaises(ValueError): order_action(order.pk, self.seller, 'accept')
        order_action(order.pk, self.buyer, 'cancel')
        order = self.propose()
        order_action(order.pk, self.seller, 'accept')
        self.client.force_login(self.seller)
        self.assertEqual(self.client.get(f'/products/{self.product.pk}/edit/').status_code, 302)
        self.client.post(f'/products/{self.product.pk}/delete/')
        self.client.post(f'/products/{self.product.pk}/state/', {'state': 'sold'})
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_status, 'available')
        with self.assertRaises(ValueError): order_action(order.pk, self.seller, 'pay')
        with self.assertRaises(ValueError): order_action(order.pk, self.other, 'cancel')

    def test_campus_display_validation_and_order_location_snapshot(self):
        self.assertContains(self.client.get(f'/products/{self.product.pk}/'), '将军路校区')
        self.assertContains(self.client.get(f'/users/{self.seller.pk}/'), '将军路校区')
        self.client.force_login(self.seller)
        self.client.post('/center/settings/', {'campus': 'unknown', 'bio': '不保存'})
        self.assertEqual(Profile.objects.get(user=self.seller).campus, 'jiang')
        self.client.force_login(self.buyer)
        self.client.post(f'/chats/{self.chat.pk}/propose/', {'campus': 'unknown', 'meeting_place': '门口'})
        self.assertFalse(DemoOrder.objects.exists())
        order = self.propose()
        self.client.force_login(self.seller)
        self.client.post('/center/settings/', {'campus': 'tian', 'bio': '天目湖', 'is_public': 'on'})
        self.assertContains(self.client.get(f'/orders/{order.pk}/'), '将军路校区南区操场北入口')
        self.assertContains(self.client.get(f'/products/{self.product.pk}/'), '天目湖校区')

    def test_start_chat_and_proposal_idempotence(self):
        self.client.force_login(self.buyer)
        self.client.post(f'/products/{self.product.pk}/chat/')
        self.client.post(f'/products/{self.product.pk}/chat/')
        self.assertEqual(Conversation.objects.count(), 1)
        order = self.propose()
        self.propose()
        self.assertEqual(DemoOrder.objects.count(), 1)
        self.client.force_login(self.seller)
        self.client.post(f'/products/{self.product.pk}/chat/')
        self.assertEqual(Conversation.objects.count(), 1)
        self.assertEqual(self.client.post(f'/chats/{self.chat.pk}/propose/', {'campus': 'jiang', 'meeting_place': '门口'}).status_code, 404)
        self.assertEqual(self.client.get(f'/orders/{order.pk}/action/').status_code, 405)

    def test_admin_cannot_mutate_financial_tables(self):
        admin = get_user_model().objects.create_superuser('finance_admin', '', 'StrongAdmin2026!')
        order = self.propose()
        self.client.force_login(admin)
        self.assertEqual(self.client.get('/admin/market/demoorder/').status_code, 200)
        self.assertEqual(self.client.post(f'/admin/market/demoorder/{order.pk}/change/', {'state': 'completed'}).status_code, 403)
        self.assertEqual(self.client.post(f'/admin/market/demoorder/{order.pk}/delete/', {'post': 'yes'}).status_code, 403)
