import json
import tempfile
import unittest
from pathlib import Path
from wsgiref.util import setup_testing_defaults

from backend.services.excuse_api import create_excuse_app
from backend.services.excuses import (
    ExcuseSeedConfig,
    ExcuseSeedError,
    ExcuseService,
    get_excuse_service,
)


class ExcuseServiceTestCase(unittest.TestCase):
    def test_default_fixture_is_loaded(self) -> None:
        service = get_excuse_service()
        self.assertIsInstance(service, ExcuseService)
        self.assertGreater(len(service.excuses), 0)
        self.assertIn(service.get_random_excuse(), service.excuses)

    def test_custom_fixture_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fixture_path = Path(temp_dir) / "excuses.json"
            fixture_path.write_text(
                json.dumps([
                    " Custom excuse one ",
                    "Custom excuse one",
                    "Custom excuse two",
                ])
            )

            config = ExcuseSeedConfig(fixture_path=fixture_path)
            service = get_excuse_service(config)

            self.assertEqual(service.excuses, ("Custom excuse one", "Custom excuse two"))

    def test_missing_fixture_raises(self) -> None:
        config = ExcuseSeedConfig(fixture_path=Path("/does/not/exist.json"))
        with self.assertRaises(ExcuseSeedError):
            get_excuse_service(config)


class ExcuseAPITestCase(unittest.TestCase):
    def setUp(self) -> None:
        config = ExcuseSeedConfig(excuses=["Always this excuse"])
        self.service = get_excuse_service(config)
        self.app = create_excuse_app(self.service)

    def _request(self, path: str = "/api/excuse", method: str = "GET"):
        environ = {}
        setup_testing_defaults(environ)
        environ["REQUEST_METHOD"] = method
        environ["PATH_INFO"] = path

        status_holder: dict = {}
        headers: list = []

        def start_response(status, response_headers, exc_info=None):  # type: ignore[override]
            status_holder["status"] = status
            headers.extend(response_headers)

        body = b"".join(self.app(environ, start_response))
        header_map = {key: value for key, value in headers}

        return status_holder["status"], header_map, body

    def test_get_excuse_returns_seeded_value(self) -> None:
        status, header_map, body = self._request()

        self.assertEqual(status, "200 OK")
        self.assertEqual(header_map.get("Content-Type"), "application/json")

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["excuse"], "Always this excuse")

    def test_method_not_allowed(self) -> None:
        status, header_map, body = self._request(method="POST")

        self.assertEqual(status, "405 Method Not Allowed")
        self.assertEqual(header_map.get("Allow"), "GET")

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["detail"], "Method Not Allowed")

    def test_not_found(self) -> None:
        status, header_map, body = self._request(path="/")

        self.assertEqual(status, "404 Not Found")

        payload = json.loads(body.decode("utf-8"))
        self.assertEqual(payload["detail"], "Not Found")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
