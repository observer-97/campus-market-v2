"""Classroom-only money simulation. All mutations commit atomically, never real payments."""
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from .models import DemoOrder, DemoWallet, WalletEntry, Product, OrderEvent

ACTIVE_STATES = [DemoOrder.State.ACCEPTED, DemoOrder.State.PAID]

def reserved(product):
    return product.orders.filter(state__in=ACTIVE_STATES).exists()

@transaction.atomic
def grant_demo_balance(user):
    wallet, _ = DemoWallet.objects.get_or_create(user=user)
    if DemoWallet.objects.filter(pk=wallet.pk, grant_claimed=False).update(grant_claimed=True, balance_cents=F('balance_cents') + 100000):
        WalletEntry.objects.create(user=user, kind='grant', delta_cents=100000)

@transaction.atomic
def order_action(order_id, user, action):
    order = DemoOrder.objects.select_for_update().get(pk=order_id)
    product = Product.objects.select_for_update().get(pk=order.product_id)
    if user.pk not in [order.buyer_id, order.seller_id]:
        raise ValueError('无权操作此交易。')
    buyer = user.pk == order.buyer_id
    before = order.state
    S = DemoOrder.State
    if action == 'accept' and not buyer and before == S.PROPOSED:
        if product.owner_id != order.seller_id or product.status != 'approved' or product.sale_status != 'available' or product.revision != order.product_revision or int(product.price * 100) != order.amount_cents:
            raise ValueError('商品已变化或不在售，请取消此意愿，重新协商并发起。')
        if reserved(product):
            raise ValueError('该商品已有进行中的交易。')
        if not DemoOrder.objects.filter(pk=order.pk, state=before).update(state=S.ACCEPTED, updated_at=timezone.now()):
            raise ValueError('交易状态已改变，请刷新。')
        order.state = S.ACCEPTED
    elif action == 'pay' and buyer and before == S.ACCEPTED:
        order.state = S.PAID
        _claim_transition(order, before)
        wallet, _ = DemoWallet.objects.get_or_create(user=user)
        if not DemoWallet.objects.filter(pk=wallet.pk, balance_cents__gte=order.amount_cents).update(balance_cents=F('balance_cents') - order.amount_cents):
            raise ValueError('模拟余额不足，请先在交易中心领取演示余额。')
        WalletEntry.objects.create(user=user, order=order, kind='pay', delta_cents=-order.amount_cents)
    elif action == 'confirm' and buyer and before == S.PAID:
        order.state = S.COMPLETED
        _claim_transition(order, before)
        wallet, _ = DemoWallet.objects.get_or_create(user_id=order.seller_id)
        DemoWallet.objects.filter(pk=wallet.pk).update(balance_cents=F('balance_cents') + order.amount_cents)
        WalletEntry.objects.create(user_id=order.seller_id, order=order, kind='release', delta_cents=order.amount_cents)
        product.sale_status = 'sold'
        product.revision += 1
        product.save()
    elif action == 'refund' and not buyer and before == S.PAID:
        order.state = S.CANCELED
        _claim_transition(order, before)
        wallet, _ = DemoWallet.objects.get_or_create(user_id=order.buyer_id)
        DemoWallet.objects.filter(pk=wallet.pk).update(balance_cents=F('balance_cents') + order.amount_cents)
        WalletEntry.objects.create(user_id=order.buyer_id, order=order, kind='refund', delta_cents=order.amount_cents)
    elif action == 'cancel' and before in [S.PROPOSED, S.ACCEPTED]:
        order.state = S.CANCELED
        _claim_transition(order, before)
    else:
        raise ValueError('当前身份或交易状态不允许此操作；请刷新页面，勿重复付款或结算。')
    OrderEvent.objects.create(order=order, actor=user, state=order.state)
    return order

def _claim_transition(order, before):
    if not DemoOrder.objects.filter(pk=order.pk, state=before).update(state=order.state, updated_at=timezone.now()):
        raise ValueError('交易状态已改变，请刷新。')
