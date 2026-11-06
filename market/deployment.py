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
PROBE_NAME = '���߳־û����ձ��'


def database_uses_tls():
    # Inspect the application's physical libpq connection, including through a pooler.
    # pg_stat_ssl can describe the pooler's internal database hop instead.
    if connection.vendor != 'postgresql':
        return False
    pgconn = getattr(connection.connection, 'pgconn', None)
    return bool(pgconn is not None and pgconn.ssl_in_use)


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
        checks['database_tls'] = database_uses_tls()
    except Exception:
        checks.update(database=False, schema=False, database_tls=False)
    checks['database_media'] = isinstance(default_storage, DatabaseImageStorage)
    checks['frontend_files'] = all((settings.BASE_DIR / 'templates' / name).is_file() for name in ['listing.html', 'base.html'])
    try:
        category, _ = classify('��ë����', '������ѵ��ʹ�ã������ף��ߴ�����')
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
        return HttpResponseForbidden('����������Ա�ɲ鿴�������ա�')
    if request.method == 'POST':
        if request.POST.get('action') == 'save_probe':
            LogEntry.objects.create(user=request.user, object_repr=PROBE_NAME,
                                    action_flag=CHANGE, change_message='���ձ�� ' + uuid.uuid4().hex[:16])
            messages.success(request, '��д�����ݿ⡣����±�ǣ�����һ���������¼����Ա��˶ԣ����²����ҲӦ������')
        return redirect('deployment_check')
    data = readiness()
    labels = {'vercel_production': 'ǰ��������� Vercel Production', 'postgresql': 'ʹ�� PostgreSQL �־û����ݿ�',
              'database': '��˿����������ݿ�', 'schema': '�˺š���Ʒ��˽�š����������ݿ������',
              'database_tls': '���ݿ������Ѽ���', 'database_media': '�ϴ�ͼƬд�����ݿ�',
              'model': '�����ģ�Ϳ���ʵ��Ԥ��', 'frontend_files': 'ǰ��ҳ��ģ������Ŀ����'}
    marker = LogEntry.objects.filter(object_repr=PROBE_NAME, content_type__isnull=True).order_by('-action_time', '-id').first()
    return render(request, 'admin/deployment_check.html', {
        **admin.site.each_context(request), 'title': '������������', 'report': data,
        'rows': [(labels[key], value) for key, value in data['checks'].items()], 'marker': marker})
