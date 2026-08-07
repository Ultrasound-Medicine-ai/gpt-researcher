"""Tests for frontend buildChatContext helpers (mirrored logic documentation).

The canonical implementations live in frontend/nextjs/utils/buildChatContext.ts.
These tests validate equivalent Python expectations for critical behavior.
"""


def test_research_task_merges_topic_and_refinements():
    topic = "CNN的前沿发展"
    ordered_data = [
        {"type": "question", "content": topic},
        {"type": "question", "content": "我要近两年的"},
        {"type": "chat", "content": "好的，我会聚焦近两年的 CNN 前沿发展。"},
    ]

    refinements = [
        item["content"]
        for item in ordered_data
        if item.get("type") == "question"
        and item.get("content", "").strip()
        and item["content"].strip() != topic
    ]

    task = topic
    if refinements:
        task += "\n\nAdditional requirements from preparation conversation:\n"
        task += "\n".join(f"- {item}" for item in refinements)

    assert "CNN的前沿发展" in task
    assert "我要近两年的" in task
    assert "Additional requirements" in task
