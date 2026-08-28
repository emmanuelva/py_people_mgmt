import time

from django.test import TestCase
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.test import APITestCase

from core.models import User
from core.permissions import StaffRequiredForCreateMixin


class UserManagerTests(TestCase):
    def test_create_user_requires_email(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email=None, password='pw')

    def test_create_user_defaults_to_non_staff_non_superuser(self):
        user = User.objects.create_user(email='user@example.com', password='pw')
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.check_password('pw'))

    def test_create_superuser_sets_staff_and_superuser_flags(self):
        user = User.objects.create_superuser(email='admin@example.com', password='pw')
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_rejects_is_staff_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email='admin@example.com', password='pw', is_staff=False)

    def test_create_superuser_rejects_is_superuser_false(self):
        with self.assertRaises(ValueError):
            User.objects.create_superuser(email='admin@example.com', password='pw', is_superuser=False)


class SoftDeleteModelTests(TestCase):
    def test_delete_sets_deleted_at_instead_of_removing_row(self):
        user = User.objects.create_user(email='user@example.com', password='pw')
        user.delete()
        self.assertIsNotNone(user.deleted_at)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

    def test_save_updates_updated_at(self):
        user = User.objects.create_user(email='user@example.com', password='pw')
        original_updated_at = user.updated_at
        time.sleep(0.001)
        user.first_name = 'Changed'
        user.save()
        self.assertGreater(user.updated_at, original_updated_at)


class StaffRequiredForCreateMixinTests(TestCase):
    def test_create_action_requires_admin_permission(self):
        class DummyView(StaffRequiredForCreateMixin):
            action = 'create'

        permissions = DummyView().get_permissions()
        self.assertEqual(len(permissions), 1)
        self.assertIsInstance(permissions[0], IsAdminUser)

    def test_other_actions_delegate_to_super(self):
        class DummyBase:
            def get_permissions(self):
                return ['base-permissions']

        class DummyView(StaffRequiredForCreateMixin, DummyBase):
            action = 'list'

        self.assertEqual(DummyView().get_permissions(), ['base-permissions'])


class TokenAuthenticationAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='user@example.com', password='correct-password')

    def test_obtain_token_with_valid_credentials(self):
        response = self.client.post(
            '/api/token/', {'email': 'user@example.com', 'password': 'correct-password'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_obtain_token_with_invalid_credentials(self):
        response = self.client.post(
            '/api/token/', {'email': 'user@example.com', 'password': 'wrong-password'}, format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token(self):
        obtain = self.client.post(
            '/api/token/', {'email': 'user@example.com', 'password': 'correct-password'}, format='json'
        )
        response = self.client.post('/api/token/refresh/', {'refresh': obtain.data['refresh']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)

    def test_verify_valid_access_token(self):
        obtain = self.client.post(
            '/api/token/', {'email': 'user@example.com', 'password': 'correct-password'}, format='json'
        )
        response = self.client.post('/api/token/verify/', {'token': obtain.data['access']}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_verify_invalid_token_is_rejected(self):
        response = self.client.post('/api/token/verify/', {'token': 'not-a-real-token'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_access_token_authenticates_api_requests(self):
        obtain = self.client.post(
            '/api/token/', {'email': 'user@example.com', 'password': 'correct-password'}, format='json'
        )
        response = self.client.get('/api/people/', HTTP_AUTHORIZATION=f'Bearer {obtain.data["access"]}')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_request_without_token_is_unauthorized(self):
        response = self.client.get('/api/people/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)


class APIDocsTests(APITestCase):
    def test_schema_is_served(self):
        response = self.client.get('/api/schema/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_swagger_ui_is_served(self):
        response = self.client.get('/api/schema/swagger-ui/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_redoc_is_served(self):
        response = self.client.get('/api/schema/redoc/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
