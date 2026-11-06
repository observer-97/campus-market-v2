from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from market.models import Product

class Command(BaseCommand):
    help = '幂等创建演示账号和商品，不覆盖既有账号或商品。'
    def handle(self, *args, **options):
        user, created = get_user_model().objects.get_or_create(username='demo_student')
        if created:
            user.set_password('CampusDemo2026!')
            user.save()
            self.stdout.write('新建演示账号 demo_student / CampusDemo2026!（仅限课堂模拟，请勿填写真实隐私）')
        else:
            self.stdout.write('账号已存在，保留原密码及数据。')
        examples = [
            ('同济高等数学 · 上下册', '【演示商品】课本保存完好，有少量课堂笔记。希望能帮到下一位同学。', '28.00', 'study'),
            ('无线降噪蓝牙耳机', '【演示商品】通勤和自习用，充电盒齐全。左耳外壳有轻微划痕。', '89.00', 'digital'),
            ('入门羽毛球拍一对', '【演示商品】社团活动用过，线床完整，附拍套，适合日常锻炼。', '45.00', 'sports'),
            ('宿舍透明收纳箱', '【演示商品】搬宿舍转让，带盖可叠放，放书和衣物都方便。', '15.00', 'daily'),
            ('英语六级真题与解析', '【演示商品】只写过前两套，答案册齐全，备考完成后转让。', '18.00', 'study'),
            ('轻便无线鼠标', '【演示商品】蓝牙连接稳定，静音按键，适合图书馆使用。', '32.00', 'digital'),
            ('瑜伽垫与拉伸带', '【演示商品】六毫米运动垫，防滑表面，已清洁，附收纳绑带。', '25.00', 'sports'),
            ('不锈钢保温杯', '【演示商品】五百毫升，杯盖不漏水，杯底有使用痕迹。', '20.00', 'daily'),
        ]
        count = 0
        for title, description, price, category in examples:
            _, added = Product.objects.get_or_create(owner=user, title=title, defaults={'description': description, 'price': price, 'category': category, 'contact': '演示联系信息：campus_demo（无真实联系方式）'})
            count += added
        self.stdout.write(f'新增 {count} 件演示商品；已有内容保持原样。')
