import secrets
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

class Command(BaseCommand):
    help = '创建本地管理员并一次性输出随机密码；不修改已有账号或权限。'

    def add_arguments(self, parser):
        parser.add_argument('--username', default='campus_admin')

    def handle(self, *args, **options):
        username = options['username']
        User = get_user_model()
        existing = User.objects.filter(username=username).first()
        if existing:
            if not (existing.is_active and existing.is_staff and existing.is_superuser):
                raise CommandError('同名账号已存在且不是有效超级管理员，不会自动提权；请使用其他 --username。')
            self.stdout.write('管理员已存在，保留原密码；需要重置时运行 changepassword。')
            return
        password = secrets.token_urlsafe(18)
        User.objects.create_superuser(username=username, email='', password=password)
        self.stdout.write(f'管理员用户名：{username}\n初始密码：{password}\n入口：/admin/\n请保存密码；此密码只在本次输出，登录后可修改。')
