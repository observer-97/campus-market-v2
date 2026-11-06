from datetime import datetime
from zoneinfo import ZoneInfo
from django.contrib.auth import get_user_model
from django.test import TestCase
from .models import Product, Profile


class CampusFilterTests(TestCase):
    def setUp(self):
        self.products = {}
        for code in ['ming', 'jiang', 'tian', 'unset', 'missing']:
            owner = get_user_model().objects.create_user('campus_' + code)
            if code != 'missing':
                Profile.objects.create(user=owner, campus='' if code == 'unset' else code, is_public=False)
            self.products[code] = Product.objects.create(owner=owner, title='校区教材' + code,
                description='课程教材', price='20', category='study', contact='演示', status='approved')

    def test_each_campus_and_all_include_unknown(self):
        response = self.client.get('/')
        self.assertEqual(response.context['page'].paginator.count, 5)
        self.assertContains(response, '商品所在校区')
        self.assertContains(response, '全部校区')
        for code, name in [('ming', '明故宫校区'), ('jiang', '将军路校区'), ('tian', '天目湖校区')]:
            with self.subTest(campus=code):
                response = self.client.get('/', {'campus': code})
                self.assertEqual(list(response.context['page']), [self.products[code]])
                self.assertContains(response, f'value="{code}" selected')
                self.assertIn(name, response.context['active_filters'])
        response = self.client.get('/', {'campus': ''})
        self.assertEqual(response.context['page'].paginator.count, 5)
        self.assertEqual(response.context['active_filters'], [])
        # A private personal homepage does not hide the campus already public on details.
        Profile.objects.filter(user=self.products['jiang'].owner).update(campus='tian')
        self.assertEqual(self.client.get('/', {'campus': 'jiang'}).context['page'].paginator.count, 0)
        self.assertEqual(self.client.get('/', {'campus': 'tian'}).context['page'].paginator.count, 2)

    def test_combination_and_pagination_preserve_campus(self):
        owner = self.products['jiang'].owner
        for i in range(15):
            product = Product.objects.create(owner=owner, title=f'组合筛选教材{i}', description='课程文本',
                price=10+i, category='study', contact='演示', status='approved')
            Product.objects.filter(pk=product.pk).update(created_at=datetime(2026, 10, 22, 23, 59,
                tzinfo=ZoneInfo('Asia/Hong_Kong')))
        params = {'q': '组合筛选教材', 'campus': 'jiang', 'category': 'study', 'min_price': '10',
            'max_price': '30', 'start_date': '2026-10-22', 'end_date': '2026-10-22', 'sort': 'price_desc'}
        response = self.client.get('/', params)
        self.assertEqual(response.context['page'].paginator.count, 15)
        self.assertEqual(response.context['page'][0].price, 24)
        for text in ['campus=jiang', 'category=study', 'min_price=10', 'max_price=30',
                     'start_date=2026-10-22', 'end_date=2026-10-22', 'sort=price_desc', 'page=2']:
            self.assertContains(response, text)
        response = self.client.get('/', {**params, 'page': '2'})
        self.assertEqual(len(response.context['page']), 3)
        self.assertContains(response, 'value="jiang" selected')
        self.assertEqual(self.client.get('/', {**params, 'campus': 'ming'}).context['page'].paginator.count, 0)

    def test_invalid_campus_and_visibility_rules(self):
        for state in ['pending', 'rejected']:
            Product.objects.create(owner=self.products['jiang'].owner, title='不公开' + state,
                description='测试', price='20', category='study', contact='演示', status=state)
        for state in ['sold', 'offline']:
            Product.objects.create(owner=self.products['jiang'].owner, title='不在售' + state,
                description='测试', price='20', category='study', contact='演示', status='approved', sale_status=state)
        self.assertEqual(list(self.client.get('/', {'campus': 'jiang'}).context['page']), [self.products['jiang']])
        response = self.client.get('/', {'campus': 'unexpected'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('campus', response.context['search_form'].errors)
        self.assertEqual(response.context['page'].paginator.count, 0)
        self.assertContains(response, 'class="filter-menu" open')
