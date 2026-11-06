import json
from unittest.mock import patch
from django.contrib.admin.models import LogEntry
from django.contrib.auth import get_user_model
from django.db import OperationalError
from django.test import TestCase, SimpleTestCase, Client, override_settings
from market.deployment import PROBE_NAME, database_uses_tls
from tools.verify_live import verify
import build


class ReadinessTests(TestCase):
    def test_local_backend_not_reported_as_cloud(self):
        response = self.client.get('/api/health/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])
        self.assertFalse(response.json()['cloud_ready'])
        self.assertFalse(response.json()['checks']['vercel_production'])
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertNotContains(response, 'SECRET_KEY')

    def test_real_model_failure_and_database_failure_return_503(self):
        with patch('market.deployment.classify', side_effect=ValueError('private filesystem path')):
            response = self.client.get('/api/health/')
            self.assertEqual(response.status_code, 503)
            self.assertFalse(response.json()['checks']['model'])
            self.assertNotContains(response, 'private filesystem', status_code=503)
        with patch('market.deployment.connection.cursor', side_effect=OperationalError('private database password')):
            response = self.client.get('/api/health/')
            self.assertEqual(response.status_code, 503)
            self.assertFalse(response.json()['checks']['database'])
            self.assertNotContains(response, 'private database password', status_code=503)

    def test_admin_marker_permissions_csrf_and_cross_browser(self):
        User = get_user_model()
        ordinary = User.objects.create_user('release_viewer')
        staff = User.objects.create_user('release_staff', is_staff=True)
        admin = User.objects.create_superuser('release_admin', '', 'AdminRelease2026!')
        self.assertEqual(self.client.get('/admin/deployment-check/').status_code, 302)
        for user, code in [(ordinary, 302), (staff, 403)]:
            self.client.force_login(user)
            self.assertEqual(self.client.get('/admin/deployment-check/').status_code, code)
        self.client.force_login(admin)
        self.assertContains(self.client.get('/admin/deployment-check/'), '������������')
        self.assertFalse(LogEntry.objects.filter(object_repr=PROBE_NAME).exists())
        strict = Client(enforce_csrf_checks=True)
        strict.force_login(admin)
        self.assertEqual(strict.post('/admin/deployment-check/', {'action': 'save_probe'}).status_code, 403)
        self.assertEqual(self.client.post('/admin/deployment-check/', {'action': 'save_probe'}).status_code, 302)
        marker = LogEntry.objects.get(object_repr=PROBE_NAME)
        other = Client()
        other.force_login(admin)
        self.assertContains(other.get('/admin/deployment-check/'), marker.change_message)


class ReleaseToolTests(SimpleTestCase):
    def test_build_rejects_local_and_preview_before_migration(self):
        for values in [{'VERCEL': '0', 'VERCEL_ENV': 'production'}, {'VERCEL': '1', 'VERCEL_ENV': 'preview'}]:
            with patch.dict('os.environ', values), patch('build.subprocess.run') as run:
                with self.assertRaises(SystemExit):
                    build.main()
                run.assert_not_called()

    def test_public_checker_requires_real_cloud_and_assets(self):
        def get(url):
            if url.endswith('/api/health/'):
                return 200, 'application/json', json.dumps({'cloud_ready': True, 'checks': {'vercel_production': True}, 'release': 'test'}).encode()
            if url.endswith('/static/app.css'):
                return 200, 'text/css', b'body {color:black}'
            if '/uploads/' in url:
                return 200, 'image/png', b'example-image'
            return 200, 'text/html', '<title>��̼�</title><link href="/static/app.css"><img src="/uploads/sample.png/">'.encode()
        report = verify('https://campus-example.vercel.app', get)
        self.assertTrue(report['passed'])
        self.assertTrue(report['remaining_manual_checks'])
        with self.assertRaises(ValueError):
            verify('http://localhost:8001', get)
        def missing_backend(url):
            return (200, 'application/json', b'{"cloud_ready":false}') if url.endswith('/api/health/') else get(url)
        with self.assertRaises(ValueError):
            verify('https://campus-example.vercel.app', missing_backend)


class DatabaseTlsTests(SimpleTestCase):
    def test_pooler_uses_actual_client_tls_without_server_query(self):
        from types import SimpleNamespace
        with patch('market.deployment.connection') as db:
            db.vendor = 'postgresql'
            db.connection = SimpleNamespace(pgconn=SimpleNamespace(ssl_in_use=True))
            db.cursor.side_effect = AssertionError('Do not query the pooler backend for client TLS')
            self.assertTrue(database_uses_tls())
            db.cursor.assert_not_called()

    def test_plain_or_non_postgres_connection_is_not_encrypted(self):
        from types import SimpleNamespace
        with patch('market.deployment.connection') as db:
            db.vendor = 'postgresql'
            db.connection = SimpleNamespace(pgconn=SimpleNamespace(ssl_in_use=False))
            self.assertFalse(database_uses_tls())
            db.connection = None
            self.assertFalse(database_uses_tls())
            db.vendor = 'sqlite'
            self.assertFalse(database_uses_tls())
