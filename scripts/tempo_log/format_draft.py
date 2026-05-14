import json
import sys


def _fmt(minutes):
    return f"{minutes // 60}h {minutes % 60:02d}m"


def format_draft_table(date_str, entries, unmatched=None):
    total = sum(e["scaled_minutes"] for e in entries)
    lines = [
        f"Date: {date_str}  |  Total: {_fmt(total)}",
        "",
        f"{'Jira Ticket':<14} {'Duration':<10} {'Description':<35} {'Source'}",
        "-" * 76,
    ]
    for e in entries:
        lines.append(
            f"{e['ticket_key']:<14} {_fmt(e['scaled_minutes']):<10} "
            f"{e['description'][:34]:<35} {e.get('source', '')}"
        )
    lines.append("")
    if unmatched:
        lines.append(f"Unmatched events ({len(unmatched)}):")
        for u in unmatched:
            lines.append(f"  - {u}")
    else:
        lines.append("Unmatched events: none")
    lines.append("")
    lines.append("Confirm to log to Tempo? (yes / edit / cancel)")
    return "\n".join(lines)


if __name__ == "__main__":
    entries = json.loads(sys.argv[1])
    unmatched = json.loads(sys.argv[2]) if len(sys.argv) > 2 else []
    date_str = sys.argv[3] if len(sys.argv) > 3 else "TODAY"
    print(format_draft_table(date_str, entries, unmatched or None))
