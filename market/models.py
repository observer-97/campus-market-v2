from django.conf import settings
from django.db import models

CATEGORIES = [('study', '学习用品'), ('digital', '电子用品'), ('sports', '体育用品'), ('daily', '生活用品')]
CAMPUSES = [('ming', '明故宫校区'), ('jiang', '将军路校区'), ('tian', '天目湖校区')]

class Product(models.Model):
    class Status(models.TextChoices):
        PENDING = 'pending', '待审核'
        APPROVED = 'approved', '已上架'
        REJECTED = 'rejected', '已驳回'
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='发布者', on_delete=models.CASCADE)
    title = models.CharField('商品标题', max_length=100)
    description = models.TextField('商品描述', max_length=3000)
    price = models.DecimalField('价格（元）', max_digits=8, decimal_places=2)
    category = models.CharField('商品类别', max_length=12, choices=CATEGORIES)
    contact = models.CharField('联系信息', max_length=200)
    image = models.ImageField('商品图片（可选）', upload_to='products/%Y/%m/', blank=True)
    created_at = models.DateTimeField('发布时间', auto_now_add=True)
    status = models.CharField('上架状态', max_length=12, choices=Status.choices, default=Status.PENDING)
    rejection_reason = models.TextField('驳回理由', max_length=1000, blank=True)
    revision = models.PositiveIntegerField('提交版本', default=1)
    reviewed_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='审核人', on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_products')
    reviewed_at = models.DateTimeField('审核时间', null=True, blank=True)
    class SaleStatus(models.TextChoices):
        AVAILABLE = 'available', '在售'
        SOLD = 'sold', '已售出'
        OFFLINE = 'offline', '已下架'
    sale_status = models.CharField('交易状态', max_length=12, choices=SaleStatus.choices, default=SaleStatus.AVAILABLE)
    def __str__(self):
        return self.title
    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at', '-id']
        constraints = [models.CheckConstraint(condition=models.Q(price__gt=0), name='positive_price')]

class Favorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='收藏用户', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, verbose_name='收藏商品', on_delete=models.CASCADE, related_name='favorites')
    def __str__(self):
        return f'{self.user} 收藏 {self.product}'
    class Meta:
        verbose_name = '收藏记录'
        verbose_name_plural = '收藏记录'
        constraints = [models.UniqueConstraint(fields=['user', 'product'], name='unique_favorite')]

class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_public = models.BooleanField('公开个人中心', default=False)
    bio = models.CharField('个人简介', max_length=300, blank=True)
    campus = models.CharField('所在校区', max_length=12, choices=CAMPUSES, blank=True)
    default_contact = models.CharField('默认联系方式', max_length=200, blank=True)
    class Meta:
        verbose_name = '用户个人资料'
        verbose_name_plural = '用户个人资料'

class Conversation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='buy_conversations')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sell_conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['product', 'buyer'], name='one_product_buyer_chat'), models.CheckConstraint(condition=~models.Q(buyer=models.F('seller')), name='different_chat_participants')]

class ChatMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at', 'id']

class DemoOrder(models.Model):
    class State(models.TextChoices):
        PROPOSED = 'proposed', '待卖家确认地点与交易意愿'
        ACCEPTED = 'accepted', '待买家模拟付款'
        PAID = 'paid', '模拟款项已托管，待线下交付'
        COMPLETED = 'completed', '已确认收货，模拟款项已结算'
        CANCELED = 'canceled', '已取消 / 已退款'
    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='orders')
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='purchases')
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='sales')
    title = models.CharField(max_length=100)
    amount_cents = models.PositiveIntegerField()
    product_revision = models.PositiveIntegerField()
    campus = models.CharField(max_length=12, choices=CAMPUSES)
    meeting_place = models.CharField('双方约定的具体地点', max_length=200)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PROPOSED)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        verbose_name = '模拟交易订单'
        verbose_name_plural = '模拟交易订单'
        constraints = [models.UniqueConstraint(fields=['product'], condition=models.Q(state__in=['accepted', 'paid']), name='one_reserved_order_per_product'), models.UniqueConstraint(fields=['conversation'], condition=models.Q(state__in=['proposed', 'accepted', 'paid']), name='one_open_order_per_conversation'), models.CheckConstraint(condition=models.Q(amount_cents__gt=0), name='positive_order_amount')]
        ordering = ['-created_at', '-id']
    @property
    def amount(self):
        from decimal import Decimal
        return Decimal(self.amount_cents) / 100

class DemoWallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    balance_cents = models.PositiveIntegerField(default=0)
    grant_claimed = models.BooleanField(default=False)
    class Meta:
        verbose_name = '模拟余额'
        verbose_name_plural = '模拟余额'
    @property
    def balance(self):
        from decimal import Decimal
        return Decimal(self.balance_cents) / 100

class WalletEntry(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    order = models.ForeignKey(DemoOrder, on_delete=models.PROTECT, null=True, blank=True)
    kind = models.CharField(max_length=12, choices=[('grant', '领取模拟余额'), ('pay', '模拟付款到托管'), ('release', '模拟托管结算'), ('refund', '模拟退款')])
    delta_cents = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = '模拟资金流水'
        verbose_name_plural = '模拟资金流水'
        ordering = ['-created_at', '-id']
        constraints = [models.UniqueConstraint(fields=['order', 'kind'], name='unique_order_wallet_operation')]
    @property
    def amount(self):
        from decimal import Decimal
        return Decimal(self.delta_cents) / 100

class OrderEvent(models.Model):
    order = models.ForeignKey(DemoOrder, on_delete=models.PROTECT, related_name='events')
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    state = models.CharField(max_length=12, choices=DemoOrder.State.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        verbose_name = '模拟交易历史'
        verbose_name_plural = '模拟交易历史'
        ordering = ['created_at', 'id']

class ProductHistory(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='history')
    title = models.CharField('当时的商品标题', max_length=100)
    status = models.CharField('当时的审核状态', max_length=12, choices=Product.Status.choices)
    sale_status = models.CharField('当时的交易状态', max_length=12, choices=Product.SaleStatus.choices)
    created_at = models.DateTimeField('记录时间', auto_now_add=True)
    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = '商品历史记录'
        verbose_name_plural = '商品历史记录'

class ProductReport(models.Model):
    REASONS = [('fraud', '疑似欺诈'), ('prohibited', '违禁或违规商品'), ('spam', '广告或垃圾内容'), ('other', '其他问题')]
    STATES = [('pending', '待处理'), ('resolved', '已处理'), ('dismissed', '不予受理')]
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='举报人', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, verbose_name='被举报商品', null=True, on_delete=models.SET_NULL)
    product_title = models.CharField('举报时商品标题', max_length=100)
    reason = models.CharField('举报类型', max_length=12, choices=REASONS)
    details = models.TextField('举报说明', max_length=2000)
    state = models.CharField('处理状态', max_length=12, choices=STATES, default='pending')
    result = models.TextField('处理结果', max_length=2000, blank=True)
    handled_by = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name='处理人', null=True, blank=True, on_delete=models.SET_NULL, related_name='handled_reports')
    handled_at = models.DateTimeField('处理时间', null=True, blank=True)
    created_at = models.DateTimeField('举报时间', auto_now_add=True)
    class Meta:
        ordering = ['-created_at', '-id']
        verbose_name = '商品举报'
        verbose_name_plural = '商品举报'
        constraints = [models.UniqueConstraint(fields=['reporter', 'product'], condition=models.Q(state='pending'), name='one_pending_report_per_user_product')]


class StoredImage(models.Model):
    """Small classroom uploads, persisted alongside application data on PostgreSQL."""
    name = models.CharField(max_length=180, primary_key=True)
    data = models.BinaryField(editable=False)
    content_type = models.CharField(max_length=32)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = '云端商品图片'
        verbose_name_plural = '云端商品图片'
