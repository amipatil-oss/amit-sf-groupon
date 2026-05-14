import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts/tempo_log"))

from scale_hours import scale_to_8h


def test_two_equal_entries_split_evenly():
    entries = [
        {"ticket_key": "A-1", "raw_minutes": 60, "description": "a", "source": "Tempo"},
        {"ticket_key": "B-2", "raw_minutes": 60, "description": "b", "source": "Tempo"},
    ]
    result = scale_to_8h(entries)
    assert sum(e["scaled_minutes"] for e in result) == 480
    assert result[0]["scaled_minutes"] == 240
    assert result[1]["scaled_minutes"] == 240


def test_proportional_scaling():
    entries = [
        {"ticket_key": "A-1", "raw_minutes": 120, "description": "a", "source": "Tempo"},
        {"ticket_key": "B-2", "raw_minutes": 60, "description": "b", "source": "Tempo"},
    ]
    result = scale_to_8h(entries)
    assert sum(e["scaled_minutes"] for e in result) == 480
    assert result[0]["scaled_minutes"] == 320  # 480 * 2/3
    assert result[1]["scaled_minutes"] == 160  # 480 * 1/3


def test_single_entry_gets_full_8h():
    entries = [{"ticket_key": "A-1", "raw_minutes": 90, "description": "a", "source": "Tempo"}]
    result = scale_to_8h(entries)
    assert result[0]["scaled_minutes"] == 480


def test_minimum_15_minutes_enforced():
    entries = [
        {"ticket_key": "A-1", "raw_minutes": 200, "description": "a", "source": "Tempo"},
        {"ticket_key": "B-2", "raw_minutes": 1, "description": "b", "source": "Tempo"},
    ]
    result = scale_to_8h(entries)
    assert sum(e["scaled_minutes"] for e in result) == 480
    assert result[1]["scaled_minutes"] >= 15


def test_total_always_480():
    entries = [
        {"ticket_key": "A-1", "raw_minutes": 1, "description": "a", "source": "Tempo"},
        {"ticket_key": "B-2", "raw_minutes": 1, "description": "b", "source": "Tempo"},
        {"ticket_key": "C-3", "raw_minutes": 1, "description": "c", "source": "Tempo"},
    ]
    result = scale_to_8h(entries)
    assert sum(e["scaled_minutes"] for e in result) == 480


def test_preserves_all_fields():
    entries = [{"ticket_key": "SFDC-999", "raw_minutes": 60, "description": "sprint", "source": "Calendar+Tempo"}]
    result = scale_to_8h(entries)
    assert result[0]["ticket_key"] == "SFDC-999"
    assert result[0]["description"] == "sprint"
    assert result[0]["source"] == "Calendar+Tempo"
    assert "raw_minutes" not in result[0]
