"""Memes feed API endpoints.

This module exposes the public memes feed routes backed by a configurable
repository abstraction. The default implementation ships with an in-memory
repository so the blueprint can be exercised without a database, while the
interfaces make it straightforward to plug in a database-backed repository.
"""

from __future__ import annotations

import math
import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Mapping, MutableMapping, Optional, Protocol, Sequence, Tuple, Type

from flask import Blueprint, abort, jsonify, request

DEFAULT_PAGE: int = 1
DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 100
DEFAULT_RANDOM_CACHE_TTL: float = 30.0


@dataclass(frozen=True)
class MemeCreator:
    """Public-facing creator information for a meme."""

    id: Any
    username: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None

    def to_dict(self) -> MutableMapping[str, Any]:
        return {
            "id": str(self.id) if self.id is not None else None,
            "username": self.username,
            "displayName": self.display_name,
            "avatarUrl": self.avatar_url,
        }


@dataclass(frozen=True)
class MemeRecord:
    """Normalised representation of a meme with aggregated vote counts."""

    id: Any
    slug: Optional[str] = None
    title: Optional[str] = None
    caption: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    status: str = "pending"
    upvotes: int = 0
    downvotes: int = 0
    tags: Tuple[str, ...] = ()
    categories: Tuple[str, ...] = ()
    creator: Optional[MemeCreator] = None
    extra: Mapping[str, Any] = field(default_factory=dict)

    @property
    def score(self) -> int:
        try:
            up = int(self.upvotes)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            up = 0
        try:
            down = int(self.downvotes)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            down = 0
        return max(0, up) - max(0, down)


@dataclass(frozen=True)
class MemesFilter:
    """Filtering options supported by the repository."""

    statuses: Tuple[str, ...] = ("approved",)
    creator_ids: Tuple[str, ...] = ()
    tags: Tuple[str, ...] = ()
    search: Optional[str] = None

    def normalised_statuses(self) -> Tuple[str, ...]:
        return tuple({status.lower() for status in self.statuses if status})

    def normalised_creator_ids(self) -> Tuple[str, ...]:
        return tuple({str(identifier) for identifier in self.creator_ids if identifier != ""})

    def normalised_tags(self) -> Tuple[str, ...]:
        return tuple({tag.lower() for tag in self.tags if tag})


class QueryParameterError(ValueError):
    """Raised when the client submits invalid pagination or filter parameters."""


@dataclass(frozen=True)
class MemesQueryParams:
    """Validated query parameters for the memes feed."""

    page: int = DEFAULT_PAGE
    page_size: int = DEFAULT_PAGE_SIZE
    sort: str = "new"
    filters: MemesFilter = field(default_factory=MemesFilter)

    @classmethod
    def from_mapping(
        cls,
        args: Mapping[str, Any],
        *,
        default_page_size: int = DEFAULT_PAGE_SIZE,
        max_page_size: int = MAX_PAGE_SIZE,
    ) -> "MemesQueryParams":
        page = _parse_positive_int(
            _first_value(args, ("page", "pageNumber", "page_number", "p")),
            default=DEFAULT_PAGE,
            name="page",
        )
        page_size = _parse_positive_int(
            _first_value(args, ("pageSize", "page_size", "limit", "perPage", "per_page")),
            default=default_page_size,
            name="pageSize",
            maximum=max_page_size,
        )
        sort = _normalise_sort(_first_value(args, ("sort", "order", "ordering")))

        statuses = _collect_values(args, ("status", "statuses", "state"))
        if statuses:
            statuses = [status.lower() for status in statuses if status]
        else:
            statuses = ["approved"]

        creator_ids = _collect_values(args, ("creatorId", "creator", "authorId", "author"))
        tags = _collect_values(args, ("tag", "tags", "category", "categories"))
        search_raw = _first_value(args, ("search", "q", "query"))
        search = search_raw.strip() if isinstance(search_raw, str) and search_raw.strip() else None

        filters = MemesFilter(
            statuses=tuple(dict.fromkeys(statuses)),
            creator_ids=tuple(dict.fromkeys(creator_ids)),
            tags=tuple(dict.fromkeys(tag.lower() for tag in tags if tag)),
            search=search,
        )

        return cls(page=page, page_size=page_size, sort=sort, filters=filters)


