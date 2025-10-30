import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from backend.services.storage import (
    LocalStorageService,
    S3StorageService,
    StorageConfig,
    get_storage_service,
)


class LocalStorageServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp_dir.cleanup)
        self.service = LocalStorageService(
            base_path=self.tmp_dir.name,
            base_url="/media",
        )

    def test_upload_and_generate_url(self) -> None:
        data = io.BytesIO(b"example-data")
        key = self.service.upload(data, "images/photo.png")

        expected_path = Path(self.tmp_dir.name) / "images" / "photo.png"
        self.assertTrue(expected_path.exists())
        self.assertEqual(expected_path.read_bytes(), b"example-data")
        self.assertEqual(key, "images/photo.png")
        self.assertEqual(self.service.generate_url(key), "/media/images/photo.png")

    def test_delete_removes_uploaded_file(self) -> None:
        key = self.service.upload(io.BytesIO(b"to delete"), "docs/report.pdf")
        target_path = Path(self.tmp_dir.name) / "docs" / "report.pdf"
        self.assertTrue(target_path.exists())

        self.service.delete(key)
        self.assertFalse(target_path.exists())

    def test_upload_rejects_path_traversal(self) -> None:
        with self.assertRaises(ValueError):
            self.service.upload(io.BytesIO(b"invalid"), "../outside.txt")


class S3StorageServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_client = mock.Mock()
        self.service = S3StorageService(
            bucket_name="test-bucket",
            region_name="us-east-1",
            client=self.mock_client,
            public_base_url="https://cdn.example.com/images",
            use_presigned_urls=True,
        )

    def test_upload_invokes_boto_client(self) -> None:
        data = io.BytesIO(b"s3 data")
        key = self.service.upload(
            data,
            "avatars/user.png",
            content_type="image/png",
            extra_args={"Metadata": {"uploaded-by": "test"}},
        )

        self.assertEqual(key, "avatars/user.png")
        self.mock_client.upload_fileobj.assert_called_once()
        _, args, kwargs = self.mock_client.upload_fileobj.mock_calls[0]
        self.assertEqual(args[1], "test-bucket")
        self.assertEqual(args[2], "avatars/user.png")
        extra_args = kwargs["ExtraArgs"]
        self.assertEqual(extra_args["ContentType"], "image/png")
        self.assertEqual(extra_args["Metadata"], {"uploaded-by": "test"})

    def test_delete_invokes_boto_client(self) -> None:
        self.service.delete("avatars/user.png")
        self.mock_client.delete_object.assert_called_once_with(
            Bucket="test-bucket", Key="avatars/user.png"
        )

    def test_generate_presigned_url(self) -> None:
        self.mock_client.generate_presigned_url.return_value = "https://signed.example"  # type: ignore[assignment]
        url = self.service.generate_url("avatars/user.png", expires_in=120)

        self.assertEqual(url, "https://signed.example")
        self.mock_client.generate_presigned_url.assert_called_once_with(
            "get_object",
            Params={"Bucket": "test-bucket", "Key": "avatars/user.png"},
            ExpiresIn=120,
        )

    def test_public_url_when_presigned_disabled(self) -> None:
        service = S3StorageService(
            bucket_name="test-bucket",
            region_name="us-east-1",
            client=self.mock_client,
            public_base_url="https://cdn.example.com/images",
            use_presigned_urls=False,
        )
        url = service.generate_url("avatars/user.png")
        self.assertEqual(url, "https://cdn.example.com/images/avatars/user.png")
        self.mock_client.generate_presigned_url.assert_not_called()


class StorageConfigFactoryTestCase(unittest.TestCase):
    def test_local_service_from_environment(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "local",
                "STORAGE_LOCAL_BASE_URL": "/uploads",
            },
            clear=True,
        ):
            # Ensure classmethod can create config and factory returns a local service.
            config = StorageConfig.from_env()
            service = get_storage_service(config, local_base_path=tempfile.mkdtemp())
            self.assertIsInstance(service, LocalStorageService)

    def test_s3_service_from_environment(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "STORAGE_BACKEND": "s3",
                "STORAGE_S3_BUCKET": "bucket-name",
                "AWS_DEFAULT_REGION": "us-west-2",
                "STORAGE_S3_USE_PRESIGNED_URLS": "true",
            },
            clear=True,
        ):
            mock_boto3 = mock.Mock()
            mock_client = mock.Mock()
            mock_boto3.client.return_value = mock_client

            with mock.patch("backend.services.storage.boto3", mock_boto3):
                service = get_storage_service()

            self.assertIsInstance(service, S3StorageService)
            mock_boto3.client.assert_called_once_with(
                "s3",
                region_name="us-west-2",
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
