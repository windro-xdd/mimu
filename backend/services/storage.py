from __future__ import annotations

import io
import os
import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, BinaryIO, Dict, Optional, Union, cast

try:  # pragma: no cover - optional dependency
    import boto3  # type: ignore[import]
except ImportError:  # pragma: no cover - optional dependency
    boto3 = None  # type: ignore[assignment]


BinarySource = Union[BinaryIO, bytes, bytearray]


def _coerce_binary_stream(file_obj: BinarySource) -> BinaryIO:
    """Ensure the provided object can be consumed as a binary stream."""
    if isinstance(file_obj, (bytes, bytearray)):
        return io.BytesIO(file_obj)

    if not hasattr(file_obj, "read"):
        raise TypeError("file_obj must be a binary file-like object or bytes-like data.")

    stream = cast(BinaryIO, file_obj)
    if hasattr(stream, "seek"):
        stream.seek(0)
    return stream


def _normalize_storage_key(key: str) -> str:
    """Normalise and validate storage keys to prevent path traversal."""
    if not isinstance(key, str) or not key.strip():
        raise ValueError("Storage key must be a non-empty string.")

    cleaned = key.strip().replace("\\", "/").lstrip("/")
    segments = [segment for segment in cleaned.split("/") if segment]

    if not segments:
        raise ValueError("Storage key resolves to an empty path.")

    for segment in segments:
        if segment in {".", ".."}:
            raise ValueError("Storage key cannot contain path traversal segments.")

    return "/".join(segments)