class MemesRepository(Protocol):
    """Repository interface required by the memes service."""

    def fetch_memes(
        self,
        *,
        offset: int,
        limit: int,
        sort: str,
        filters: MemesFilter,
    ) -> Tuple[Sequence[MemeRecord], int]:
        ...

    def get_random_meme(self, *, filters: MemesFilter) -> Optional[MemeRecord]:
        ...


class InMemoryMemesRepository:
    """Thread-safe repository backed by an in-memory list of memes."""

    def __init__(self, memes: Optional[Iterable[MemeRecord]] = None) -> None:
        self._lock = threading.Lock()
        self._memes = tuple(memes or ())

    def fetch_memes(
        self,
        *,
        offset: int,
        limit: int,
        sort: str,
        filters: MemesFilter,
    ) -> Tuple[Sequence[MemeRecord], int]:
        with self._lock:
            filtered = tuple(meme for meme in self._memes if _meme_matches(meme, filters))

        ordered = _order_memes(filtered, sort)
        total = len(ordered)
        if offset < 0:
            offset = 0
        end = None if limit <= 0 else offset + limit
        page_items = ordered[offset:end]
        return page_items, total

    def get_random_meme(self, *, filters: MemesFilter) -> Optional[MemeRecord]:
        with self._lock:
            candidates = [meme for meme in self._memes if _meme_matches(meme, filters)]
        if not candidates:
            return None
        return random.choice(candidates)


