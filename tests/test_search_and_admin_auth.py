from io import BytesIO
import os
import tempfile
import json
import unittest
from unittest.mock import patch

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import (
    Announcement,
    FeaturePost,
    Institution,
    InstitutionCategory,
    LostFoundItem,
    MarketplaceItem,
    Post,
)
from app.ratelimit import _hits, _lock


class CampusConnectWebTestCase(unittest.TestCase):
    def setUp(self):
        with _lock:
            _hits.clear()
        self.app = create_app()
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite://',
            ADMIN_USERNAME='test-admin',
            ADMIN_PASSWORD_HASH=generate_password_hash('correct-test-password'),
        )
        self.upload_dir = tempfile.TemporaryDirectory()
        self.app.config['UPLOAD_FOLDER'] = self.upload_dir.name
        self.context = self.app.app_context()
        self.context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.context.pop()
        self.upload_dir.cleanup()

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

    def test_search_includes_public_feature_listings_but_not_confessions(self):
        self.client.post('/api/features', json={
            'kind': 'jobs', 'title': 'Campus design internship',
            'body': 'Apply for a design internship.', 'author_name': 'Amina',
        })
        self.client.post('/api/features', json={
            'kind': 'confessions', 'title': 'Campus secret',
            'body': 'This should stay out of public search.',
        })
        results = self.client.get('/api/search?q=campus').get_json()['results']
        self.assertIn('Campus design internship', {item['title'] for item in results})
        self.assertNotIn('Campus secret', {item['title'] for item in results})

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
        self.assertNotIn(b'data-section="features"', response.data)
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

    def test_feature_categories_can_be_created_and_listed(self):
        categories = [
            'jobs', 'accommodation', 'resources', 'deals', 'events',
            'polls', 'confessions', 'lost_documents', 'services',
        ]
        for kind in categories:
            payload = {
                'kind': kind,
                'title': f'{kind} listing',
                'body': 'A useful CampusConnect listing.',
                'author_name': 'Test Student',
                'options': ['Option A', 'Option B'] if kind == 'polls' else None,
                'event_date': '2027-01-15' if kind == 'events' else None,
            }
            response = self.client.post('/api/features', json=payload)
            self.assertEqual(response.status_code, 201, response.get_json())
            listed = self.client.get(f'/api/features?kind={kind}')
            self.assertEqual(listed.status_code, 200)
            self.assertEqual(listed.get_json()['items'][0]['kind'], kind)

    def test_resource_files_can_be_uploaded_and_downloaded(self):
        response = self.client.post('/api/features', data={
            'kind': 'resources',
            'title': 'Biology revision notes',
            'body': 'Study notes for the biology unit.',
            'author_name': 'Amina',
            'resource_file': (BytesIO(b'%PDF-1.4 test notes'), 'biology-notes.pdf'),
        }, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 201, response.get_json())
        resource = response.get_json()
        self.assertEqual(resource['file_name'], 'biology-notes.pdf')
        self.assertTrue(resource['file_url'].startswith('/api/uploads/'))
        listed = self.client.get('/api/features?kind=resources').get_json()['items'][0]
        self.assertEqual(listed['file_name'], 'biology-notes.pdf')
        self.assertEqual(listed['file_url'], resource['file_url'])
        download = self.client.get(resource['file_url'] + '?download=1')
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment', download.headers['Content-Disposition'])
        self.assertEqual(download.data, b'%PDF-1.4 test notes')
        download.close()
        self.assertEqual(len(os.listdir(self.upload_dir.name)), 1)

    def test_resource_file_upload_rejects_unsupported_extensions(self):
        response = self.client.post('/api/features', data={
            'kind': 'resources',
            'title': 'Unexpected file',
            'body': 'This file type must not be stored.',
            'author_name': 'Amina',
            'resource_file': (BytesIO(b'not a document'), 'script.html'),
        }, content_type='multipart/form-data')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(os.listdir(self.upload_dir.name), [])

    def test_anonymous_and_lost_document_posts_protect_identity_and_contact(self):
        confession = self.client.post('/api/features', json={
            'kind': 'confessions',
            'title': 'A private thought',
            'body': 'I am nervous about exams.',
            'author_name': 'Do not reveal me',
            'contact': 'secret@example.com',
        })
        self.assertEqual(confession.status_code, 201)
        self.assertEqual(confession.get_json()['author_name'], 'Anonymous')
        self.assertIsNone(confession.get_json()['contact'])

        document = self.client.post('/api/features', json={
            'kind': 'lost_documents',
            'title': 'Student ID found',
            'body': 'Found near the library. Contact the front desk.',
            'contact': '0712345678',
        })
        self.assertEqual(document.status_code, 201)
        self.assertNotIn('contact', document.get_json())

    def test_polls_accept_one_vote_per_voter_key(self):
        response = self.client.post('/api/features', json={
            'kind': 'polls',
            'title': 'Best study time?',
            'body': 'When do you focus best?',
            'options': ['Morning', 'Evening'],
        })
        feature_id = response.get_json()['id']
        ballot = {'voter_key': 'test-voter-key-0001', 'option_index': 0}
        vote = self.client.post(f'/api/features/{feature_id}/vote', json=ballot)
        self.assertEqual(vote.status_code, 200)
        self.assertEqual(vote.get_json()['counts'], [1, 0])
        duplicate = self.client.post(f'/api/features/{feature_id}/vote', json=ballot)
        self.assertEqual(duplicate.status_code, 409)

    def test_study_assistant_fails_closed_without_provider_key(self):
        self.app.config['AI_API_KEY'] = None
        response = self.client.post('/api/study-assistant', json={'question': 'Explain algebra'})
        self.assertEqual(response.status_code, 503)

    def test_study_assistant_uses_configured_openai_compatible_provider(self):
        self.app.config.update(
            AI_API_KEY='test-provider-key',
            AI_API_BASE_URL='https://ai.example.test/v1',
            AI_MODEL='test-model',
        )

        class FakeProviderResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self, _limit):
                return json.dumps({
                    'choices': [{'message': {'content': 'Here is a step-by-step explanation.'}}],
                }).encode()

        with patch('app.features.urlopen', return_value=FakeProviderResponse()) as provider:
            response = self.client.post('/api/study-assistant', json={
                'question': 'How does photosynthesis work?',
            })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['answer'], 'Here is a step-by-step explanation.')
        outgoing = provider.call_args.args[0]
        self.assertEqual(outgoing.full_url, 'https://ai.example.test/v1/chat/completions')
        self.assertEqual(outgoing.get_header('Authorization'), 'Bearer test-provider-key')

    def test_study_assistant_rejects_private_provider_endpoints(self):
        self.app.config.update(
            AI_API_KEY='test-provider-key',
            AI_API_BASE_URL='https://127.0.0.1/v1',
        )
        with patch('app.features.urlopen') as provider:
            response = self.client.post('/api/study-assistant', json={
                'question': 'Explain fractions.',
            })
        self.assertEqual(response.status_code, 503)
        provider.assert_not_called()

    def test_feature_moderation_requires_admin_session(self):
        response = self.client.get('/api/admin/features')
        self.assertEqual(response.status_code, 401)

    def test_admin_can_moderate_feature_listings_without_hard_deleting(self):
        created = self.client.post('/api/features', json={
            'kind': 'deals', 'title': 'Campus cafe offer',
            'body': 'Discount for students.', 'author_name': 'Cafe',
        }).get_json()
        login = self.client.post('/api/admin/login', json={
            'username': 'test-admin',
            'password': 'correct-test-password',
        }).get_json()
        headers = {'X-Admin-Token': login['token']}

        self.assertEqual(self.client.get('/api/admin/features', headers=headers).status_code, 200)
        deleted = self.client.delete(
            f"/api/admin/features/{created['id']}", headers=headers
        )
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(
            self.client.get('/api/features?kind=deals').get_json()['items'],
            [],
        )
        self.assertFalse(db.session.get(FeaturePost, created['id']).active)

    def test_events_require_a_valid_date_and_external_links_are_validated(self):
        missing_date = self.client.post('/api/features', json={
            'kind': 'events', 'title': 'Campus talk', 'body': 'Guest speaker',
            'author_name': 'Campus club',
        })
        self.assertEqual(missing_date.status_code, 400)
        invalid_link = self.client.post('/api/features', json={
            'kind': 'resources', 'title': 'Study guide', 'body': 'Review notes',
            'author_name': 'Campus club', 'external_url': 'javascript:alert(1)',
        })
        self.assertEqual(invalid_link.status_code, 400)


if __name__ == '__main__':
    unittest.main()
