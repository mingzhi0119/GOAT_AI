from __future__ import annotations

import hashlib
import io
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol

try:
    from boto3.session import Session as Boto3Session
    from botocore.client import Config as BotoCoreConfig
    from botocore.exceptions import ClientError
except ImportError:  # pragma: no cover - exercised when boto3 is unavailable
    Boto3Session = None  # type: ignore[assignment]
    BotoCoreConfig = None  # type: ignore[assignment]

    class ClientError(Exception):
        """Fallback boto3 ClientError when the dependency is unavailable."""


from goat_ai.config.settings import Settings


class ObjectStoreError(RuntimeError):
    """Raised when an object-store operation fails."""


class ObjectNotFoundError(ObjectStoreError):
    """Raised when a requested object key does not exist."""


@dataclass(frozen=True)
class StoredObjectDescriptor:
    storage_key: str
    byte_size: int = 0
    sha256: str = ""
    filesystem_path: Path | None = None


class ObjectStore(Protocol):
    backend_name: str

    def put_bytes(
        self,
        *,
        key: str | None = None,
        storage_key: str | None = None,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObjectDescriptor: ...

    def get_bytes(self, key: str) -> bytes: ...

    def read_bytes(self, key: str) -> bytes: ...

    def read_text(self, key: str, encoding: str = "utf-8") -> str: ...

    def delete(self, key: str) -> None: ...

    def exists(self, key: str) -> bool: ...

    def list_keys(self, prefix: str) -> list[str]: ...

    def get_filesystem_path(self, key: str) -> Path | None: ...


def normalize_object_key(key: str) -> str:
    raw = key.strip().replace("\\", "/")
    if not raw:
        raise ValueError("Object key must not be empty.")
    if raw.startswith("/"):
        raise ValueError("Object key must be relative.")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Object key must not escape the configured root.")
    return path.as_posix()


def normalize_object_prefix(prefix: str) -> str:
    raw = prefix.strip().replace("\\", "/").strip("/")
    if not raw:
        return ""
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("Object prefix must not escape the configured root.")
    return path.as_posix()


def build_object_store(settings: Settings) -> ObjectStore:
    if settings.object_store_backend == "local":
        return LocalObjectStore(
            root=settings.object_store_root,
            allowed_absolute_roots=(settings.object_store_root, settings.data_dir),
        )
    return S3ObjectStore(
        bucket=settings.object_store_bucket,
        prefix=settings.object_store_prefix,
        endpoint_url=settings.object_store_endpoint_url,
        region_name=settings.object_store_region,
        access_key_id=settings.object_store_access_key_id,
        secret_access_key=settings.object_store_secret_access_key,
        addressing_style=settings.object_store_s3_addressing_style,
    )


def read_text(
    store: ObjectStore,
    *,
    key: str | None = None,
    storage_key: str | None = None,
    encoding: str = "utf-8",
) -> str:
    return store.read_text(
        _resolve_requested_key(key=key, storage_key=storage_key), encoding
    )


def write_text(
    store: ObjectStore,
    *,
    key: str | None = None,
    storage_key: str | None = None,
    text: str,
    encoding: str = "utf-8",
    content_type: str | None = None,
) -> StoredObjectDescriptor:
    return store.put_bytes(
        key=key,
        storage_key=storage_key,
        content=text.encode(encoding),
        content_type=content_type,
    )


def _resolve_requested_key(*, key: str | None, storage_key: str | None) -> str:
    if key and storage_key and key != storage_key:
        raise ValueError(
            "Object key and storage_key must match when both are provided."
        )
    candidate = key or storage_key
    if candidate is None:
        raise ValueError("Object key must not be empty.")
    return candidate


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@dataclass(frozen=True)
class LocalObjectStore:
    root: Path
    allowed_absolute_roots: tuple[Path, ...] = ()
    backend_name: str = "local"

    def __post_init__(self) -> None:
        resolved_root = self.root.resolve()
        resolved_root.mkdir(parents=True, exist_ok=True)
        object.__setattr__(self, "root", resolved_root)
        resolved_allowed_roots = tuple(
            root.resolve() for root in self.allowed_absolute_roots
        ) or (resolved_root,)
        object.__setattr__(
            self,
            "allowed_absolute_roots",
            resolved_allowed_roots,
        )

    def put_bytes(
        self,
        *,
        key: str | None = None,
        storage_key: str | None = None,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObjectDescriptor:
        _ = content_type
        resolved_key = _resolve_requested_key(key=key, storage_key=storage_key)
        normalized_key = normalize_object_key(resolved_key)
        target = self._path_for_key(normalized_key)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        except OSError as exc:
            raise ObjectStoreError(
                f"Failed to write object '{normalized_key}'."
            ) from exc
        return StoredObjectDescriptor(
            storage_key=normalized_key,
            byte_size=len(content),
            sha256=_sha256(content),
            filesystem_path=target,
        )

    def get_bytes(self, key: str) -> bytes:
        target = self._path_for_read(key)
        try:
            return target.read_bytes()
        except FileNotFoundError as exc:
            raise ObjectNotFoundError(f"Object '{key}' was not found.") from exc
        except OSError as exc:
            raise ObjectStoreError(f"Failed to read object '{key}'.") from exc

    def read_bytes(self, key: str) -> bytes:
        return self.get_bytes(key)

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        return self.get_bytes(key).decode(encoding)

    def delete(self, key: str) -> None:
        target = self._path_for_read(key)
        if not target.exists():
            return
        try:
            target.unlink()
            self._prune_empty_parents(target.parent)
        except FileNotFoundError:
            return
        except OSError as exc:
            raise ObjectStoreError(f"Failed to delete object '{key}'.") from exc

    def exists(self, key: str) -> bool:
        return self._path_for_read(key).is_file()

    def list_keys(self, prefix: str) -> list[str]:
        normalized_prefix = normalize_object_prefix(prefix)
        base = (
            self.root
            if not normalized_prefix
            else self._path_for_key(normalized_prefix)
        )
        if not base.exists():
            return []
        if base.is_file():
            return [base.relative_to(self.root).as_posix()]
        return sorted(
            path.relative_to(self.root).as_posix()
            for path in base.rglob("*")
            if path.is_file()
        )

    def get_filesystem_path(self, key: str) -> Path | None:
        return self._path_for_read(key)

    def _path_for_key(self, key: str) -> Path:
        normalized_key = normalize_object_key(key)
        return self.root.joinpath(*PurePosixPath(normalized_key).parts)

    def _path_for_read(self, key: str) -> Path:
        absolute = self._resolve_allowed_absolute_path(key)
        if absolute is not None:
            return absolute
        return self._path_for_key(key)

    def _resolve_allowed_absolute_path(self, key: str) -> Path | None:
        candidate = Path(key)
        if not candidate.is_absolute():
            return None
        resolved = candidate.resolve()
        if not any(
            _is_within_root(resolved, root) for root in self.allowed_absolute_roots
        ):
            raise ObjectStoreError(
                f"Absolute object path '{resolved}' falls outside the allowed roots."
            )
        return resolved

    def _prune_empty_parents(self, path: Path) -> None:
        current = path
        while _is_within_root(current, self.root) and current != self.root:
            try:
                current.rmdir()
            except OSError:
                return
            current = current.parent


@dataclass(frozen=True)
class S3ObjectStore:
    bucket: str
    prefix: str = ""
    endpoint_url: str = ""
    region_name: str = ""
    access_key_id: str = ""
    secret_access_key: str = ""
    addressing_style: str = "auto"
    client: Any | None = None
    backend_name: str = "s3"

    def __post_init__(self) -> None:
        object.__setattr__(self, "prefix", normalize_object_prefix(self.prefix))
        if self.client is not None:
            return
        if Boto3Session is None or BotoCoreConfig is None:
            raise ObjectStoreError(
                "boto3 is required for GOAT_OBJECT_STORE_BACKEND=s3."
            )
        session = Boto3Session(
            aws_access_key_id=self.access_key_id or None,
            aws_secret_access_key=self.secret_access_key or None,
            region_name=self.region_name or None,
        )
        client = session.client(
            "s3",
            endpoint_url=self.endpoint_url or None,
            config=BotoCoreConfig(s3={"addressing_style": self.addressing_style}),
        )
        object.__setattr__(self, "client", client)

    def put_bytes(
        self,
        *,
        key: str | None = None,
        storage_key: str | None = None,
        content: bytes,
        content_type: str | None = None,
    ) -> StoredObjectDescriptor:
        normalized_key = normalize_object_key(
            _resolve_requested_key(key=key, storage_key=storage_key)
        )
        try:
            params: dict[str, object] = {
                "Bucket": self.bucket,
                "Key": self._full_key(normalized_key),
                "Body": content,
            }
            if content_type:
                params["ContentType"] = content_type
            self._client().put_object(**params)
        except Exception as exc:
            raise ObjectStoreError(
                f"Failed to write object '{normalized_key}' to S3."
            ) from exc
        return StoredObjectDescriptor(
            storage_key=normalized_key,
            byte_size=len(content),
            sha256=_sha256(content),
        )

    def get_bytes(self, key: str) -> bytes:
        normalized_key = normalize_object_key(key)
        try:
            response = self._client().get_object(
                Bucket=self.bucket,
                Key=self._full_key(normalized_key),
            )
            body = response["Body"]
            if hasattr(body, "read"):
                return bytes(body.read())
            if isinstance(body, (bytes, bytearray)):
                return bytes(body)
            if isinstance(body, io.BytesIO):
                return body.getvalue()
            raise ObjectStoreError(
                f"Unexpected body type for object '{normalized_key}'."
            )
        except ClientError as exc:
            if _looks_like_s3_not_found(exc):
                raise ObjectNotFoundError(
                    f"Object '{normalized_key}' was not found."
                ) from exc
            raise ObjectStoreError(
                f"Failed to read object '{normalized_key}' from S3."
            ) from exc
        except ObjectStoreError:
            raise
        except Exception as exc:
            raise ObjectStoreError(
                f"Failed to read object '{normalized_key}' from S3."
            ) from exc

    def read_bytes(self, key: str) -> bytes:
        return self.get_bytes(key)

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        return self.get_bytes(key).decode(encoding)

    def delete(self, key: str) -> None:
        normalized_key = normalize_object_key(key)
        try:
            self._client().delete_object(
                Bucket=self.bucket,
                Key=self._full_key(normalized_key),
            )
        except Exception as exc:
            raise ObjectStoreError(
                f"Failed to delete object '{normalized_key}' from S3."
            ) from exc

    def exists(self, key: str) -> bool:
        normalized_key = normalize_object_key(key)
        try:
            self._client().head_object(
                Bucket=self.bucket,
                Key=self._full_key(normalized_key),
            )
            return True
        except ClientError as exc:
            if _looks_like_s3_not_found(exc):
                return False
            raise ObjectStoreError(
                f"Failed to inspect object '{normalized_key}' in S3."
            ) from exc
        except Exception as exc:
            raise ObjectStoreError(
                f"Failed to inspect object '{normalized_key}' in S3."
            ) from exc

    def list_keys(self, prefix: str) -> list[str]:
        normalized_prefix = normalize_object_prefix(prefix)
        full_prefix = (
            self._full_key(normalized_prefix)
            if normalized_prefix
            else self._prefix_with_trailing_slash()
        )
        out: list[str] = []
        continuation_token: str | None = None
        while True:
            params: dict[str, object] = {
                "Bucket": self.bucket,
                "Prefix": full_prefix,
            }
            if continuation_token:
                params["ContinuationToken"] = continuation_token
            try:
                response = self._client().list_objects_v2(**params)
            except Exception as exc:
                raise ObjectStoreError(
                    f"Failed to list objects under prefix '{normalized_prefix}'."
                ) from exc
            for item in response.get("Contents", []):
                raw_key = str(item.get("Key", ""))
                if not raw_key:
                    continue
                stripped = self._strip_configured_prefix(raw_key)
                if stripped:
                    out.append(stripped)
            if not response.get("IsTruncated"):
                break
            continuation_token = str(response.get("NextContinuationToken", ""))
            if not continuation_token:
                break
        return sorted(out)

    def get_filesystem_path(self, key: str) -> Path | None:
        _ = key
        return None

    def _client(self) -> Any:
        assert self.client is not None
        return self.client

    def _full_key(self, key: str) -> str:
        return self._full_prefix(normalize_object_key(key))

    def _full_prefix(self, prefix: str) -> str:
        if not self.prefix:
            return prefix
        if not prefix:
            return self.prefix
        return f"{self.prefix}/{prefix}"

    def _prefix_with_trailing_slash(self) -> str:
        if not self.prefix:
            return ""
        return f"{self.prefix}/"

    def _strip_configured_prefix(self, key: str) -> str:
        if not self.prefix:
            return key
        if key == self.prefix:
            return ""
        return key.removeprefix(f"{self.prefix}/")


def _is_within_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _looks_like_s3_not_found(exc: ClientError) -> bool:
    code = str(exc.response.get("Error", {}).get("Code", "")).strip()
    return code in {"404", "NoSuchKey", "NotFound"}
