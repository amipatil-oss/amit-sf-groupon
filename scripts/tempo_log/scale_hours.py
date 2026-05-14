import json
import sys


def scale_to_8h(entries):
    """Scale entries proportionally so scaled_minutes sums to exactly 480.

    Preserves all input fields except raw_minutes (replaced by scaled_minutes).
    Enforces 15-minute minimum per entry.
    """
    if not entries:
        return []

    total_raw = sum(e["raw_minutes"] for e in entries)

    if total_raw == 0:
        per = 480 // len(entries)
        remainder = 480 - per * len(entries)
        result = [{**{k: v for k, v in e.items() if k != "raw_minutes"}, "scaled_minutes": per} for e in entries]
        result[0]["scaled_minutes"] += remainder
        return result

    result = [
        {**{k: v for k, v in e.items() if k != "raw_minutes"}, "scaled_minutes": round(e["raw_minutes"] / total_raw * 480)}
        for e in entries
    ]

    # Fix rounding drift so total == 480 exactly
    diff = 480 - sum(r["scaled_minutes"] for r in result)
    if diff != 0:
        largest = max(range(len(result)), key=lambda i: result[i]["scaled_minutes"])
        result[largest]["scaled_minutes"] += diff

    # Enforce 15-minute minimum: steal from largest entry
    for i, r in enumerate(result):
        if r["scaled_minutes"] < 15:
            shortfall = 15 - r["scaled_minutes"]
            donor = max(range(len(result)), key=lambda j: result[j]["scaled_minutes"] if j != i else -1)
            result[donor]["scaled_minutes"] -= shortfall
            result[i]["scaled_minutes"] = 15

    return result


if __name__ == "__main__":
    entries = json.loads(sys.argv[1])
    print(json.dumps(scale_to_8h(entries), indent=2))
