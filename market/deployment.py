"""Readiness diagnostics contain no credentials or user data."""
import os
import uuid
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.models import LogEntry, CHANGE
from django.core.files.storage import default_storage
from django.db import connection
from django.http import HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from .ml import classify
from .models import Product, StoredImage, CATEGORIES
from .storage import DatabaseImageStorage

RELEASE = '2026-11-06-fullstack-v2'
PROBE_NAME = '上线持久化验收标记'


def readiness():
    checks = {}
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            connected = cursor.fetchone()[0] == 1
        tables = set(connection.introspection.table_names())
        needed = {'auth_user', 'django_session', 'django_admin_log', 'market_product',
                  'market_favorite', 'market_profile', 'market_conversation', 'market_chatmessage',
                  'market_demoorder', 'market_demowallet', 'market_walletentry',
                  'market_orderevent', 'market_producthistory', 'market_productreport', 'market_storedimage'}
        checks['database'] = connected
        checks['schema'] = needed.issubset(tables)
        encrypted = False
        if connection.vendor == 'postgresql':
            with connection.cursor() as cursor:
                cursor.execute('SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()')
                row = cursor.fetchone()
                encrypted = bool(row and row[0])
        checks['database_tls'] = encrypted
    except Exception:
        checks.update(database=False, schema=False, database_tls=False)
    checks['database_media'] = isinstance(default_storage, DatabaseImageStorage)
    checks['frontend_files'] = all((settings.BASE_DIR / 'templates' / name).is_file() for name in ['listing.html', 'base.html'])
    try:
        category, _ = classify('羽毛球拍', '体育课训练使用，附拍套，线床完整')
        checks['model'] = category in dict(CATEGORIES)
    except Exception:
        checks['model'] = False
    vercel = settings.IS_VERCEL and os.environ.get('VERCEL_ENV') == 'production'
    checks['vercel_production'] = vercel
    checks['postgresql'] = connection.vendor == 'postgresql'
    running = all(checks.get(k, False) for k in ['database', 'schema', 'model', 'frontend_files'])
    return {'service': 'campus-market', 'release': RELEASE, 'ok': running,
            'cloud_ready': running and all(checks.values()), 'checks': checks}


@require_GET
def health(request):
    data = readiness()
    response = JsonResponse(data, status=200 if data['ok'] else 503)
    response['Cache-Control'] = 'no-store'
    return response


@admin.site.admin_view
@require_http_methods(['GET', 'POST'])
def deployment_check(request):
    if not request.user.is_superuser:
        return HttpResponseForbidden('仅超级管理员可查看上线验收。')
    if request.method == 'POST':
        if request.POST.get('action') == 'save_probe':
            LogEntry.objects.create(user=request.user, object_repr=PROBE_NAME,
                                    action_flag=CHANGE, change_message='验收标记 ' + uuid.uuid4().hex[:16])
            messages.success(request, '已写入数据库。请记下标记，在另一个浏览器登录管理员后核对；重新部署后也应保留。')
        return redirect('deployment_check')
    data = readiness()
    labels = {'vercel_production': '前后端运行于 Vercel Production', 'postgresql': '使用 PostgreSQL 持久化数据库',
              'database': '后端可以连接数据库', 'schema': '账号、商品、私信、订单等数据库表完整',
              'database_tls': '数据库连接已加密', 'database_media': '上传图片写入数据库',
              'model': '保存的模型可以实际预测', 'frontend_files': '前端页面模板随项目部署'}
    marker = LogEntry.objects.filter(object_repr=PROBE_NAME, content_type__isnull=True).order_by('-action_time', '-id').first()
    return render(request, 'admin/deployment_check.html', {
        **admin.site.each_context(request), 'title': '完整上线验收', 'report': data,
        'rows': [(labels[key], value) for key, value in data['checks'].items()], 'marker': marker})