def _to_bool(value: Optional[Union[str, bool]], default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class StorageConfig:
    """Configuration container for storage backends."""

    backend: str = "local"
    local_base_path: Union[str, Path] = field(
        default_factory=lambda: Path(__file__).resolve().parent.parent / "uploads"
    )
    local_base_url: Optional[str] = "/uploads"
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    s3_endpoint_url: Optional[str] = None
    s3_use_presigned_urls: Union[bool, str] = True
    s3_public_base_url: Optional[str] = None
    s3_default_acl: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_session_token: Optional[str] = None

    def __post_init__(self) -> None:
        self.backend = (self.backend or "local").lower()

        self.local_base_path = Path(self.local_base_path).expanduser()

        if self.local_base_url:
            sanitized = self.local_base_url.strip()
            self.local_base_url = sanitized.rstrip("/") if sanitized != "/" else "/"

        if self.s3_public_base_url:
            self.s3_public_base_url = self.s3_public_base_url.rstrip("/")

        self.s3_use_presigned_urls = _to_bool(self.s3_use_presigned_urls, default=True)

    @classmethod
    def from_env(cls) -> "StorageConfig":
        """Build configuration from environment variables."""

        default_local_path = Path(__file__).resolve().parent.parent / "uploads"
        local_base_path = os.getenv("STORAGE_LOCAL_BASE_PATH")

        return cls(
            backend=os.getenv("STORAGE_BACKEND", "local"),
            local_base_path=Path(local_base_path) if local_base_path else default_local_path,
            local_base_url=os.getenv("STORAGE_LOCAL_BASE_URL", "/uploads"),
            s3_bucket=os.getenv("STORAGE_S3_BUCKET")
            or os.getenv("AWS_S3_BUCKET")
            or os.getenv("AWS_S3_BUCKET_NAME"),
            s3_region=os.getenv("STORAGE_S3_REGION") or os.getenv("AWS_DEFAULT_REGION"),
            s3_endpoint_url=os.getenv("STORAGE_S3_ENDPOINT_URL")
            or os.getenv("AWS_S3_ENDPOINT_URL"),
            s3_use_presigned_urls=os.getenv("STORAGE_S3_USE_PRESIGNED_URLS"),
            s3_public_base_url=os.getenv("STORAGE_S3_PUBLIC_BASE_URL"),
            s3_default_acl=os.getenv("STORAGE_S3_DEFAULT_ACL"),
            aws_access_key_id=os.getenv("STORAGE_AWS_ACCESS_KEY_ID")
            or os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("STORAGE_AWS_SECRET_ACCESS_KEY")
            or os.getenv("AWS_SECRET_ACCESS_KEY"),
            aws_session_token=os.getenv("STORAGE_AWS_SESSION_TOKEN")
            or os.getenv("AWS_SESSION_TOKEN"),
        )


class StorageService(ABC):
    """Abstract base class for storage services."""

    @abstractmethod
    def upload(
        self,
        file_stream: BinarySource,
        file_key: str,
        *,
        content_type: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Upload a file stream and return the resolved storage key."""

    @abstractmethod
    def delete(self, file_key: str) -> None:
        """Delete the object referenced by the provided key."""

    @abstractmethod
    def generate_url(self, file_key: str, *, expires_in: int = 3600) -> str:
        """Generate a URL that can be used to retrieve the object."""


class LocalStorageService(StorageService):
    """Storage service that persists files to the local filesystem."""

    def __init__(self, base_path: Union[str, Path], base_url: Optional[str] = "/uploads") -> None:
        base_path_obj = Path(base_path)
        base_path_obj.mkdir(parents=True, exist_ok=True)
        self.base_path = base_path_obj.resolve()
        self.base_url = base_url.rstrip("/") if base_url and base_url != "/" else base_url

    def upload(
        self,
        file_stream: BinarySource,
        file_key: str,
        *,
        content_type: Optional[str] = None,
        **_: Any,
    ) -> str:
        sanitized_key = _normalize_storage_key(file_key)
        target_path = self._resolve_path(sanitized_key)
        target_path.parent.mkdir(parents=True, exist_ok=True)

        stream = _coerce_binary_stream(file_stream)
        with target_path.open("wb") as destination:
            shutil.copyfileobj(stream, destination)

        return sanitized_key

    def delete(self, file_key: str) -> None:
        sanitized_key = _normalize_storage_key(file_key)
        target_path = self._resolve_path(sanitized_key)

        try:
            target_path.unlink(missing_ok=True)  # type: ignore[attr-defined]
        except TypeError:  # pragma: no cover - Python < 3.8 fallback
            if target_path.exists():
                target_path.unlink()

    def generate_url(self, file_key: str, *, expires_in: int = 3600) -> str:  # noqa: ARG002
        sanitized_key = _normalize_storage_key(file_key)
        if self.base_url:
            base = "/" if self.base_url == "/" else self.base_url
            base = base.rstrip("/") if base != "/" else base
            return f"{base}/{sanitized_key}" if base != "/" else f"/{sanitized_key}"
        return str(self._resolve_path(sanitized_key))

    def _resolve_path(self, sanitized_key: str) -> Path:
        relative_path = Path(*sanitized_key.split("/"))
        target_path = (self.base_path / relative_path).resolve()

        try:
            target_path.relative_to(self.base_path)
        except ValueError as exc:
            raise ValueError("Resolved path escapes the storage directory.") from exc

        return target_path


class S3StorageService(StorageService):
    """Storage service backed by an S3-compatible object store."""

    def __init__(
        self,
        *,
        bucket_name: str,
        region_name: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        client: Optional[Any] = None,
        use_presigned_urls: bool = True,
        public_base_url: Optional[str] = None,
        default_acl: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        aws_session_token: Optional[str] = None,
    ) -> None:
        if not bucket_name:
            raise ValueError("bucket_name is required for S3StorageService.")

        self.bucket_name = bucket_name
        self.region_name = region_name
        self.endpoint_url = endpoint_url
        self.use_presigned_urls = use_presigned_urls
        self.public_base_url = public_base_url.rstrip("/") if public_base_url else None
        self.default_acl = default_acl

        if client is not None:
            self.client = client
        else:
            if boto3 is None:  # pragma: no cover - environment dependent
                raise ImportError("boto3 is required for S3StorageService but is not installed.")

            client_kwargs: Dict[str, Any] = {}
            if region_name:
                client_kwargs["region_name"] = region_name
            if endpoint_url:
                client_kwargs["endpoint_url"] = endpoint_url
            if aws_access_key_id:
                client_kwargs["aws_access_key_id"] = aws_access_key_id
            if aws_secret_access_key:
                client_kwargs["aws_secret_access_key"] = aws_secret_access_key
            if aws_session_token:
                client_kwargs["aws_session_token"] = aws_session_token

            self.client = boto3.client("s3", **client_kwargs)

    def upload(
        self,
        file_stream: BinarySource,
        file_key: str,
        *,
        content_type: Optional[str] = None,
        acl: Optional[str] = None,
        extra_args: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> str:
        sanitized_key = _normalize_storage_key(file_key)
        stream = _coerce_binary_stream(file_stream)

        upload_args: Dict[str, Any] = {}
        if extra_args:
            upload_args.update(extra_args)
        if content_type:
            upload_args.setdefault("ContentType", content_type)
        if acl or self.default_acl:
            upload_args.setdefault("ACL", acl or self.default_acl)

        kwargs: Dict[str, Any] = {}
        if upload_args:
            kwargs["ExtraArgs"] = upload_args

        self.client.upload_fileobj(stream, self.bucket_name, sanitized_key, **kwargs)
        return sanitized_key

    def delete(self, file_key: str) -> None:
        sanitized_key = _normalize_storage_key(file_key)
        self.client.delete_object(Bucket=self.bucket_name, Key=sanitized_key)

    def generate_url(self, file_key: str, *, expires_in: int = 3600) -> str:
        sanitized_key = _normalize_storage_key(file_key)

        if not self.use_presigned_urls and self.public_base_url:
            return f"{self.public_base_url}/{sanitized_key}"

        params = {"Bucket": self.bucket_name, "Key": sanitized_key}
        return self.client.generate_presigned_url(
            "get_object", Params=params, ExpiresIn=expires_in
        )


def get_storage_service(
    config: Optional[StorageConfig] = None, **overrides: Any
) -> StorageService:
    """Factory returning the appropriate storage service for the configuration."""

    config = config or StorageConfig.from_env()
    if overrides:
        config = replace(config, **overrides)

    if config.backend == "local":
        return LocalStorageService(
            base_path=config.local_base_path,
            base_url=config.local_base_url,
        )

    if config.backend == "s3":
        if not config.s3_bucket:
            raise ValueError("S3 bucket name must be configured for S3 backend.")

        return S3StorageService(
            bucket_name=config.s3_bucket,
            region_name=config.s3_region,
            endpoint_url=config.s3_endpoint_url,
            use_presigned_urls=config.s3_use_presigned_urls,
            public_base_url=config.s3_public_base_url,
            default_acl=config.s3_default_acl,
            aws_access_key_id=config.aws_access_key_id,
            aws_secret_access_key=config.aws_secret_access_key,
            aws_session_token=config.aws_session_token,
        )

    raise ValueError(f"Unsupported storage backend '{config.backend}'.")
