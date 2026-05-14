import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts/tempo_log"))

from format_draft import format_draft_table


def test_contains_date_and_total():
    entries = [{"ticket_key": "A-1", "scaled_minutes": 480, "description": "work", "source": "Tempo"}]
    out = format_draft_table("2026-05-13", entries)
    assert "2026-05-13" in out
    assert "8h 00m" in out


def test_contains_ticket_keys():
    entries = [
        {"ticket_key": "SFDC-1", "scaled_minutes": 240, "description": "a", "source": "Calendar+Tempo"},
        {"ticket_key": "SFDC-2", "scaled_minutes": 240, "description": "b", "source": "Tempo"},
    ]
    out = format_draft_table("2026-05-13", entries)
    assert "SFDC-1" in out
    assert "SFDC-2" in out


def test_minutes_rendered_as_hours_minutes():
    entries = [{"ticket_key": "A-1", "scaled_minutes": 90, "description": "x", "source": "Tempo"}]
    out = format_draft_table("2026-05-13", entries)
    assert "1h 30m" in out


def test_unmatched_events_shown_when_present():
    entries = [{"ticket_key": "A-1", "scaled_minutes": 480, "description": "x", "source": "Tempo"}]
    out = format_draft_table("2026-05-13", entries, unmatched=["Design sync (no ticket)"])
    assert "Design sync" in out
    assert "Unmatched" in out


def test_no_unmatched_message_when_empty():
    entries = [{"ticket_key": "A-1", "scaled_minutes": 480, "description": "x", "source": "Tempo"}]
    out = format_draft_table("2026-05-13", entries)
    assert "none" in out or "Unmatched events: none" in out


def test_confirm_prompt_included():
    entries = [{"ticket_key": "A-1", "scaled_minutes": 480, "description": "x", "source": "Tempo"}]
    out = format_draft_table("2026-05-13", entries)
    assert "yes" in out.lower() and "cancel" in out.lower()
