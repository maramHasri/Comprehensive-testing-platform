import unittest

from app import create_app


class AuthVerifyRoutesTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app()
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def test_should_return_html_for_path_verify_route(self) -> None:
        response = self.client.get("/auth/verify/invalid-token-for-route-check")
        self.assertNotEqual(response.status_code, 404)
        self.assertEqual(response.content_type, "text/html; charset=utf-8")

    def test_should_return_json_error_for_missing_query_token(self) -> None:
        response = self.client.get("/auth/verify")
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertIn("message", payload)


if __name__ == "__main__":
    unittest.main()
