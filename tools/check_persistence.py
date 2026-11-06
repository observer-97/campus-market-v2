"""Two-process persistence test, restricted to isolated local/CI databases."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / '.packages312'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['write', 'read'])
    parser.add_argument('--state', required=True)
    parser.add_argument('--local-db')
    args = parser.parse_args()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    from django.conf import settings
    if args.local_db:
        if settings.IS_VERCEL or os.environ.get('DATABASE_URL'):
            raise SystemExit('本机验证模式不能使用云端或已有 DATABASE_URL。')
        path = Path(args.local_db).resolve()
        if path == (ROOT / 'db.sqlite3').resolve():
            raise SystemExit('拒绝修改项目原有数据库。')
        path.parent.mkdir(parents=True, exist_ok=True)
        settings.DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': path}}
    elif not (os.environ.get('CI') == 'true' and settings.DATABASES['default'].get('HOST') in ['localhost', '127.0.0.1', 'postgres']):
        raise SystemExit('仅允许明确隔离的本机数据库或 CI localhost 数据库；禁止在真实生产数据上自动写入测试。')
    settings.STORAGES = {'default': {'BACKEND': 'market.storage.DatabaseImageStorage'},
                         'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'}}
    import django
    django.setup()
    from PIL import Image
    from django.contrib.auth import get_user_model
    from django.core.files.uploadedfile import SimpleUploadedFile
    from django.core.management import call_command
    from django.test import Client
    from market.models import Product, Profile, Favorite, ChatMessage, DemoOrder
    from market.ml import classify
    state_path = Path(args.state)
    def new_client():
        return Client(enforce_csrf_checks=True, HTTP_X_FORWARDED_PROTO='https')
    def post(client, url, values=None, **options):
        client.get(url if url in ['/register/', '/login/', '/admin/login/'] else '/')
        values = values or {}
        if options.get('content_type') == 'application/json':
            return client.post(url, json.dumps(values), HTTP_X_CSRFTOKEN=client.cookies['csrftoken'].value, **options)
        return client.post(url, {**values, 'csrfmiddlewaretoken': client.cookies['csrftoken'].value}, **options)
    if args.stage == 'write':
        if state_path.exists():
            raise SystemExit('状态文件已存在，请使用新的隔离输出目录。')
        call_command('migrate', interactive=False, verbosity=0)
        suffix = uuid.uuid4().hex[:12]
        seller, buyer, manager = new_client(), new_client(), new_client()
        usernames = ['probe_seller_' + suffix, 'probe_buyer_' + suffix]
        password = 'Probe-' + uuid.uuid4().hex
        for client, name in zip([seller, buyer], usernames):
            result = post(client, '/register/', {'username': name, 'password1': password, 'password2': password})
            assert result.status_code == 302, 'Registration failed'
        User = get_user_model()
        owner = User.objects.get(username=usernames[0])
        Profile.objects.update_or_create(user=owner, defaults={'campus': 'jiang', 'is_public': True})
        admin = User.objects.create_superuser('probe_admin_' + suffix, '', password)
        assert post(manager, '/admin/login/', {'username': admin.username, 'password': password, 'next': '/admin/'}).status_code == 302
        image = io.BytesIO()
        Image.new('RGB', (40, 30), 'green').save(image, format='PNG')
        data = {'title': '持久化验收教材' + suffix, 'description': '仅供隔离验收的学习教材，不是真实商品', 'price': '12.50', 'category': 'study', 'contact': '模拟联系信息'}
        assert post(seller, '/publish/', {**data, 'image': SimpleUploadedFile('probe.png', image.getvalue(), content_type='image/png')}).status_code == 302
        product = Product.objects.get(owner=owner)
        result = post(manager, f'/admin/market/product/{product.pk}/change/', {**data, 'owner': owner.pk, 'status': 'approved', 'rejection_reason': '', 'review_revision': product.revision, '_save': '保存'})
        assert result.status_code == 302, 'Moderation failed'
        product.refresh_from_db()
        assert product.status == 'approved'
        assert post(buyer, f'/products/{product.pk}/favorite/').status_code == 302
        chat = post(buyer, f'/products/{product.pk}/chat/')['Location']
        assert post(buyer, chat, {'body': '请在将军路南区操场北入口面交，课堂验收消息'}).status_code == 302
        assert post(buyer, chat + 'propose/', {'campus': 'jiang', 'meeting_place': '将军路南区操场北入口'}).status_code == 302
        order = DemoOrder.objects.get(product=product)
        assert post(seller, f'/orders/{order.pk}/action/', {'action': 'accept'}).status_code == 302
        assert post(buyer, '/trades/grant/').status_code == 302
        assert post(buyer, f'/orders/{order.pk}/action/', {'action': 'pay'}).status_code == 302
        order.refresh_from_db()
        assert order.state == 'paid', 'Simulated payment failed'
        assert post(manager, '/admin/deployment-check/', {'action': 'save_probe'}).status_code == 302
        state = {'product': product.pk, 'order': order.pk, 'chat': chat,
                 'title': product.title, 'image_url': product.image.url, 'image_sha256': hashlib.sha256(image.getvalue()).hexdigest(),
                 'seller_cookie': seller.cookies[settings.SESSION_COOKIE_NAME].value,
                 'buyer_cookie': buyer.cookies[settings.SESSION_COOKIE_NAME].value,
                 'admin_cookie': manager.cookies[settings.SESSION_COOKIE_NAME].value}
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
        print('WRITE PASS: registered, uploaded, moderated, favorited, chatted, paid and saved database marker')
    else:
        state = json.loads(state_path.read_text(encoding='utf-8'))
        seller, buyer, manager = new_client(), new_client(), new_client()
        for client, key in [(seller, 'seller_cookie'), (buyer, 'buyer_cookie'), (manager, 'admin_cookie')]:
            client.cookies[settings.SESSION_COOKIE_NAME] = state[key]
        assert state['title'] in seller.get('/mine/').content.decode()
        assert state['title'] in buyer.get('/favorites/').content.decode()
        assert '将军路南区操场北入口' in buyer.get(state['chat']).content.decode()
        image = new_client().get(state['image_url'])
        assert image.status_code == 200 and hashlib.sha256(image.content).hexdigest() == state['image_sha256']
        assert '验收标记' in manager.get('/admin/deployment-check/').content.decode()
        assert DemoOrder.objects.get(pk=state['order']).state == 'paid'
        title, description = '羽毛球拍', '体育课训练使用，附拍套，线床完整'
        response = post(buyer, '/api/predict/', {'title': title, 'description': description}, content_type='application/json')
        assert response.status_code == 200 and response.json()['category'] == classify(title, description)[0]
        assert post(buyer, f'/orders/{state["order"]}/action/', {'action': 'confirm', 'received': 'on'}).status_code == 302
        assert DemoOrder.objects.get(pk=state['order']).state == 'completed'
        assert Product.objects.get(pk=state['product']).sale_status == 'sold'
        print('READ PASS: separate process reused sessions and persisted image/favorite/chat/escrow; real prediction and receipt completed')


if __name__ == '__main__':
    main()
