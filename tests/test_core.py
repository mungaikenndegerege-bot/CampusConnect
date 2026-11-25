import os
import tempfile
import unittest
from unittest.mock import patch

from sqlalchemy import URL
from werkzeug.datastructures import FileStorage

from app import create_app, db
from app.models import Institution
from app.storage import StorageValidationError, upload_asset


class CampusConnectApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        database_path = os.path.join(self.temp_dir.name, 'test.db')
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test-only-secret',
            'SQLALCHEMY_DATABASE_URI': URL.create('sqlite', database=database_path),
            'STORAGE_BACKEND': 'local',
            'UPLOAD_FOLDER': os.path.join(self.temp_dir.name, 'uploads'),
        })
        with self.app.app_context():
            db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.engine.dispose()
        self.temp_dir.cleanup()

    def test_post_owner_token_controls_edits_and_content_persists(self):
        created = self.client.post('/api/posts', json={
            'poster_name': 'Jane Kamau',
            'title': 'Study group',
            'body': 'We are meeting to study.',
        })
        self.assertEqual(created.status_code, 201)
        post = created.get_json()
        self.assertTrue(post['owner_token'])

        rejected = self.client.put(f"/api/posts/{post['id']}", json={
            'owner_token': 'not-the-token',
            'title': 'Changed title',
            'body': 'Changed message',
        })
        self.assertEqual(rejected.status_code, 403)

        updated = self.client.put(f"/api/posts/{post['id']}", json={
            'owner_token': post['owner_token'],
            'title': 'Updated study group',
            'body': 'Updated meeting details.',
        })
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.get_json()['title'], 'Updated study group')
        self.assertNotIn('owner_token_hash', updated.get_json())

        listing = self.client.get('/api/posts').get_json()
        self.assertEqual(listing['items'][0]['title'], 'Updated study group')

    def test_form_marketplace_upload_without_an_image_is_supported(self):
        response = self.client.post('/api/marketplace', data={
            'poster_name': 'Jane Kamau',
            'poster_contact': '0712345678',
            'title': 'Textbook',
            'description': 'A textbook in good condition.',
            'price': '500',
            'category': 'Books',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.get_json()['owner_token'])

    def test_event_and_opportunity_creation(self):
        event = self.client.post('/api/events', data={
            'poster_name': 'Jane Kamau',
            'title': 'Campus careers event',
            'description': 'A campus career and networking event.',
            'venue': 'Main hall',
            'starts_at': '2027-01-15T08:00:00Z',
        })
        self.assertEqual(event.status_code, 201)
        self.assertTrue(event.get_json()['owner_token'])

        opportunity = self.client.post('/api/opportunities', json={
            'poster_name': 'Jane Kamau',
            'opportunity_type': 'internship',
            'title': 'Software internship',
            'organization': 'Campus Labs',
            'description': 'A software development internship opportunity.',
            'application_url': 'https://example.org/apply',
        })
        self.assertEqual(opportunity.status_code, 201)
        self.assertEqual(self.client.get('/api/opportunities').get_json()['total'], 1)

    def test_create_routes_replay_resources_for_idempotency_key(self):
        with self.app.app_context():
            institution = Institution(name='Campus Test University')
            db.session.add(institution)
            db.session.commit()
            institution_id = institution.id
        cases = [
            ('/api/posts', {
                'poster_name': 'Jane Kamau',
                'title': 'Study group',
                'body': 'We are meeting to study.',
            }),
            ('/api/marketplace', {
                'poster_name': 'Jane Kamau',
                'poster_contact': '0712345678',
                'title': 'Textbook',
                'description': 'A textbook in good condition.',
                'price': '500',
                'category': 'Books',
            }),
            ('/api/lostandfound', {
                'poster_name': 'Jane Kamau',
                'poster_contact': '0712345678',
                'item_type': 'lost',
                'title': 'Blue backpack',
                'description': 'Blue backpack with notebooks inside.',
                'location': 'Main library',
            }),
            ('/api/events', {
                'poster_name': 'Jane Kamau',
                'title': 'Campus careers event',
                'description': 'A campus career and networking event.',
                'venue': 'Main hall',
                'starts_at': '2027-01-15T08:00:00Z',
            }),
            ('/api/opportunities', {
                'poster_name': 'Jane Kamau',
                'opportunity_type': 'internship',
                'title': 'Software internship',
                'organization': 'Campus Labs',
                'description': 'A software development internship opportunity.',
                'application_url': 'https://example.org/apply',
            }),
            (f'/api/institutions/{institution_id}/posts', {
                'poster_name': 'Jane Kamau',
                'title': 'Campus discussion',
                'body': 'A discussion for students at the test university.',
                'topic': 'General',
            }),
        ]
        for index, (path, payload) in enumerate(cases):
            with self.subTest(path=path):
                key = f'campusconnect-test-key-{index:02d}'
                first = self.client.post(path, json=payload, headers={'Idempotency-Key': key})
                retry_payload = dict(payload)
                retry_payload['title'] = 'Changed title must not create another resource'
                retry = self.client.post(path, json=retry_payload, headers={'Idempotency-Key': key})

                self.assertEqual(first.status_code, 201)
                self.assertEqual(retry.status_code, 200)
                self.assertEqual(retry.get_json()['id'], first.get_json()['id'])
                self.assertEqual(retry.get_json()['owner_token'], first.get_json()['owner_token'])

        with self.app.app_context():
            from app.models import IdempotencyRecord
            self.assertEqual(IdempotencyRecord.query.count(), len(cases))
            self.assertEqual(db.session.get(Institution, institution_id).community.post_count, 1)

    def test_idempotency_key_length_is_validated(self):
        response = self.client.post('/api/posts', json={
            'poster_name': 'Jane Kamau',
            'title': 'Study group',
            'body': 'We are meeting to study.',
        }, headers={'Idempotency-Key': 'short'})
        self.assertEqual(response.status_code, 400)

    def test_invalid_upload_signature_is_rejected(self):
        upload = FileStorage(
            stream=__import__('io').BytesIO(b'not an image'),
            filename='photo.png',
            content_type='image/png',
        )
        with self.app.app_context():
            with self.assertRaises(StorageValidationError):
                upload_asset(upload, 'post_image', 1024, {'png'})

    def test_admin_login_fails_closed_without_environment_credentials(self):
        with patch.dict(os.environ, {'ADMIN_USERNAME': '', 'ADMIN_PASSWORD': ''}):
            response = self.client.post('/api/admin/login', json={
                'username': 'admin',
                'password': 'password',
            })
        self.assertEqual(response.status_code, 503)

    def test_health_check_includes_database_connectivity(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})


if __name__ == '__main__':
    unittest.main()
