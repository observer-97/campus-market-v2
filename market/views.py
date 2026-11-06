import json
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import ProductForm, AccountSettingsForm, SearchForm, ReportForm
from .models import Product, Favorite, Profile, ProductReport, CATEGORIES, CAMPUSES
from .trading import reserved
from .ml import classify

def listing(request, products, heading, personal=False, **extra):
    from django.core.paginator import Paginator
    query = request.GET.copy()
    query.pop('page', None)
    return render(request, 'listing.html', {'page': Paginator(products, 12).get_page(request.GET.get('page')), 'heading': heading, 'categories': CATEGORIES, 'personal': personal, 'filter_query': query.urlencode(), **extra})

def index(request):
    products = Product.objects.select_related('owner').filter(status=Product.Status.APPROVED, sale_status=Product.SaleStatus.AVAILABLE).exclude(orders__state__in=['accepted', 'paid'])
    form = SearchForm(request.GET or {'sort': 'newest'})
    if form.is_valid():
        values = form.cleaned_data
        if values['q']: products = products.filter(Q(title__icontains=values['q']) | Q(description__icontains=values['q']))
        if values['category']: products = products.filter(category=values['category'])
        if values['campus']: products = products.filter(owner__profile__campus=values['campus'])
        if values['min_price'] is not None: products = products.filter(price__gte=values['min_price'])
        if values['max_price'] is not None: products = products.filter(price__lte=values['max_price'])
        if values['start_date']: products = products.filter(created_at__date__gte=values['start_date'])
        if values['end_date']: products = products.filter(created_at__date__lte=values['end_date'])
        products = products.order_by({'newest': '-created_at', 'oldest': 'created_at', 'price_asc': 'price', 'price_desc': '-price'}.get(values['sort'], '-created_at'), '-id')
    else:
        products = products.none()
    active_filters = []
    if form.is_valid():
        if values['category']:
            active_filters.append(dict(CATEGORIES)[values['category']])
        if values['campus']:
            active_filters.append(dict(CAMPUSES)[values['campus']])
        if values['min_price'] is not None or values['max_price'] is not None:
            low = f"{values['min_price']:g}" if values['min_price'] is not None else '0'
            high = f"{values['max_price']:g}" if values['max_price'] is not None else '不限'
            active_filters.append(f'价格 {low}～{high} 元')
        if values['start_date'] or values['end_date']:
            active_filters.append(f"发布 {values['start_date'] or '不限'} 至 {values['end_date'] or '不限'}")
        if values['sort'] and values['sort'] != 'newest':
            active_filters.append(dict(SearchForm.base_fields['sort'].choices)[values['sort']])
    return listing(request, products, '发现校园好物', search_form=form, active_filters=active_filters)

def register(request):
    form = UserCreationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.save())
        return redirect('index')
    return render(request, 'auth.html', {'form': form, 'register': True})

@login_required
def publish(request):
    settings = Profile.objects.filter(user=request.user).first()
    form = ProductForm(request.POST if request.method == 'POST' else None, request.FILES or None, initial={'contact': settings.default_contact if settings else ''})
    if request.method == 'POST' and form.is_valid():
        product = form.save(commit=False)
        product.owner = request.user
        product.save()
        messages.success(request, '提交成功，商品正在等待管理员审核，通过后会公开上架。')
        return redirect('detail', pk=product.pk)
    return render(request, 'publish.html', {'form': form})

@login_required
@transaction.atomic
def edit(request, pk):
    product = get_object_or_404(Product.objects.select_for_update(), pk=pk, owner=request.user)
    if reserved(product):
        messages.error(request, '商品有待付款或已付款交易，请先完成或取消交易，再修改商品。')
        return redirect('detail', pk=pk)
    form = ProductForm(request.POST if request.method == 'POST' else None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        product = form.save(commit=False)
        product.status = Product.Status.PENDING
        product.sale_status = Product.SaleStatus.AVAILABLE
        product.rejection_reason = ''
        product.reviewed_by = None
        product.reviewed_at = None
        product.revision += 1
        product.save()
        messages.success(request, '修改已提交，商品重新进入待审核，审核通过前不会公开展示。')
        return redirect('detail', pk=product.pk)
    return render(request, 'publish.html', {'form': form, 'editing': True, 'product': product})

def visible_products(request):
    products = Product.objects.select_related('owner')
    if request.user.is_authenticated:
        return products.filter(Q(status=Product.Status.APPROVED) | Q(owner=request.user))
    return products.filter(status=Product.Status.APPROVED)

def detail(request, pk):
    product = get_object_or_404(visible_products(request), pk=pk)
    saved = request.user.is_authenticated and Favorite.objects.filter(user=request.user, product=product).exists()
    seller_profile = Profile.objects.filter(user=product.owner).first()
    return render(request, 'detail.html', {'product': product, 'saved': saved, 'seller_profile': seller_profile, 'reserved': reserved(product)})

@login_required
def mine(request):
    return listing(request, Product.objects.filter(owner=request.user), '我的发布', True)

@login_required
def favorites(request):
    return listing(request, visible_products(request).filter(favorites__user=request.user), '我的收藏', True)

@login_required
@require_POST
@transaction.atomic
def delete(request, pk):
    product = get_object_or_404(Product.objects.select_for_update(), pk=pk, owner=request.user)
    if reserved(product):
        messages.error(request, '商品有进行中的交易，请先完成或取消交易。')
        return redirect('detail', pk=pk)
    product.sale_status = Product.SaleStatus.OFFLINE
    product.save()
    messages.success(request, '商品已下架，历史记录已保留。')
    return redirect('mine')

@login_required
def center(request):
    return redirect('profile', user_id=request.user.pk)

@login_required
def account_settings(request):
    settings, _ = Profile.objects.get_or_create(user=request.user)
    form = AccountSettingsForm(request.POST if request.method == 'POST' else None, instance=settings)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, '账号资料已保存；默认联系方式不会自动公开或修改旧商品。')
        return redirect('account_settings')
    return render(request, 'account_settings.html', {'form': form})

