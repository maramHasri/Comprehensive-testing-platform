import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import create_app


class InvitationLifecycleRoutesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    @patch("app.routes.auth.routes.validate_student_invite_token")
    def test_should_validate_auth_invite_and_return_next_action_register(
        self,
        mock_validate_student_invite_token,
    ) -> None:
        invitation = SimpleNamespace(id=10, expires_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00"))
        payload = {"organization_id": 99, "role": "student", "target_email": "student@example.com"}
        mock_validate_student_invite_token.return_value = (invitation, payload, None)
        response = self.client.get("/auth/invite/signed.token.value")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["valid"], True)
        self.assertEqual(body["organization_id"], 99)
        self.assertEqual(body["role"], "student")
        self.assertEqual(body["next_action"], "register")

    @patch("app.routes.auth.routes.get_jwt_identity")
    @patch("app.routes.auth.routes.validate_student_invite_token")
    def test_should_validate_auth_invite_and_return_next_action_accept_for_authenticated_user(
        self,
        mock_validate_student_invite_token,
        mock_get_jwt_identity,
    ) -> None:
        invitation = SimpleNamespace(id=11, expires_at=SimpleNamespace(isoformat=lambda: "2026-01-01T00:00:00"))
        payload = {"organization_id": 44, "role": "student", "target_email": None}
        mock_validate_student_invite_token.return_value = (invitation, payload, None)
        mock_get_jwt_identity.return_value = "7"
        response = self.client.get("/auth/invite/another.signed.token")
        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["valid"], True)
        self.assertEqual(body["next_action"], "accept")

    @patch("app.routes.invitations.routes.db.session.commit")
    @patch("app.routes.invitations.routes._ensure_student_membership")
    @patch("app.routes.invitations.routes._create_student_user_from_payload")
    @patch("app.routes.invitations.routes.validate_student_invite_token")
    def test_should_redeem_invitation_then_be_idempotent_on_reuse(
        self,
        mock_validate_student_invite_token,
        mock_create_student_user_from_payload,
        mock_ensure_student_membership,
        mock_commit,
    ) -> None:
        invitation = SimpleNamespace(id=22, used_count=0)
        payload = {"organization_id": 55, "role": "student", "target_email": "new.student@example.com"}
        user = SimpleNamespace(id=123)
        mock_validate_student_invite_token.return_value = (invitation, payload, None)
        mock_create_student_user_from_payload.return_value = (user, None)
        mock_ensure_student_membership.side_effect = [True, False]
        request_body = {
            "token": "signed.invite.token",
            "email": "new.student@example.com",
            "password": "StrongPass123",
            "full_name": "New Student",
        }
        response_first = self.client.post("/api/invitations/redeem", json=request_body)
        self.assertEqual(response_first.status_code, 200)
        first_body = response_first.get_json()
        self.assertEqual(first_body["membership_created"], True)
        self.assertEqual(first_body["organization_id"], 55)
        self.assertEqual(invitation.used_count, 1)
        response_second = self.client.post("/api/invitations/redeem", json=request_body)
        self.assertEqual(response_second.status_code, 200)
        second_body = response_second.get_json()
        self.assertEqual(second_body["membership_created"], False)
        self.assertEqual(invitation.used_count, 1)
        self.assertEqual(mock_commit.call_count, 2)


if __name__ == "__main__":
    unittest.main()
