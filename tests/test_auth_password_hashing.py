import unittest

from app.services import auth_service


class AuthPasswordHashingTestCase(unittest.TestCase):
    def test_should_hash_password_with_bcrypt_prefix(self) -> None:
        hashed_password = auth_service._hash_password("MyStrongPass123")
        self.assertNotEqual(hashed_password, "MyStrongPass123")
        self.assertTrue(
            hashed_password.startswith("$2a$")
            or hashed_password.startswith("$2b$")
            or hashed_password.startswith("$2y$")
        )

    def test_should_verify_bcrypt_hash_correctly(self) -> None:
        hashed_password = auth_service._hash_password("MyStrongPass123")
        self.assertTrue(
            auth_service._verify_institution_password(hashed_password, "MyStrongPass123")
        )
        self.assertFalse(
            auth_service._verify_institution_password(hashed_password, "WrongPassword")
        )

    def test_should_reject_non_bcrypt_stored_password(self) -> None:
        self.assertFalse(
            auth_service._verify_institution_password("legacy_plain_password", "legacy_plain_password")
        )


if __name__ == "__main__":
    unittest.main()
