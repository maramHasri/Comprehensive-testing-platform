import unittest

from app.utils.invitation_token import (
    InvitationTokenInvalid,
    decode_invitation_token,
    generate_invitation_token,
)


class InvitationTokenTestCase(unittest.TestCase):
    def test_should_generate_and_decode_signed_invite_token(self) -> None:
        token = generate_invitation_token(
            invitation_id=12,
            organization_id=45,
            role="student",
            target_email="student@example.com",
        )
        payload = decode_invitation_token(token, max_age_seconds=60)
        self.assertEqual(payload["invitation_id"], 12)
        self.assertEqual(payload["organization_id"], 45)
        self.assertEqual(payload["role"], "student")
        self.assertEqual(payload["target_email"], "student@example.com")

    def test_should_fail_for_tampered_token(self) -> None:
        token = generate_invitation_token(
            invitation_id=1,
            organization_id=2,
            role="student",
        )
        with self.assertRaises(InvitationTokenInvalid):
            decode_invitation_token(f"{token}tampered", max_age_seconds=60)


if __name__ == "__main__":
    unittest.main()
