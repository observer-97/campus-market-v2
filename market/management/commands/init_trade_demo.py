from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from market.models import Product, Profile

class Command(BaseCommand):
    help = '创建独立的模拟交易卖家、买家及待审核示例商品；不覆盖已有数据。'
    def handle(self, *args, **kwargs):
        users = {}
        for name, campus in [('demo_seller', 'jiang'), ('demo_buyer', 'ming')]:
            user, created = get_user_model().objects.get_or_create(username=name)
            users[name] = user
            if created:
                user.set_password('CampusTrade2026!')
                user.save()
                self.stdout.write(f'新建课堂账号 {name} / CampusTrade2026!')
                Profile.objects.get_or_create(user=user, defaults={'campus': campus, 'is_public': name == 'demo_seller', 'bio': '课堂模拟交易账号，非真实个人资料'})
            else:
                self.stdout.write(f'{name} 已存在，保留其原密码、校区及公开设置。')
        product, created = Product.objects.get_or_create(owner=users['demo_seller'], title='【模拟交易演示】线性代数教材', defaults={'description': '课堂模拟交易示例，不是真实出售商品。可演示私信协商将军路校区南区操场北入口面交。', 'price': '35.50', 'category': 'study', 'contact': '演示联系信息，无真实联系方式'})
        self.stdout.write(f'示例商品 #{product.pk}，状态：{product.get_status_display()}。若待审核，请管理员先在后台审核通过。')
