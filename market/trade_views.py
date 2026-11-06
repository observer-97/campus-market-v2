from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Product, CAMPUSES, Conversation, ChatMessage, DemoOrder


def participants(user):
    return Q(buyer=user) | Q(seller=user)


@login_required
@require_POST
def start_chat(request, pk):
    product = get_object_or_404(Product, pk=pk, status='approved', sale_status='available')
    if product.owner_id == request.user.pk:
        messages.error(request, '不能与自己发起私聊。')
        return redirect('detail', pk=pk)
    conversation, _ = Conversation.objects.get_or_create(product=product, buyer=request.user, defaults={'seller': product.owner})
    return redirect('chat', pk=conversation.pk)


@login_required
def trades(request):
    conversations = Conversation.objects.filter(participants(request.user)).select_related('product', 'buyer', 'seller').order_by('-id')
    history = DemoOrder.objects.filter(participants(request.user)).select_related('buyer', 'seller', 'product')
    return render(request, 'trades.html', {
        'conversations': Paginator(conversations, 20).get_page(request.GET.get('page')),
        'orders': Paginator(history, 20).get_page(request.GET.get('history_page')),
    })


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
    return render(request, 'chat.html', {'conversation': conversation, 'chat_page': page, 'chat_messages': list(reversed(list(page))), 'campuses': CAMPUSES})


@login_required
@require_POST
def share_meeting(request, pk):
    conversation = get_object_or_404(Conversation.objects.filter(participants(request.user)), pk=pk)
    campus = request.POST.get('campus', '')
    place = request.POST.get('meeting_place', '').strip()
    if campus not in dict(CAMPUSES) or not place or len(place) > 200:
        messages.error(request, '请选择交易校区并填写具体地点（最多 200 字）。')
    else:
        ChatMessage.objects.create(conversation=conversation, sender=request.user,
            body=f'见面地点建议：{dict(CAMPUSES)[campus]} · {place}\n请双方在私信中确认时间与地点，线下验货，付款方式自行协商。')
        messages.success(request, '地点建议已发送给对方，请继续私信确认。')
    return redirect('chat', pk=pk)


@login_required
def order_detail(request, pk):
    order = get_object_or_404(DemoOrder.objects.filter(participants(request.user)).select_related('buyer', 'seller', 'product', 'conversation'), pk=pk)
    return render(request, 'order.html', {'order': order, 'events': order.events.select_related('actor')})


def retired_response():
    return HttpResponse('支付和模拟交易操作已停用。请通过私信协商，线下验货并自行付款；历史模拟记录仅供查看。', status=410, content_type='text/plain; charset=utf-8')


@login_required
@require_POST
def act_order(request, pk):
    get_object_or_404(DemoOrder.objects.filter(participants(request.user)), pk=pk)
    return retired_response()


@login_required
@require_POST
def propose_order(request, pk):
    get_object_or_404(Conversation.objects.filter(participants(request.user)), pk=pk)
    return retired_response()


@login_required
@require_POST
def grant(request):
    return retired_response()
