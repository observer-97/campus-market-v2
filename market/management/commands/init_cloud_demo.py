"""Explicit, idempotent cloud demo bootstrap. Never logs the administrator password."""
import io
import os
from PIL import Image, ImageDraw
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from market.models import Product, Profile


class Command(BaseCommand):
    help = '构建阶段初始化独立的云端功能演示演示；不导入本机用户、不覆盖已有密码和商品。'

    @transaction.atomic
    def handle(self, *args, **options):
        User = get_user_model()
        username = os.environ.get('CAMPUS_ADMIN_USERNAME', '').strip()
        password = os.environ.get('CAMPUS_ADMIN_PASSWORD', '')
        if not username or not password:
            raise CommandError('请先在 Vercel 设置私有 CAMPUS_ADMIN_USERNAME 和 CAMPUS_ADMIN_PASSWORD。')
        if username in {'demo_student', 'demo_seller', 'demo_buyer'}:
            raise CommandError('管理员不能使用公开演示账号的名称。')
        try:
            if len(password) < 16 or password.startswith('REPLACE_'):
                raise ValidationError('管理员密码至少 16 字符。')
            validate_password(password, User(username=username))
        except ValidationError as exc:
            raise CommandError('管理员密码不满足要求，请生成新的随机密码。') from exc
        admin = User.objects.filter(username=username).first()
        if admin:
            if not (admin.is_active and admin.is_staff and admin.is_superuser):
                raise CommandError('管理员同名账号已存在且权限不符，拒绝自动提权。请更换管理员用户名。')
        else:
            admin = User.objects.create_superuser(username=username, email='', password=password)
            self.stdout.write('已创建独立管理员。密码不会写入日志；再次部署不会重置密码。')
        existing = set(Product.objects.values_list('pk', flat=True))
        call_command('init_demo', stdout=self.stdout)
        call_command('init_trade_demo', stdout=self.stdout)
        for name, campus in [('demo_student', 'tian'), ('demo_seller', 'jiang'), ('demo_buyer', 'ming')]:
            Profile.objects.get_or_create(user=User.objects.get(username=name), defaults={
                'campus': campus, 'is_public': name != 'demo_buyer', 'bio': '公开功能演示演示账号，请勿填写真实隐私。'})
        count = 0
        for product in Product.objects.exclude(pk__in=existing).filter(owner__username__in=['demo_student', 'demo_seller']):
            # Only new, explicitly marked sample products are pre-approved by this bootstrap.
            if '演示' not in product.description:
                continue
            image = Image.new('RGB', (720, 480), {'study': '#dce8d5', 'digital': '#d9e6f1', 'sports': '#f4e7cd', 'daily': '#e9dcf0'}[product.category])
            draw = ImageDraw.Draw(image)
            draw.rounded_rectangle((240, 110, 480, 370), radius=25, fill='#ffffff', outline='#345648', width=6)
            draw.text((275, 225), product.category.upper() + ' / DEMO', fill='#345648')
            data = io.BytesIO()
            image.save(data, format='PNG')
            product.image.save('demo.png', ContentFile(data.getvalue()), save=False)
            product.status = Product.Status.APPROVED
            product.reviewed_by = admin
            product.reviewed_at = timezone.now()
            product.save()
            count += 1
        self.stdout.write(f'云端初始化完成：新增并审核 {count} 件明确标识的演示商品；已有数据保持原样。')