@login_required
def report_product(request, pk):
    product = get_object_or_404(visible_products(request), pk=pk)
    if product.owner_id == request.user.pk:
        messages.error(request, '不能举报自己发布的商品。')
        return redirect('detail', pk=pk)
    form = ReportForm(request.POST if request.method == 'POST' else None)
    if request.method == 'POST' and form.is_valid():
        try:
            with transaction.atomic():
                report = form.save(commit=False)
                report.reporter = request.user
                report.product = product
                report.product_title = product.title
                report.save()
            messages.success(request, '举报已提交，请在“我的举报”中查看处理结果。')
            return redirect('reports')
        except IntegrityError:
            form.add_error(None, '你已有该商品的待处理举报，请等待管理员处理。')
    return render(request, 'report.html', {'form': form, 'product': product})

@login_required
def reports(request):
    from django.core.paginator import Paginator
    page = Paginator(ProductReport.objects.filter(reporter=request.user), 12).get_page(request.GET.get('page'))
    return render(request, 'reports.html', {'page': page})

def profile(request, user_id):
    owner = get_object_or_404(get_user_model(), pk=user_id, is_active=True)
    own = request.user.is_authenticated and request.user.pk == owner.pk
    settings = Profile.objects.filter(user=owner).first()
    if not own and not (settings and settings.is_public):
        return render(request, 'profile_private.html', {'owner': owner})
    products = Product.objects.filter(owner=owner).prefetch_related('history')
    if not own:
        products = products.filter(status=Product.Status.APPROVED)
    counts = {value: products.filter(sale_status=value).count() for value, _ in Product.SaleStatus.choices}
    counts['available'] = products.filter(sale_status=Product.SaleStatus.AVAILABLE, status=Product.Status.APPROVED).count()
    selected = request.GET.get('state', '')
    if selected in dict(Product.SaleStatus.choices):
        products = products.filter(sale_status=selected)
        if selected == Product.SaleStatus.AVAILABLE:
            products = products.filter(status=Product.Status.APPROVED)
    from django.core.paginator import Paginator
    page = Paginator(products, 12).get_page(request.GET.get('page'))
    return render(request, 'profile.html', {'owner': owner, 'profile': settings, 'own': own, 'page': page, 'states': Product.SaleStatus.choices, 'counts': counts, 'selected': selected, 'campuses': CAMPUSES})

@login_required
@require_POST
def profile_settings(request):
    bio = request.POST.get('bio', '').strip()
    current = Profile.objects.filter(user=request.user).first()
    campus = request.POST.get('campus', current.campus if current else '')
    if campus and campus not in dict(CAMPUSES):
        messages.error(request, '请选择有效校区。')
    elif len(bio) > 300:
        messages.error(request, '个人简介最多 300 字。')
    else:
        Profile.objects.update_or_create(user=request.user, defaults={'is_public': request.POST.get('is_public') == 'on', 'bio': bio, 'campus': campus})
        messages.success(request, '个人中心设置已保存。')
    return redirect('center')

@login_required
@require_POST
@transaction.atomic
def sale_state(request, pk):
    product = get_object_or_404(Product.objects.select_for_update(), pk=pk, owner=request.user)
    if reserved(product):
        messages.error(request, '商品有进行中的交易，请先完成或取消交易。')
        return redirect('center')
    target = request.POST.get('state')
    if target not in dict(Product.SaleStatus.choices):
        return JsonResponse({'error': '无效交易状态。'}, status=400)
    if target == Product.SaleStatus.SOLD and product.status != Product.Status.APPROVED:
        messages.error(request, '只有审核通过的商品才能标记为已售出。')
    elif product.sale_status != target:
        if target == Product.SaleStatus.AVAILABLE:
            product.status = Product.Status.PENDING
            product.rejection_reason = ''
            product.reviewed_at = None
            product.reviewed_by = None
        product.sale_status = target
        product.revision += 1
        product.save()
        messages.success(request, '状态已更新并保留历史。重新上架需要管理员审核。' if target == Product.SaleStatus.AVAILABLE else '状态已更新并保留历史。')
    return redirect('center')

@login_required
@require_POST
def favorite(request, pk):
    product = get_object_or_404(visible_products(request), pk=pk)
    saved, created = Favorite.objects.get_or_create(user=request.user, product=product)
    if not created: saved.delete()
    return redirect('detail', pk=pk)

@login_required
@require_POST
def predict(request):
    try:
        payload = json.loads(request.body)
        title, description = payload.get('title', ''), payload.get('description', '')
        if not isinstance(title, str) or not isinstance(description, str): raise ValueError('请输入文本。')
        if not title.strip() or not description.strip(): raise ValueError('请先填写商品标题和描述。')
        if len(title) > 100 or len(description) > 3000: raise ValueError('标题最多 100 字，描述最多 3000 字。')
    except (ValueError, AttributeError, TypeError) as exc:
        return JsonResponse({'error': str(exc) if not isinstance(exc, json.JSONDecodeError) else '请求格式错误。'}, status=400)
    try:
        category, algorithm = classify(title, description)
        return JsonResponse({'category': category, 'label': dict(CATEGORIES)[category], 'algorithm': algorithm})
    except ValueError as exc:
        return JsonResponse({'error': str(exc)}, status=503)
    except Exception:
        return JsonResponse({'error': '分类模型不可用，请运行 python manage.py train_model 后重启服务；仍可手动选择类别。'}, status=503)