class SQLAlchemyMemesRepository(MemesRepository):
    """Repository backed by SQLAlchemy sessions and models.

    The repository is intentionally adaptable so that existing declarative
    models can be reused without modification by supplying light-weight
    adapters for creators, tags, or vote aggregation.
    """

    def __init__(
        self,
        session_factory: Callable[[], Any],
        meme_model: Type[Any],
        *,
        field_mapping: Optional[Mapping[str, str]] = None,
        creator_adapter: Optional[Callable[[Any], Optional[MemeCreator]]] = None,
        vote_counters: Optional[
            Callable[[Any, Sequence[Any]], Mapping[Any, Tuple[int, int]]]
        ] = None,
        tag_loader: Optional[Callable[[Any], Sequence[str]]] = None,
    ) -> None:
        try:
            from sqlalchemy import func, or_, select  # type: ignore[import-not-found]
        except ImportError as exc:  # pragma: no cover - defensive
            raise RuntimeError(
                "SQLAlchemyMemesRepository requires SQLAlchemy to be installed."
            ) from exc

        if not callable(session_factory):  # pragma: no cover - defensive
            raise TypeError("session_factory must be callable")

        self._func = func
        self._or = or_
        self._select = select
        self._session_factory = session_factory
        self._meme_model = meme_model
        self._field_mapping = dict(field_mapping or {})
        self._creator_adapter = creator_adapter or self._default_creator_adapter
        self._vote_counters = vote_counters
        self._tag_loader = tag_loader

    def fetch_memes(
        self,
        *,
        offset: int,
        limit: int,
        sort: str,
        filters: MemesFilter,
    ) -> Tuple[Sequence[MemeRecord], int]:
        session = self._session_factory()
        close = getattr(session, "close", None)
        try:
            query = self._apply_basic_filters(self._select(self._meme_model), filters)
            if hasattr(session, "scalars"):
                memes = list(session.scalars(query).all())
            else:  # pragma: no cover - legacy SQLAlchemy support
                memes = [row[0] for row in session.execute(query)]
            vote_counts = self._compute_vote_counts(session, memes)
        finally:
            if callable(close):
                close()
        records = [self._build_record(meme, vote_counts) for meme in memes]
        filtered = tuple(record for record in records if _meme_matches(record, filters))
        ordered = _order_memes(filtered, sort)
        total = len(ordered)
        if offset < 0:
            offset = 0
        end = None if limit <= 0 else offset + limit
        return ordered[offset:end], total

    def get_random_meme(self, *, filters: MemesFilter) -> Optional[MemeRecord]:
        session = self._session_factory()
        close = getattr(session, "close", None)
        vote_counts: Dict[Any, Tuple[int, int]] = {}
        try:
            query = self._apply_basic_filters(self._select(self._meme_model), filters)
            meme = None
            try:
                meme = session.scalars(query.order_by(self._func.random()).limit(1)).first()
            except Exception:  # pragma: no cover - driver fallback
                meme = None
            if meme is None:
                if hasattr(session, "scalars"):
                    candidates = list(session.scalars(query).all())
                else:  # pragma: no cover - legacy SQLAlchemy support
                    candidates = [row[0] for row in session.execute(query)]
                if not candidates:
                    return None
                meme = random.choice(candidates)
            vote_counts = self._compute_vote_counts(session, [meme])
        finally:
            if callable(close):
                close()
        record = self._build_record(meme, vote_counts)
        if not _meme_matches(record, filters):
            return None
        return record

    def _apply_basic_filters(self, query: Any, filters: MemesFilter) -> Any:
        statuses = filters.normalised_statuses()
        status_column = self._get_column("status", "status")
        if status_column is not None and statuses:
            query = query.where(status_column.in_(statuses))

        creator_ids = filters.normalised_creator_ids()
        if creator_ids:
            for candidate in ("creator_id", "author_id", "user_id", "owner_id"):
                column = self._get_column(candidate, candidate)
                if column is not None:
                    query = query.where(column.in_(self._coerce_ids(creator_ids, column)))
                    break

        if filters.search:
            pattern = f"%{filters.search.lower()}%"
            clauses = []
            for key in ("title", "caption", "description", "summary", "text"):
                column = self._get_column(key, key)
                if column is None:
                    continue
                try:
                    clauses.append(column.ilike(pattern))  # type: ignore[attr-defined]
                except AttributeError:
                    clauses.append(self._func.lower(column).like(pattern))
            if clauses:
                query = query.where(self._or(*clauses))
        return query

    def _build_record(
        self,
        meme: Any,
        vote_counts: Mapping[Any, Tuple[int, int]],
    ) -> MemeRecord:
        meme_id = self._get_attr_value(meme, "id", "id")
        votes = vote_counts.get(meme_id)
        upvotes, downvotes = self._resolve_votes(meme, votes)
        extra: Dict[str, Any] = {}
        preview_url = self._get_attr_value(meme, "preview_url", "preview_url")
        if preview_url:
            extra["previewUrl"] = preview_url
        permalink = self._get_attr_value(meme, "permalink", "permalink")
        if permalink:
            extra["permalink"] = permalink
        return MemeRecord(
            id=meme_id,
            slug=self._get_attr_value(meme, "slug", "slug"),
            title=self._get_attr_value(meme, "title", "title"),
            caption=self._get_attr_value(meme, "caption", "caption"),
            description=self._get_attr_value(meme, "description", "description"),
            image_url=self._get_attr_value(meme, "image_url", "image_url"),
            thumbnail_url=self._get_attr_value(meme, "thumbnail_url", "thumbnail_url"),
            created_at=self._get_attr_value(meme, "created_at", "created_at"),
            updated_at=self._get_attr_value(meme, "updated_at", "updated_at"),
            status=self._get_attr_value(meme, "status", "status") or "",
            upvotes=upvotes,
            downvotes=downvotes,
            tags=tuple(self._resolve_tags(meme)),
            categories=self._resolve_categories(meme),
            creator=self._extract_creator(meme),
            extra=extra,
        )

    def _extract_creator(self, meme: Any) -> Optional[MemeCreator]:
        candidate_names: Tuple[Optional[str], ...] = (
            self._field_mapping.get("creator"),
            "creator",
            "author",
            "user",
            "owner",
        )
        for name in candidate_names:
            if not name:
                continue
            if hasattr(meme, name):
                return self._creator_adapter(getattr(meme, name))
        return None

    def _resolve_tags(self, meme: Any) -> Sequence[str]:
        if self._tag_loader is not None:
            tags = self._tag_loader(meme)
            return tuple(str(tag) for tag in tags) if tags else ()
        for key in (
            self._field_mapping.get("tags"),
            "tags",
            "tag_list",
            "labels",
            "keywords",
        ):
            if not key:
                continue
            value = getattr(meme, key, None)
            if value is None:
                continue
            return self._coerce_iterable(value)
        return ()

    def _resolve_categories(self, meme: Any) -> Tuple[str, ...]:
        value = self._get_attr_value(meme, "categories", "categories")
        if value is None:
            value = self._get_attr_value(meme, "category", "category")
        return self._coerce_iterable(value)

    def _get_column(self, key: str, default: str) -> Any:
        name = self._field_mapping.get(key, default)
        if name is None:
            return None
        return getattr(self._meme_model, name, None)

    def _get_attr_value(self, meme: Any, key: str, default: str) -> Any:
        name = self._field_mapping.get(key, default)
        if name is None:
            return None
        return getattr(meme, name, None)

    def _compute_vote_counts(
        self,
        session: Any,
        memes: Sequence[Any],
    ) -> Dict[Any, Tuple[int, int]]:
        if self._vote_counters is None or not memes:
            return {}
        raw_mapping = self._vote_counters(session, memes) or {}
        if isinstance(raw_mapping, Mapping):
            items = raw_mapping.items()
        else:  # pragma: no cover - defensive
            items = list(raw_mapping)
        resolved: Dict[Any, Tuple[int, int]] = {}
        for entry in items:
            try:
                key, value = entry
            except (TypeError, ValueError):
                continue
            meme_id = self._resolve_key_identifier(key)
            if meme_id is None:
                continue
            up, down = self._normalise_vote_pair(value)
            resolved[meme_id] = (max(0, up), max(0, down))
        return resolved

    def _resolve_votes(
        self,
        meme: Any,
        aggregated: Optional[Tuple[int, int]],
    ) -> Tuple[int, int]:
        if aggregated is not None:
            up, down = aggregated
            return max(0, up), max(0, down)

        up = self._first_int_attr(
            meme, ("upvotes", "upvote_count", "upvote_total", "likes", "like_count")
        )
        down = self._first_int_attr(
            meme,
            ("downvotes", "downvote_count", "downvote_total", "dislikes", "dislike_count"),
        )

        if down is None:
            score_attr = getattr(meme, "score", None)
            try:
                score = int(score_attr)
            except (TypeError, ValueError):
                score = None
            if score is not None:
                if up is not None:
                    down = max(0, up - score)
                else:
                    if score >= 0:
                        up = score
                        down = 0
                    else:
                        up = 0
                        down = abs(score)

        return max(0, up or 0), max(0, down or 0)

    def _resolve_key_identifier(self, key: Any) -> Any:
        if isinstance(key, self._meme_model):
            return self._get_attr_value(key, "id", "id")
        return key

    @staticmethod
    def _normalise_vote_pair(value: Any) -> Tuple[int, int]:
        if isinstance(value, (tuple, list)) and len(value) >= 2:
            up, down = value[0], value[1]
        elif isinstance(value, Mapping):
            up = value.get("up") or value.get("upvotes") or value.get("positive") or 0
            down = value.get("down") or value.get("downvotes") or value.get("negative") or 0
        else:
            up, down = value, 0
        try:
            up_int = int(up)
        except (TypeError, ValueError):
            up_int = 0
        try:
            down_int = int(down)
        except (TypeError, ValueError):
            down_int = 0
        return up_int, down_int

    @staticmethod
    def _first_int_attr(obj: Any, names: Sequence[str]) -> Optional[int]:
        for name in names:
            if not name or not hasattr(obj, name):
                continue
            value = getattr(obj, name)
            try:
                return int(value)
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _coerce_iterable(value: Any) -> Tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            return tuple(part.strip() for part in value.split(",") if part.strip())
        if isinstance(value, (list, tuple, set)):
            return tuple(str(part).strip() for part in value if str(part).strip())
        return ()

    @staticmethod
    def _coerce_ids(ids: Sequence[str], column: Any) -> Sequence[Any]:
        coerced: List[Any] = []
        python_type = None
        try:
            python_type = column.type.python_type  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - defensive
            python_type = None
        for identifier in ids:
            if python_type is int:
                try:
                    coerced.append(int(identifier))
                    continue
                except ValueError:
                    pass
            coerced.append(identifier)
        return coerced

    @staticmethod
    def _default_creator_adapter(value: Any) -> Optional[MemeCreator]:
        if value is None:
            return None
        identifier = getattr(value, "id", None) or getattr(value, "uuid", None)
        username = getattr(value, "username", None) or getattr(value, "handle", None)
        display_name = (
            getattr(value, "display_name", None)
            or getattr(value, "full_name", None)
            or getattr(value, "name", None)
        )
        avatar = (
            getattr(value, "avatar_url", None)
            or getattr(value, "avatar", None)
            or getattr(value, "image_url", None)
        )
        if username is None and identifier is not None:
            username = str(identifier)
        if identifier is None and username is None:
            return None
        return MemeCreator(
            id=identifier if identifier is not None else username,
            username=username or "",
            display_name=display_name,
            avatar_url=avatar,
        )


