import unittest

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import (
    Announcement,
    Institution,
    InstitutionCategory,
    LostFoundItem,
    MarketplaceItem,
    Post,
)


class CampusConnectWebTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            ADMIN_USERNAME='test-admin',
            ADMIN_PASSWORD_HASH=generate_password_hash('correct-test-password'),
        )
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()

    def test_search_returns_matching_platform_content(self):
        category = InstitutionCategory(name='University')
        db.session.add(category)
        db.session.flush()
        db.session.add_all([
            Post(poster_name='Amina', title='Campus study group',
                 body='Join our campus study group.'),
            MarketplaceItem(poster_name='Amina', poster_contact='0700000000',
                            title='Campus desk', description='A study desk.',
                            category='Furniture'),
            LostFoundItem(poster_name='Amina', poster_contact='0700000000',
                          item_type='found', title='Campus keys',
                          description='Keys near campus.', location='Campus library'),
            Announcement(title='Campus update', body='Campus events this week.'),
            Institution(name='Campus University', abbreviation='CU',
                        category_id=category.id, active=True),
            Post(poster_name='Amina', title='Deleted campus post',
                 body='This should not appear.', deleted=True),
        ])
        db.session.commit()

        response = self.client.get('/api/search?q=campus')

        self.assertEqual(response.status_code, 200)
        results = response.get_json()['results']
        self.assertEqual(
            {result['section'] for result in results},
            {'community', 'marketplace', 'lostandfound', 'announcement', 'institution'},
        )
        self.assertNotIn('Deleted campus post', {result['title'] for result in results})

    def test_search_rejects_empty_or_oversized_queries(self):
        self.assertEqual(self.client.get('/api/search?q=').status_code, 400)
        self.assertEqual(self.client.get('/api/search?q=' + ('a' * 101)).status_code, 400)

    def test_homepage_renders_brand_and_platform_search(self):
        response = self.client.get('/')

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Kila Kitu Made Easy.', response.data)
        self.assertIn(b'platform-search-input', response.data)
        self.assertIn(b'id="theme-select"', response.data)
        self.assertIn(b'value="system"', response.data)
        self.assertIn(b'value="light"', response.data)
        self.assertIn(b'value="dark"', response.data)
        self.assertIn(b'class="brand-name"', response.data)
        self.assertIn(b'class="theme-icon"', response.data)
        self.assertNotIn(b'>Appearance</span>', response.data)
        self.assertIn(b'id="opening-confetti"', response.data)

    def test_admin_login_uses_configured_password_hash_and_versioned_session(self):
        response = self.client.post('/api/admin/login', json={
            'username': 'test-admin',
            'password': 'correct-test-password',
        })

        self.assertEqual(response.status_code, 200)
        token = response.get_json()['token']
        self.assertTrue(token.startswith('v2_'))
        self.assertEqual(
            self.client.get('/api/admin/ads', headers={'X-Admin-Token': token}).status_code,
            200,
        )
        self.assertEqual(
            self.client.get('/api/admin/ads', headers={'X-Admin-Token': 'legacy-token'}).status_code,
            401,
        )

    def test_admin_login_is_disabled_without_credentials(self):
        self.app.config['ADMIN_USERNAME'] = None
        response = self.client.post('/api/admin/login', json={
            'username': 'test-admin',
            'password': 'correct-test-password',
        })

        self.assertEqual(response.status_code, 503)


if __name__ == '__main__':
    unittest.main()
