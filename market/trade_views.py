from decimal import Decimal
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, OperationalError, transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Product, Profile, CAMPUSES, Conversation, ChatMessage, DemoOrder, DemoWallet, WalletEntry, OrderEvent
from .trading import ACTIVE_STATES, grant_demo_balance, order_action

def participants(user):
    return Q(buyer=user) | Q(seller=user)

@login_required
@require_POST
def start_chat(request, pk):
    product = get_object_or_404(Product, pk=pk, status='approved', sale_status='available')
    if product.owner_id == request.user.pk:
        messages.error(request, '不能与自己发起交易。')
        return redirect('detail', pk=pk)
    conversation, _ = Conversation.objects.get_or_create(product=product, buyer=request.user, defaults={'seller': product.owner})
    return redirect('chat', pk=conversation.pk)

@login_required
def trades(request):
    wallet, _ = DemoWallet.objects.get_or_create(user=request.user)
    orders = DemoOrder.objects.filter(participants(request.user)).select_related('buyer', 'seller', 'product')
    escrow = orders.filter(state='paid').aggregate(total=Sum('amount_cents'))['total'] or 0
    return render(request, 'trades.html', {'wallet': wallet, 'orders': Paginator(orders, 20).get_page(request.GET.get('page')), 'conversations': Conversation.objects.filter(participants(request.user)).select_related('product', 'buyer', 'seller').order_by('-id')[:50], 'entries': WalletEntry.objects.filter(user=request.user).select_related('order')[:20], 'escrow': Decimal(escrow) / 100})

@login_required
def chat(request, pk):
    conversation = get_object_or_404(Conversation.objects.filter(participants(request.user)).select_related('product', 'buyer', 'seller'), pk=pk)
    if request.method == 'POST':
        body = request.POST.get('body', '').strip()
        if not body or len(body) > 2000:
            messages.error(request, '私信不能为空，最多 2000 字。')
        else:
            ChatMessage.objects.create(conversation=conversation, sender=request.user, body=body)
        return redirect('chat', pk=pk)
    page = Paginator(conversation.messages.select_related('sender').order_by('-id'), 30).get_page(request.GET.get('page'))
    return render(request, 'chat.html', {'conversation': conversation, 'chat_page': page, 'chat_messages': list(reversed(list(page))), 'campuses': CAMPUSES, 'orders': conversation.orders.all()[:10]})

@login_required
@require_POST
@transaction.atomic
def propose_order(request, pk):
    conversation = get_object_or_404(Conversation.objects.filter(buyer=request.user), pk=pk)
    product = Product.objects.select_for_update().get(pk=conversation.product_id)
    campus = request.POST.get('campus', '')
    place = request.POST.get('meeting_place', '').strip()
    if campus not in dict(CAMPUSES) or not place or len(place) > 200:
        messages.error(request, '请选择交易校区并填写具体地点（最多 200 字）。')
    elif product.status != 'approved' or product.sale_status != 'available' or product.owner_id != conversation.seller_id or product.orders.filter(state__in=ACTIVE_STATES).exists():
        messages.error(request, '商品已不可交易或已有进行中的交易。')
    else:
        existing = conversation.orders.exclude(state__in=['completed', 'canceled']).first()
        if existing:
            return redirect('order', pk=existing.pk)
        try:
            with transaction.atomic():
                order = DemoOrder.objects.create(conversation=conversation, product=product, buyer=request.user, seller=conversation.seller, title=product.title, amount_cents=int(product.price * 100), product_revision=product.revision, campus=campus, meeting_place=place)
        except IntegrityError:
            existing = conversation.orders.exclude(state__in=['completed', 'canceled']).first()
            if existing:
                return redirect('order', pk=existing.pk)
            raise
        OrderEvent.objects.create(order=order, actor=request.user, state=order.state)
        return redirect('order', pk=order.pk)
    return redirect('chat', pk=pk)

@login_required
def order_detail(request, pk):
    order = get_object_or_404(DemoOrder.objects.filter(participants(request.user)).select_related('buyer', 'seller', 'product', 'conversation'), pk=pk)
    return render(request, 'order.html', {'order': order, 'events': order.events.select_related('actor')})

@login_required
@require_POST
def act_order(request, pk):
    get_object_or_404(DemoOrder.objects.filter(participants(request.user)), pk=pk)
    if request.POST.get('action') == 'confirm' and request.POST.get('received') != 'on':
        messages.error(request, '请先确认已在线下收到商品，再确认收货。')
        return redirect('order', pk=pk)
    try:
        order_action(pk, request.user, request.POST.get('action'))
        messages.success(request, '模拟交易状态已更新。')
    except (ValueError, IntegrityError, OperationalError) as exc:
        messages.error(request, str(exc) if isinstance(exc, ValueError) else '交易状态正在变化，请刷新后重试；本次操作未提交。')
    return redirect('order', pk=pk)

@login_required
@require_POST
def grant(request):
    try:
        grant_demo_balance(request.user)
        messages.success(request, '每个账号可领取一次 1000 元模拟余额，无真实价值。')
    except (IntegrityError, OperationalError):
        messages.error(request, '领取未提交，请稍后重试。')
    return redirect('trades')
