from django.test import TestCase, override_settings
from django.urls import reverse
from django.conf import settings
from .models import OAuthState, User
import responses
import jwt

class OAuthTests(TestCase):
    def setUp(self):
        self.login_url = reverse('github-login')
        self.callback_url = reverse('github-callback')

    def test_login_creates_state_and_redirects(self):
        resp = self.client.get(self.login_url)
        self.assertEqual(resp.status_code, 302)
        # state created
        st = OAuthState.objects.first()
        self.assertIsNotNone(st)

    @responses.activate
    def test_callback_exchanges_code_and_returns_jwt(self):
        # prepare state
        import secrets
        state = secrets.token_urlsafe(16)
        OAuthState.objects.create(state=state)

        # mock token exchange
        responses.add(
            responses.POST,
            'https://github.com/login/oauth/access_token',
            json={'access_token': 'gho_testtoken'},
            status=200
        )
        # mock profile fetch
        responses.add(
            responses.GET,
            'https://api.github.com/user',
            json={'id': 12345, 'login': 'alice', 'email': 'a@example.com'},
            status=200
        )

        resp = self.client.get(self.callback_url, {'code': 'abc', 'state': state})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        token = data.get('token')
        self.assertIsNotNone(token)
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        self.assertIn('sub', payload)
        self.assertTrue(User.objects.filter(github_id=12345).exists())
