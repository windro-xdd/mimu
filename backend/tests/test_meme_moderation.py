import io
import tempfile
import unittest
from pathlib import Path

from backend.app import create_app
from backend.services.storage import LocalStorageService


class MemeModerationFlowTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)

        storage_dir = Path(self.temp_dir.name) / "uploads"
        storage_dir.mkdir(parents=True, exist_ok=True)

        self.storage_service = LocalStorageService(
            base_path=storage_dir,
            base_url="/media",
        )

        self.db_path = Path(self.temp_dir.name) / "memes.sqlite"
        self.app = create_app(storage_service=self.storage_service, db_path=self.db_path)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()

    def _upload_meme(self, caption: str = "Test meme", filename: str = "meme.jpg") -> dict:
        response = self.client.post(
            "/api/memes/upload",
            data={
                "caption": caption,
                "image": (io.BytesIO(b"fake-image-data"), filename),
            },
            content_type="multipart/form-data",
            headers={
                "X-User-Id": "user-123",
                "X-User-Role": "user",
            },
        )
        self.assertEqual(response.status_code, 201)
        payload = response.get_json()
        self.assertIsNotNone(payload)
        return payload

    def test_upload_and_approve_flow(self) -> None:
        meme_payload = self._upload_meme()
        meme_id = meme_payload["id"]

        pending_response = self.client.get(
            "/admin/pending",
            headers={
                "X-User-Id": "admin-1",
                "X-User-Role": "admin",
            },
        )
        self.assertEqual(pending_response.status_code, 200)
        pending_payload = pending_response.get_json()
        self.assertEqual(len(pending_payload["data"]), 1)
        self.assertEqual(pending_payload["data"][0]["status"], "pending")

        approve_response = self.client.post(
            f"/admin/approve/{meme_id}",
            headers={
                "X-User-Id": "admin-1",
                "X-User-Role": "admin",
            },
        )
        self.assertEqual(approve_response.status_code, 200)
        approved_payload = approve_response.get_json()
        self.assertEqual(approved_payload["status"], "approved")
        self.assertTrue(approved_payload["is_promoted"])
        self.assertFalse(approved_payload["is_flagged"])

        pending_after_response = self.client.get(
            "/admin/pending",
            headers={
                "X-User-Id": "admin-1",
                "X-User-Role": "admin",
            },
        )
        self.assertEqual(pending_after_response.status_code, 200)
        self.assertEqual(pending_after_response.get_json()["data"], [])

    def test_reject_marks_meme_flagged(self) -> None:
        meme_payload = self._upload_meme(filename="meme.png")
        meme_id = meme_payload["id"]

        reject_response = self.client.post(
            f"/admin/reject/{meme_id}",
            json={"reason": "Inappropriate content"},
            headers={
                "X-User-Id": "admin-2",
                "X-User-Role": "admin",
            },
        )
        self.assertEqual(reject_response.status_code, 200)
        rejection_payload = reject_response.get_json()
        self.assertEqual(rejection_payload["status"], "rejected")
        self.assertTrue(rejection_payload["is_flagged"])
        self.assertEqual(rejection_payload["rejection_reason"], "Inappropriate content")

    def test_admin_routes_require_admin_role(self) -> None:
        self._upload_meme()

        unauthorized_response = self.client.get(
            "/admin/pending",
            headers={
                "X-User-Id": "user-456",
                "X-User-Role": "user",
            },
        )
        self.assertEqual(unauthorized_response.status_code, 403)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
