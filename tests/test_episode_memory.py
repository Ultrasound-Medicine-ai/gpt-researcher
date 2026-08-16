from datetime import datetime, timedelta, timezone

from rag.episode_memory import episode_metadata, episode_should_rollover
from rag.retrieve import _active_episode_sql


def test_episode_metadata_is_active_and_has_retention_fields():
    now = datetime(2026, 8, 15, tzinfo=timezone.utc)
    metadata = episode_metadata(episode_id="episode-1", now=now, topic_key="redis")
    assert metadata["episode_status"] == "active"
    assert metadata["episode_id"] == "episode-1"
    assert metadata["topic_key"] == "redis"
    assert metadata["expires_at"] > metadata["created_at"]


def test_episode_rolls_over_when_idle_or_archived(monkeypatch):
    monkeypatch.setenv("EPISODE_MEMORY_IDLE_MINUTES", "45")
    now = datetime(2026, 8, 15, tzinfo=timezone.utc)
    active = episode_metadata(episode_id="episode-1", now=now)
    assert not episode_should_rollover(active, now=now + timedelta(minutes=44))
    assert episode_should_rollover(active, now=now + timedelta(minutes=46))
    active["episode_status"] = "archived"
    assert episode_should_rollover(active, now=now)


def test_episode_rolls_over_on_topic_switch_or_expiry():
    now = datetime(2026, 8, 15, tzinfo=timezone.utc)
    metadata = episode_metadata(episode_id="episode-1", now=now, topic_key="redis")
    assert episode_should_rollover(metadata, now=now, topic_key="fastapi")
    assert episode_should_rollover(metadata, now=now + timedelta(days=31))


def test_normal_retrieval_excludes_archived_episode_only():
    predicate = _active_episode_sql()
    assert "chat_episode" in predicate
    assert "episode_status" in predicate
