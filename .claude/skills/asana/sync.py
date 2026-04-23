#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["requests>=2.31", "rich>=13.0"]
# ///
"""
Asana bulk sync — downloads tasks/projects to SQLite via REST API.

Usage:
  uv run sync.py --list-workspaces
  uv run sync.py -w <name-or-gid> [options]

Requires ASANA_PAT env var (Personal Access Token).
Get one at: https://app.asana.com/0/my-apps
"""

import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

try:
    import requests
    from rich.console import Console
    from rich.progress import Progress
except ImportError:
    print("Run with: uv run sync.py [args]")
    sys.exit(1)

console = Console()
BASE = "https://app.asana.com/api/1.0"


# ── API helpers ───────────────────────────────────────────────────────

def api_get(pat: str, path: str, params: dict | None = None) -> list[dict]:
    """GET with automatic pagination. Returns all results."""
    headers = {"Authorization": f"Bearer {pat}"}
    url = f"{BASE}/{path}"
    if params is None:
        params = {}
    params.setdefault("limit", 100)
    all_data = []
    while url:
        resp = requests.get(url, headers=headers, params=params)
        if resp.status_code == 401:
            console.print("[red]401 Unauthorized — check your ASANA_PAT[/red]")
            sys.exit(1)
        if not resp.ok:
            console.print(f"[red]API error {resp.status_code}: {resp.text[:300]}[/red]")
            resp.raise_for_status()
        body = resp.json()
        all_data.extend(body.get("data", []))
        next_page = body.get("next_page")
        if next_page and next_page.get("offset"):
            params["offset"] = next_page["offset"]
        else:
            url = None
    return all_data


# ── DB Setup ──────────────────────────────────────────────────────────

def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS workspaces (
            gid TEXT PRIMARY KEY,
            name TEXT,
            synced_at TEXT
        );
        CREATE TABLE IF NOT EXISTS projects (
            gid TEXT PRIMARY KEY,
            workspace_gid TEXT,
            name TEXT,
            notes TEXT,
            color TEXT,
            archived INTEGER,
            created_at TEXT,
            modified_at TEXT,
            due_date TEXT,
            start_on TEXT,
            owner_gid TEXT,
            owner_name TEXT,
            synced_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sections (
            gid TEXT PRIMARY KEY,
            project_gid TEXT,
            name TEXT,
            synced_at TEXT
        );
        CREATE TABLE IF NOT EXISTS tasks (
            gid TEXT PRIMARY KEY,
            name TEXT,
            notes TEXT,
            completed INTEGER,
            completed_at TEXT,
            assignee_gid TEXT,
            assignee_name TEXT,
            due_on TEXT,
            due_at TEXT,
            start_on TEXT,
            start_at TEXT,
            created_at TEXT,
            modified_at TEXT,
            permalink_url TEXT,
            resource_type TEXT,
            num_subtasks INTEGER,
            parent_gid TEXT,
            custom_fields_json TEXT,
            tags_json TEXT,
            synced_at TEXT
        );
        CREATE TABLE IF NOT EXISTS task_projects (
            task_gid TEXT,
            project_gid TEXT,
            section_gid TEXT,
            PRIMARY KEY (task_gid, project_gid)
        );
        CREATE TABLE IF NOT EXISTS task_stories (
            gid TEXT PRIMARY KEY,
            task_gid TEXT,
            type TEXT,
            resource_subtype TEXT,
            text TEXT,
            created_at TEXT,
            created_by_gid TEXT,
            created_by_name TEXT,
            synced_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT,
            finished_at TEXT,
            workspace_gid TEXT,
            projects_synced INTEGER,
            tasks_synced INTEGER,
            stories_synced INTEGER,
            status TEXT
        );
    """)
    return conn


# ── Sync Functions ────────────────────────────────────────────────────

TASK_FIELDS = ",".join([
    "gid", "name", "notes", "completed", "completed_at",
    "assignee.gid", "assignee.name",
    "due_on", "due_at", "start_on", "start_at",
    "created_at", "modified_at", "permalink_url",
    "resource_type", "num_subtasks", "parent.gid",
    "custom_fields", "tags.name",
    "memberships.project.gid", "memberships.section.gid",
])

PROJECT_FIELDS = ",".join([
    "gid", "name", "notes", "color", "archived",
    "created_at", "modified_at", "due_date", "start_on",
    "owner.gid", "owner.name",
])


def resolve_workspace(pat: str, workspace_ref: str) -> dict:
    workspaces = api_get(pat, "workspaces", {"opt_fields": "gid,name"})
    for ws in workspaces:
        if ws["gid"] == workspace_ref or ws["name"].lower() == workspace_ref.lower():
            return ws
    console.print(f"[red]Workspace '{workspace_ref}' not found.[/red]")
    console.print("Available workspaces:")
    for ws in workspaces:
        console.print(f"  {ws['name']}  ({ws['gid']})")
    sys.exit(1)


def sync_projects(pat: str, conn: sqlite3.Connection, workspace_gid: str,
                  project_filter: str | None = None) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    projects = api_get(pat, "projects", {
        "workspace": workspace_gid,
        "opt_fields": PROJECT_FIELDS,
    })

    if project_filter:
        filters = [f.strip().lower() for f in project_filter.split(",")]
        projects = [p for p in projects if any(f in p["name"].lower() for f in filters)]

    for p in projects:
        owner = p.get("owner") or {}
        conn.execute("""
            INSERT OR REPLACE INTO projects
            (gid, workspace_gid, name, notes, color, archived, created_at, modified_at,
             due_date, start_on, owner_gid, owner_name, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["gid"], workspace_gid, p.get("name"), p.get("notes"),
            p.get("color"), int(p.get("archived", False)),
            p.get("created_at"), p.get("modified_at"),
            p.get("due_date"), p.get("start_on"),
            owner.get("gid"), owner.get("name"), now,
        ))
    conn.commit()
    return projects


