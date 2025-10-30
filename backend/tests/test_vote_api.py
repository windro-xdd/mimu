import unittest
from typing import Dict
from unittest import mock

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend import (
    Base,
    Content,
    ContentStatus,
    ContentType,
    GamificationEventResult,
    User,
    UserRole,
    Vote,
    create_app,
)


class VoteEndpointTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine("sqlite:///:memory:")
        self.SessionLocal = sessionmaker(bind=self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

        self.gamification = mock.Mock()
        self.gamification.record_vote.return_value = GamificationEventResult(score=0.0)
        self.app = create_app(
            session_factory=self.SessionLocal,
            gamification_service=self.gamification,
        )
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()

        session = self.SessionLocal()
        self.creator = User(
            username="creator",
            email="creator@example.com",
            hashed_password="secret",
            role=UserRole.CREATOR,
            total_score=0,
        )
        session.add(self.creator)
        self.voter = User(
            username="voter",
            email="voter@example.com",
            hashed_password="secret",
            role=UserRole.VIEWER,
            total_score=0,
        )
        session.add(self.voter)
        session.flush()

        self.content = Content(
            author_id=self.creator.id,
            title="Example Content",
            body="Test body",
            status=ContentStatus.PUBLISHED,
            content_type=ContentType.ARTICLE,
            score=0,
            upvotes=0,
            downvotes=0,
        )
        session.add(self.content)
        session.commit()
        session.close()

    def tearDown(self) -> None:
        self.app_context.pop()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _vote(self, value: str, *, user_id: int | None = None, content_id: int | None = None):
        headers: Dict[str, str] = {"X-User-Id": str(user_id or self.voter.id)}
        return self.client.post(
            f"/api/content/{content_id or self.content.id}/vote",
            json={"vote": value},
            headers=headers,
        )

    def test_upvote_creates_record_and_updates_scores(self) -> None:
        response = self._vote("up")

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["score"]["total"], 1)
        self.assertEqual(data["score"]["upvotes"], 1)
        self.assertEqual(data["score"]["downvotes"], 0)
        self.assertEqual(data["user_vote"], "up")
        self.assertEqual(data["creator"]["total_score"], 1)

        self.gamification.record_vote.assert_called_once()
        _, kwargs = self.gamification.record_vote.call_args
        self.assertEqual(kwargs["delta"], 1)
        self.assertEqual(kwargs["content_id"], self.content.id)
        self.assertEqual(kwargs["voter_id"], str(self.voter.id))
        self.assertEqual(kwargs["previous_vote"], 0)
        self.assertEqual(kwargs["new_vote"], 1)

        session = self.SessionLocal()
        vote = session.get(Vote, (self.voter.id, self.content.id))
        self.assertIsNotNone(vote)
        self.assertEqual(vote.value, 1)
        content = session.get(Content, self.content.id)
        self.assertEqual(content.score, 1)
        session.close()

    def test_switching_vote_updates_totals(self) -> None:
        self._vote("up")
        self.gamification.reset_mock()

        response = self._vote("down")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["score"]["total"], -1)
        self.assertEqual(data["score"]["upvotes"], 0)
        self.assertEqual(data["score"]["downvotes"], 1)
        self.assertEqual(data["user_vote"], "down")
        self.assertEqual(data["creator"]["total_score"], -1)

        _, kwargs = self.gamification.record_vote.call_args
        self.assertEqual(kwargs["delta"], -2)

        session = self.SessionLocal()
        vote = session.get(Vote, (self.voter.id, self.content.id))
        self.assertEqual(vote.value, -1)
        content = session.get(Content, self.content.id)
        self.assertEqual(content.score, -1)
        session.close()

    def test_neutral_vote_removes_existing_vote(self) -> None:
        self._vote("down")
        self.gamification.reset_mock()

        response = self._vote("neutral")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["score"]["total"], 0)
        self.assertEqual(data["score"]["upvotes"], 0)
        self.assertEqual(data["score"]["downvotes"], 0)
        self.assertEqual(data["user_vote"], "neutral")
        self.assertEqual(data["creator"]["total_score"], 0)

        _, kwargs = self.gamification.record_vote.call_args
        self.assertEqual(kwargs["delta"], 1)

        session = self.SessionLocal()
        vote = session.get(Vote, (self.voter.id, self.content.id))
        self.assertIsNone(vote)
        session.close()

    def test_idempotent_when_repeating_same_vote(self) -> None:
        self._vote("up")
        self.gamification.reset_mock()

        response = self._vote("up")
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data["score"]["total"], 1)
        self.assertEqual(data["user_vote"], "up")
        self.gamification.record_vote.assert_not_called()

    def test_invalid_vote_payload_returns_400(self) -> None:
        response = self._vote("maybe")
        self.assertEqual(response.status_code, 400)

    def test_missing_content_returns_404(self) -> None:
        response = self._vote("up", content_id=999)
        self.assertEqual(response.status_code, 404)

    def test_requires_authentication(self) -> None:
        response = self.client.post(
            f"/api/content/{self.content.id}/vote",
            json={"vote": "up"},
        )
        self.assertEqual(response.status_code, 401)

    def test_non_integer_user_identifier_is_rejected(self) -> None:
        response = self.client.post(
            f"/api/content/{self.content.id}/vote",
            json={"vote": "up"},
            headers={"X-User-Id": "abc"},
        )
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