@dataclass(frozen=True)
class Pagination:
    """Pagination metadata for a result set."""

    page: int
    page_size: int
    total: int

    @property
    def pages(self) -> int:
        if self.page_size <= 0:
            return 1 if self.total else 0
        if self.total == 0:
            return 0
        return math.ceil(self.total / self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.pages if self.pages else False

    @property
    def has_previous(self) -> bool:
        return self.page > 1 and self.pages > 0

    def to_dict(self) -> MutableMapping[str, Any]:
        return {
            "page": self.page,
            "pageSize": self.page_size,
            "total": self.total,
            "pages": self.pages,
            "hasNext": self.has_next,
            "hasPrevious": self.has_previous,
        }


@dataclass(frozen=True)
class PaginatedMemes:
    """Container object encapsulating paginated meme results."""

    items: Sequence[MemeRecord]
    pagination: Pagination

    def to_dict(self) -> MutableMapping[str, Any]:
        return {
            "items": [_serialise_meme(item) for item in self.items],
            "pagination": self.pagination.to_dict(),
            "count": len(self.items),
            "total": self.pagination.total,
        }


class MemesService:
    """Application service orchestrating meme queries and formatting."""

    def __init__(self, repository: MemesRepository) -> None:
        self._repository = repository

    def list_memes(self, params: MemesQueryParams) -> PaginatedMemes:
        filters = params.filters
        offset = (params.page - 1) * params.page_size if params.page_size > 0 else 0
        items, total = self._repository.fetch_memes(
            offset=offset,
            limit=params.page_size,
            sort=params.sort,
            filters=filters,
        )
        pagination = Pagination(page=params.page, page_size=params.page_size, total=total)
        return PaginatedMemes(items=items, pagination=pagination)

    def get_random_meme(self, filters: Optional[MemesFilter] = None) -> Optional[MemeRecord]:
        filters = filters or MemesFilter()
        return self._repository.get_random_meme(filters=filters)


class RandomMemeCache:
    """TTL cache for the random meme endpoint to avoid repeated queries."""

    def __init__(self, ttl_seconds: float = DEFAULT_RANDOM_CACHE_TTL) -> None:
        self._ttl = max(0.0, float(ttl_seconds))
        self._lock = threading.Lock()
        self._value: Optional[MemeRecord] = None
        self._expires_at: float = 0.0

    def get(self) -> Optional[MemeRecord]:
        if self._ttl == 0:
            return None
        now = time.monotonic()
        with self._lock:
            if self._value is not None and now < self._expires_at:
                return self._value
        return None

    def set(self, value: MemeRecord) -> None:
        if self._ttl == 0:
            return
        with self._lock:
            self._value = value
            self._expires_at = time.monotonic() + self._ttl

    def invalidate(self) -> None:
        with self._lock:
            self._value = None
            self._expires_at = 0.0


def get_memes_service(repository: Optional[MemesRepository] = None) -> MemesService:
    """Factory returning a :class:`MemesService` with the provided repository."""

    repository = repository or InMemoryMemesRepository()
    return MemesService(repository)


def create_memes_app(
    service: Optional[MemesService] = None,
    *,
    repository: Optional[MemesRepository] = None,
    random_cache: Optional[RandomMemeCache] = None,
    cache_ttl_seconds: float = DEFAULT_RANDOM_CACHE_TTL,
) -> Blueprint:
    """Create the Flask blueprint exposing the memes feed API."""

    if service is None:
        service = get_memes_service(repository)
    cache = random_cache or RandomMemeCache(cache_ttl_seconds)

    blueprint = Blueprint("memes_api", __name__)

    @blueprint.route("/api/memes", methods=["GET"])
    def list_memes_route() -> Any:
        try:
            params = MemesQueryParams.from_mapping(request.args)
        except QueryParameterError as exc:  # pragma: no cover - validated in tests
            abort(400, description=str(exc))

        result = service.list_memes(params)
        return jsonify(result.to_dict())

    @blueprint.route("/api/memes/random", methods=["GET"])
    def random_meme_route() -> Any:
        if request.args.get("refresh", "").lower() in {"1", "true", "yes", "y"}:
            cache.invalidate()

        cached = cache.get()
        if cached is not None:
            return jsonify({"meme": _serialise_meme(cached), "cached": True})

        meme = service.get_random_meme(MemesFilter(statuses=("approved",)))
        if meme is None:
            abort(404, description="No approved memes available.")

        cache.set(meme)
        return jsonify({"meme": _serialise_meme(meme), "cached": False})

    return blueprint


def _meme_matches(meme: MemeRecord, filters: MemesFilter) -> bool:
    statuses = filters.normalised_statuses()
    if statuses:
        status = (meme.status or "").lower()
        if status not in statuses:
            return False

    creator_ids = filters.normalised_creator_ids()
    if creator_ids:
        meme_creator_id = None
        if meme.creator is not None:
            meme_creator_id = str(meme.creator.id)
        elif meme.extra and "creator_id" in meme.extra:
            meme_creator_id = str(meme.extra["creator_id"])
        if meme_creator_id is None or meme_creator_id not in creator_ids:
            return False

    tags = filters.normalised_tags()
    if tags:
        meme_tags = {tag.lower() for tag in (meme.tags or ())}
        if not meme_tags or not set(tags).issubset(meme_tags):
            return False

    if filters.search:
        needle = filters.search.lower()
        haystack_parts = [
            meme.title or "",
            meme.caption or "",
            meme.description or "",
        ]
        if not any(needle in part.lower() for part in haystack_parts if part):
            return False

    return True


def _order_memes(memes: Sequence[MemeRecord], sort: str) -> Tuple[MemeRecord, ...]:
    if sort == "top":
        return tuple(sorted(memes, key=lambda meme: (meme.score, _timestamp_key(meme.created_at)), reverse=True))
    if sort == "oldest":
        return tuple(sorted(memes, key=lambda meme: _timestamp_key(meme.created_at)))
    return tuple(sorted(memes, key=lambda meme: _timestamp_key(meme.created_at), reverse=True))


def _timestamp_key(value: Optional[datetime]) -> float:
    if value is None:
        return float("-inf")
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _serialise_meme(meme: MemeRecord) -> MutableMapping[str, Any]:
    payload: MutableMapping[str, Any] = {
        "id": meme.id,
        "slug": meme.slug,
        "title": meme.title,
        "caption": meme.caption or meme.description,
        "description": meme.description,
        "imageUrl": meme.image_url,
        "thumbnailUrl": meme.thumbnail_url,
        "status": meme.status,
        "createdAt": _serialise_datetime(meme.created_at),
        "updatedAt": _serialise_datetime(meme.updated_at),
        "tags": list(meme.tags or ()),
        "categories": list(meme.categories or ()),
        "votes": {
            "up": int(meme.upvotes or 0),
            "down": int(meme.downvotes or 0),
            "score": int(meme.score),
        },
        "creator": meme.creator.to_dict() if meme.creator else None,
    }
    if meme.extra:
        payload["meta"] = dict(meme.extra)
    return payload


def _serialise_datetime(value: Optional[datetime]) -> Optional[str]:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _first_value(args: Mapping[str, Any], keys: Sequence[str]) -> Optional[str]:
    for key in keys:
        if hasattr(args, "get"):
            value = args.get(key)
        else:
            value = args[key] if key in args else None
        if value is not None and value != "":
            if isinstance(value, (list, tuple)):
                return next((str(item) for item in value if item not in (None, "")), None)
            return str(value)
    return None


def _collect_values(args: Mapping[str, Any], keys: Sequence[str]) -> list[str]:
    values: list[str] = []
    for key in keys:
        if hasattr(args, "getlist"):
            values.extend(args.getlist(key))  # type: ignore[attr-defined]
        if hasattr(args, "get"):
            value = args.get(key)
        else:
            value = args[key] if key in args else None
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            values.extend(value)
        else:
            values.append(value)
    normalised: list[str] = []
    for item in values:
        if item in (None, ""):
            continue
        text = str(item)
        for chunk in text.split(","):
            cleaned = chunk.strip()
            if cleaned:
                normalised.append(cleaned)
    return normalised


def _parse_positive_int(
    value: Optional[str],
    *,
    default: int,
    name: str,
    maximum: Optional[int] = None,
) -> int:
    if value is None or value == "":
        integer = default
    else:
        try:
            integer = int(value)
        except (TypeError, ValueError) as exc:
            raise QueryParameterError(f"'{name}' must be a positive integer.") from exc
        if integer <= 0:
            raise QueryParameterError(f"'{name}' must be greater than zero.")
    if maximum is not None and integer > maximum:
        integer = maximum
    return integer


def _normalise_sort(value: Optional[str]) -> str:
    if not value:
        return "new"
    lowered = value.strip().lower()
    if lowered in {
        "new",
        "latest",
        "recent",
        "desc",
        "descending",
        "-created_at",
        "-createdat",
        "-created",
    }:
        return "new"
    if lowered in {"old", "oldest", "created_at", "createdat", "asc", "ascending"}:
        return "oldest"
    if lowered in {"top", "popular", "score", "-score", "votes", "trending"}:
        return "top"
    return "new"


__all__ = [
    "MemeCreator",
    "MemeRecord",
    "MemesFilter",
    "MemesQueryParams",
    "MemesRepository",
    "InMemoryMemesRepository",
    "SQLAlchemyMemesRepository",
    "Pagination",
    "PaginatedMemes",
    "MemesService",
    "RandomMemeCache",
    "QueryParameterError",
    "create_memes_app",
    "get_memes_service",
]
