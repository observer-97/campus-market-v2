from django.contrib import admin
from django import forms
from django.utils import timezone
from django.utils.html import format_html
from django.urls import reverse
from .forms import ProductForm
from .models import Product, Favorite, DemoOrder, DemoWallet, WalletEntry, OrderEvent, Profile, ProductReport

admin.site.site_header = '青禾集 · 数据管理后台'
admin.site.site_title = '青禾集管理'
admin.site.index_title = '校园二手平台管理'

class AdminProductForm(ProductForm):
    """Reuse all publishing validation, including real image parsing and size limits."""
    review_revision = forms.IntegerField(widget=forms.HiddenInput)
    class Meta(ProductForm.Meta):
        fields = ['owner', *ProductForm.Meta.fields, 'status', 'rejection_reason']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['review_revision'].initial = self.instance.revision
        self.fields['status'].help_text = '选择“已上架”表示审核通过；选择“已驳回”时必须填写下方理由。'
        self.fields['rejection_reason'].help_text = '理由会显示给卖家，最多 1000 字；非驳回状态会自动清空。'

    def clean(self):
        data = super().clean()
        if self.instance.pk:
            current = Product.objects.get(pk=self.instance.pk)
            if current.orders.filter(state__in=['accepted', 'paid']).exists() and any(name in self.changed_data for name in ['owner', 'title', 'description', 'price', 'category', 'contact', 'image', 'status']):
                raise forms.ValidationError('商品有进行中的交易，请先由双方完成或取消交易，后台不能直接改动商品。')
            if data.get('review_revision') != current.revision:
                raise forms.ValidationError('卖家已提交新版本，请刷新页面重新查看商品后再审核。')
        reason = (data.get('rejection_reason') or '').strip()
        if data.get('status') == Product.Status.REJECTED and not reason:
            self.add_error('rejection_reason', '驳回商品时必须填写具体理由。')
        if data.get('status') != Product.Status.REJECTED:
            reason = ''
        data['rejection_reason'] = reason
        return data

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = AdminProductForm
    list_display = ['id', 'title', 'review_link', 'status', 'sale_status', 'category', 'price', 'owner', 'created_at']
    list_display_links = ['id', 'title']
    list_filter = ['status', 'sale_status', 'category', 'created_at']
    search_fields = ['title', 'description', 'owner__username', 'contact']
    autocomplete_fields = ['owner']
    list_select_related = ['owner']
    readonly_fields = ['created_at', 'image_preview', 'revision', 'reviewed_by', 'reviewed_at', 'sale_status']
    fields = ['owner', 'title', 'description', 'price', 'category', 'contact', 'image', 'image_preview', 'status', 'sale_status', 'rejection_reason', 'revision', 'review_revision', 'reviewed_by', 'reviewed_at', 'created_at']
    date_hierarchy = 'created_at'
    list_per_page = 20

    @admin.display(description='操作')
    def review_link(self, obj):
        return format_html(
            '<a class="button" href="{}" aria-label="审核商品：{}" style="display:inline-block;white-space:nowrap">审核</a>',
            reverse('admin:market_product_change', args=[obj.pk]),
            obj.title,
        )

    @admin.display(description='图片预览')
    def image_preview(self, obj):
        if not obj or not obj.image:
            return '未上传图片'
        return format_html('<img src="{}" alt="商品图片" style="max-width:240px;max-height:180px;object-fit:contain">', obj.image.url)

    def get_changeform_initial_data(self, request):
        return {'owner': request.user.pk}

    def save_model(self, request, obj, form, change):
        if change and any(name in form.changed_data for name in ['owner', 'title', 'description', 'price', 'category', 'contact', 'image']):
            obj.revision += 1
        if obj.status == Product.Status.PENDING:
            obj.reviewed_by = None
            obj.reviewed_at = None
        else:
            obj.reviewed_by = request.user
            obj.reviewed_at = timezone.now()
        super().save_model(request, obj, form, change)

@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'product']
    search_fields = ['user__username', 'product__title']
    autocomplete_fields = ['user', 'product']
    list_select_related = ['user', 'product']
    list_per_page = 20

class ReadOnlySimulationAdmin(admin.ModelAdmin):
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False
    def get_readonly_fields(self, request, obj=None):
        return [field.name for field in self.model._meta.fields]

@admin.register(DemoOrder)
class DemoOrderAdmin(ReadOnlySimulationAdmin):
    list_display = ['id', 'title', 'buyer', 'seller', 'state', 'amount', 'campus', 'created_at']
    list_filter = ['state', 'campus']
    search_fields = ['title', 'buyer__username', 'seller__username']

@admin.register(DemoWallet)
class DemoWalletAdmin(ReadOnlySimulationAdmin):
    list_display = ['user', 'balance', 'grant_claimed']

@admin.register(WalletEntry)
class WalletEntryAdmin(ReadOnlySimulationAdmin):
    list_display = ['id', 'user', 'order', 'kind', 'amount', 'created_at']
    list_filter = ['kind']

@admin.register(OrderEvent)
class OrderEventAdmin(ReadOnlySimulationAdmin):
    list_display = ['order', 'actor', 'state', 'created_at']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'campus', 'is_public']
    list_filter = ['campus', 'is_public']
    search_fields = ['user__username']
    autocomplete_fields = ['user']

class ReportHandlingForm(forms.ModelForm):
    class Meta:
        model = ProductReport
        fields = ['state', 'result']
    def clean(self):
        data = super().clean()
        result = (data.get('result') or '').strip()
        if data.get('state') != 'pending' and not result:
            self.add_error('result', '完成处理或不予受理时，必须填写处理结果。')
        data['result'] = result
        return data

@admin.register(ProductReport)
class ProductReportAdmin(admin.ModelAdmin):
    form = ReportHandlingForm
    list_display = ['id', 'product_title', 'reporter', 'reason', 'state', 'handled_by', 'created_at']
    list_display_links = ['id', 'product_title']
    list_filter = ['state', 'reason']
    search_fields = ['product_title', 'reporter__username', 'details']
    readonly_fields = ['reporter', 'product', 'product_title', 'reason', 'details', 'created_at', 'handled_by', 'handled_at']
    fields = [*readonly_fields, 'state', 'result']
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
    def save_model(self, request, obj, form, change):
        if any(name in form.changed_data for name in ['state', 'result']):
            obj.handled_by = request.user
            obj.handled_at = timezone.now()
        super().save_model(request, obj, form, change)
