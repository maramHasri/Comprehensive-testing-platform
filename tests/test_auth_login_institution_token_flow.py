import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from app import create_app
from app.services import auth_service


class LoginInstitutionTokenFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self) -> None:
        self.app_context.pop()

    @patch("app.services.auth_service.create_session")
    @patch("app.services.auth_service.create_access_token")
    @patch("app.services.auth_service.build_user_jwt_claims")
    @patch("app.services.auth_service.get_user_by_email")
    @patch("app.services.auth_service.Institution")
    def test_should_create_session_and_use_numeric_identity(
        self,
        mock_institution_model: MagicMock,
        mock_get_user_by_email: MagicMock,
        mock_build_claims: MagicMock,
        mock_create_access_token: MagicMock,
        mock_create_session: MagicMock,
    ) -> None:
        mock_institution = MagicMock()
        mock_institution.password = auth_service._hash_password("pass12345")
        mock_institution.trust_level = "basic"
        mock_institution_model.query.get.return_value = mock_institution
        mock_user = MagicMock()
        mock_user.id = 101
        mock_user.is_active = True
        mock_get_user_by_email.return_value = mock_user
        mock_build_claims.return_value = {"roles": ["admin"], "memberships": [{"organization_id": 1}]}
        mock_create_access_token.return_value = "fake.jwt.token"
        result, status = auth_service.login_institution("admin@example.com", "pass12345", lang="en")
        self.assertEqual(status, 200)
        self.assertEqual(result, {"token": "fake.jwt.token"})
        self.assertEqual(mock_create_access_token.call_count, 1)
        kwargs = mock_create_access_token.call_args.kwargs
        self.assertEqual(kwargs["identity"], "101")
        self.assertIn("additional_claims", kwargs)
        self.assertEqual(kwargs["additional_claims"]["role"], "institution")
        self.assertEqual(kwargs["additional_claims"]["trust_level"], "basic")
        self.assertTrue(kwargs["additional_claims"]["jti"])
        self.assertEqual(mock_create_session.call_count, 1)
        session_args = mock_create_session.call_args.args
        self.assertEqual(session_args[0], 101)
        self.assertEqual(session_args[1], kwargs["additional_claims"]["jti"])
        self.assertIsNotNone(session_args[2])


if __name__ == "__main__":
    unittest.main()