def sync_sections(pat: str, conn: sqlite3.Connection, project_gid: str) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    sections = api_get(pat, f"projects/{project_gid}/sections", {"opt_fields": "gid,name"})
    for s in sections:
        conn.execute("INSERT OR REPLACE INTO sections (gid, project_gid, name, synced_at) VALUES (?, ?, ?, ?)",
                     (s["gid"], project_gid, s.get("name"), now))
    conn.commit()
    return sections


def sync_tasks(pat: str, conn: sqlite3.Connection, project_gid: str,
               include_completed: bool = False) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    params = {"opt_fields": TASK_FIELDS}
    if not include_completed:
        params["completed_since"] = "now"

    tasks = api_get(pat, f"projects/{project_gid}/tasks", params)

    if include_completed:
        # Get all tasks (including completed)
        all_tasks = api_get(pat, f"projects/{project_gid}/tasks", {"opt_fields": TASK_FIELDS})
        seen = {t["gid"] for t in tasks}
        for t in all_tasks:
            if t["gid"] not in seen:
                tasks.append(t)

    for t in tasks:
        custom_fields = json.dumps(t.get("custom_fields", []), default=str)
        tags = json.dumps([tag.get("name") for tag in (t.get("tags") or [])], default=str)
        assignee = t.get("assignee") or {}
        parent = t.get("parent") or {}

        conn.execute("""
            INSERT OR REPLACE INTO tasks
            (gid, name, notes, completed, completed_at, assignee_gid, assignee_name,
             due_on, due_at, start_on, start_at, created_at, modified_at,
             permalink_url, resource_type, num_subtasks, parent_gid,
             custom_fields_json, tags_json, synced_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            t["gid"], t.get("name"), t.get("notes"),
            int(t.get("completed", False)), t.get("completed_at"),
            assignee.get("gid"), assignee.get("name"),
            t.get("due_on"), t.get("due_at"),
            t.get("start_on"), t.get("start_at"),
            t.get("created_at"), t.get("modified_at"),
            t.get("permalink_url"), t.get("resource_type"),
            t.get("num_subtasks"), parent.get("gid"),
            custom_fields, tags, now,
        ))

        for m in (t.get("memberships") or []):
            proj = (m.get("project") or {}).get("gid")
            sec = (m.get("section") or {}).get("gid")
            if proj:
                conn.execute("INSERT OR REPLACE INTO task_projects (task_gid, project_gid, section_gid) VALUES (?, ?, ?)",
                             (t["gid"], proj, sec))
    conn.commit()
    return tasks


def sync_stories(pat: str, conn: sqlite3.Connection, task_gid: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    stories = api_get(pat, f"tasks/{task_gid}/stories", {
        "opt_fields": "gid,type,resource_subtype,text,created_at,created_by.gid,created_by.name"
    })
    count = 0
    keep_subtypes = {"comment_added", "marked_complete", "marked_incomplete",
                     "assigned", "unassigned", "due_date_changed",
                     "name_changed", "notes_changed"}
    for s in stories:
        if s.get("resource_subtype") in keep_subtypes:
            created_by = s.get("created_by") or {}
            conn.execute("""
                INSERT OR REPLACE INTO task_stories
                (gid, task_gid, type, resource_subtype, text, created_at,
                 created_by_gid, created_by_name, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                s["gid"], task_gid, s.get("type"), s.get("resource_subtype"),
                s.get("text"), s.get("created_at"),
                created_by.get("gid"), created_by.get("name"), now,
            ))
            count += 1
    conn.commit()
    return count


# ── Main ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Sync Asana workspace to SQLite")
    parser.add_argument("--workspace", "-w", help="Workspace name or GID")
    parser.add_argument("--db", default="asana.db", help="SQLite database path (default: asana.db)")
    parser.add_argument("--projects", "-p", help="Comma-separated project name filter (substring match)")
    parser.add_argument("--include-completed", action="store_true", help="Include completed tasks")
    parser.add_argument("--include-stories", action="store_true", help="Sync task comments/stories (slow)")
    parser.add_argument("--list-workspaces", action="store_true", help="Just list available workspaces")
    parser.add_argument("--list-projects", action="store_true", help="Just list projects in workspace")
    args = parser.parse_args()

    pat = os.environ.get("ASANA_PAT")
    if not pat:
        console.print("[red]Set ASANA_PAT env var with your Personal Access Token[/red]")
        console.print("Get one at: https://app.asana.com/0/my-apps")
        sys.exit(1)

    if args.list_workspaces:
        for ws in api_get(pat, "workspaces", {"opt_fields": "gid,name"}):
            console.print(f"  {ws['name']}  ({ws['gid']})")
        return

    if not args.workspace:
        console.print("[red]--workspace/-w is required (use --list-workspaces to find it)[/red]")
        sys.exit(1)

    workspace = resolve_workspace(pat, args.workspace)
    console.print(f"[bold]Workspace:[/bold] {workspace['name']} ({workspace['gid']})")

    if args.list_projects:
        for p in api_get(pat, "projects", {"workspace": workspace["gid"], "opt_fields": "gid,name"}):
            console.print(f"  {p['name']}  ({p['gid']})")
        return

    conn = init_db(args.db)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT OR REPLACE INTO workspaces (gid, name, synced_at) VALUES (?, ?, ?)",
                 (workspace["gid"], workspace["name"], now))

    log_id = conn.execute("INSERT INTO sync_log (started_at, workspace_gid, status) VALUES (?, ?, 'running')",
                          (now, workspace["gid"])).lastrowid
    conn.commit()

    total_tasks = 0
    total_stories = 0

    try:
        with Progress(console=console) as progress:
            projects = sync_projects(pat, conn, workspace["gid"], args.projects)
            console.print(f"[green]Synced {len(projects)} projects[/green]")

            task_bar = progress.add_task("Syncing tasks...", total=len(projects))

            for proj in projects:
                sync_sections(pat, conn, proj["gid"])
                tasks = sync_tasks(pat, conn, proj["gid"], args.include_completed)
                total_tasks += len(tasks)

                if args.include_stories:
                    for t in tasks:
                        total_stories += sync_stories(pat, conn, t["gid"])

                progress.update(task_bar, advance=1,
                                description=f"[cyan]{proj['name']}[/cyan] ({len(tasks)} tasks)")

        conn.execute("""
            UPDATE sync_log SET finished_at=?, projects_synced=?, tasks_synced=?, stories_synced=?, status='done'
            WHERE id=?
        """, (datetime.now(timezone.utc).isoformat(), len(projects), total_tasks, total_stories, log_id))
        conn.commit()

        console.print(f"\n[bold green]Done![/bold green] {len(projects)} projects, {total_tasks} tasks, {total_stories} stories → {args.db}")

    except Exception as e:
        conn.execute("UPDATE sync_log SET finished_at=?, status=? WHERE id=?",
                     (datetime.now(timezone.utc).isoformat(), f"error: {e}", log_id))
        conn.commit()
        console.print(f"[red]Error: {e}[/red]")
        raise


if __name__ == "__main__":
    main()
