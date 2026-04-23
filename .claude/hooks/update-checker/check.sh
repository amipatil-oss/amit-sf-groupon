#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/update-checker.json"
LAST_CHECK="$SCRIPT_DIR/.last_check"
RESULTS="$SCRIPT_DIR/.check_results"
INSTALLED_PLUGINS="$HOME/.claude/plugins/installed_plugins.json"

# --- Interval gate ---
export CONFIG
INTERVAL_DAYS=$(python3 -c "
import json, os
with open(os.environ['CONFIG']) as f:
    print(json.load(f).get('check_interval_days', 7))
")
INTERVAL_SECS=$((INTERVAL_DAYS * 86400))
NOW=$(date +%s)

if [ -f "$LAST_CHECK" ]; then
    LAST=$(cat "$LAST_CHECK")
    ELAPSED=$((NOW - LAST))
    if [ "$ELAPSED" -lt "$INTERVAL_SECS" ]; then
        exit 0
    fi
fi

# --- Export SCRIPT_DIR so the Python heredoc can access it ---
export SCRIPT_DIR

# --- Run checks via Python ---
python3 << 'PYTHON_SCRIPT'
import json, shlex, subprocess, os, time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

script_dir = Path(os.environ["SCRIPT_DIR"])

config_path = script_dir / "update-checker.json"
results_path = script_dir / ".check_results"
npm_versions_path = script_dir / ".npm_versions"
installed_path = Path.home() / ".claude" / "plugins" / "installed_plugins.json"

with open(config_path) as f:
    config = json.load(f)

if installed_path.exists():
    with open(installed_path) as f:
        installed = json.load(f)
else:
    installed = {"plugins": {}}

plugins_installed = installed.get("plugins", {})
results = {"timestamp": time.time(), "plugins": {}, "npm": {}, "health": {}, "repos": {}}


def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip(), r.returncode == 0
    except Exception:
        return "", False


def check_plugin(name, plugin_conf):
    entry = plugins_installed.get(name, [{}])[0]
    local_sha = entry.get("gitCommitSha", "")
    version = entry.get("version", "?")
    install_path = entry.get("installPath", "")

    if not local_sha:
        return name, {"status": "unknown", "reason": "no local SHA"}

    remote_url = plugin_conf.get("remote", "")

    if not remote_url and install_path and os.path.isdir(os.path.join(install_path, ".git")):
        remote_url, ok = run(f"git -C {shlex.quote(install_path)} remote get-url origin")
        if not ok:
            remote_url = ""

    if not remote_url:
        marketplace = name.split("@")[-1] if "@" in name else ""
        if marketplace:
            cache_base = Path.home() / ".claude" / "plugins" / "cache" / marketplace
            if cache_base.is_dir() and (cache_base / ".git").is_dir():
                remote_url, ok = run(f"git -C {shlex.quote(str(cache_base))} remote get-url origin")
                if not ok:
                    remote_url = ""

    if not remote_url:
        # Plugin installed without git history — can't compare, just report installed
        return name, {"status": "installed", "version": version, "reason": "no git tracking"}

    out, ok = run(f"git ls-remote {shlex.quote(remote_url)} HEAD", timeout=15)
    if not ok:
        return name, {"status": "check_failed", "reason": "git ls-remote failed"}

    remote_sha = out.split()[0] if out else ""
    if not remote_sha:
        return name, {"status": "check_failed", "reason": "empty remote SHA"}

    if remote_sha != local_sha:
        return name, {
            "status": "update_available",
            "version": version,
            "local_sha": local_sha[:12],
            "remote_sha": remote_sha[:12]
        }
    return name, {"status": "up_to_date", "version": version}


def check_npm(package):
    out, ok = run(f"npm view {shlex.quote(package)} version 2>/dev/null", timeout=15)
    if not ok or not out:
        return package, {"status": "check_failed", "reason": "npm view failed"}
    return package, {"status": "ok", "latest": out}


def check_health(name, url):
    out, ok = run(
        f"curl -s -o /dev/null --head -w '%{{http_code}}' --connect-timeout 5 --max-time 10 {shlex.quote(url)}",
        timeout=15
    )
    code = int(out) if out.isdigit() else 0
    if 200 <= code < 400:
        return name, {"status": "ok", "code": code}
    return name, {"status": "unreachable", "code": code}


def check_repo(repo, repo_conf):
    """Watch a GitHub repo for recent commits matching keywords."""
    keywords = [k.lower() for k in repo_conf.get("keywords", [])]
    # Fetch recent commits (last 7 days) via GitHub API
    out, ok = run(
        f"curl -s -H 'Accept: application/vnd.github.v3+json' "
        f"'https://api.github.com/repos/{repo}/commits?per_page=20'",
        timeout=20
    )
    if not ok or not out:
        return repo, {"status": "check_failed", "reason": "GitHub API request failed"}

    try:
        commits = json.loads(out)
        if isinstance(commits, dict) and "message" in commits:
            return repo, {"status": "check_failed", "reason": commits["message"]}
    except json.JSONDecodeError:
        return repo, {"status": "check_failed", "reason": "invalid JSON response"}

    matched = []
    for commit in commits[:20]:
        msg = commit.get("commit", {}).get("message", "").lower()
        sha = commit.get("sha", "")[:8]
        date = commit.get("commit", {}).get("author", {}).get("date", "")[:10]
        hits = [kw for kw in keywords if kw in msg]
        if hits:
            matched.append({
                "sha": sha,
                "date": date,
                "message": commit.get("commit", {}).get("message", "").split("\n")[0][:80],
                "keywords": hits
            })

    if matched:
        return repo, {"status": "changes_found", "matches": matched}
    return repo, {"status": "no_changes", "commits_checked": len(commits[:20])}


# Run all checks in parallel
with ThreadPoolExecutor(max_workers=8) as pool:
    futures = {}

    for name, conf in config.get("plugins", {}).items():
        futures[pool.submit(check_plugin, name, conf)] = ("plugin", name)

    for pkg in config.get("npm_packages", []):
        futures[pool.submit(check_npm, pkg)] = ("npm", pkg)

    for name, url in config.get("http_health", {}).items():
        futures[pool.submit(check_health, name, url)] = ("health", name)

    for repo, repo_conf in config.get("repos_to_watch", {}).items():
        futures[pool.submit(check_repo, repo, repo_conf)] = ("repo", repo)

    for future in as_completed(futures):
        category, key = futures[future]
        try:
            result_key, result_val = future.result()
            if category == "plugin":
                results["plugins"][result_key] = result_val
            elif category == "npm":
                results["npm"][result_key] = result_val
            elif category == "repo":
                results["repos"][result_key] = result_val
            else:
                results["health"][result_key] = result_val
        except Exception as e:
            bucket = {"plugin": "plugins", "npm": "npm", "health": "health", "repo": "repos"}[category]
            results[bucket][key] = {"status": "check_failed", "reason": str(e)}

# Save results
with open(results_path, "w") as f:
    json.dump(results, f, indent=2)

# Load previous npm versions for comparison
prev_npm = {}
if npm_versions_path.exists():
    with open(npm_versions_path) as f:
        prev_npm = json.load(f)

# Save current npm versions
current_npm = {}
for pkg, info in results["npm"].items():
    if info.get("latest"):
        current_npm[pkg] = info["latest"]
if current_npm:
    with open(npm_versions_path, "w") as f:
        json.dump(current_npm, f, indent=2)

# Format output
has_updates = False
lines = []
lines.append("\U0001f504 CoS Update Check")
lines.append("\u2501" * 40)

# Plugins
plugin_lines = []
for name, info in sorted(results["plugins"].items()):
    display = name.split("@")[0]
    st = info["status"]
    if st == "up_to_date":
        v = info.get("version", "")
        plugin_lines.append(f"  \u2705 {display} \u2014 up to date ({v})")
    elif st == "update_available":
        has_updates = True
        v = info.get("version", "")
        plugin_lines.append(f"  \U0001f538 {display} \u2014 update available (current: {v})")
    elif st == "installed":
        plugin_lines.append(f"  \u2796 {display} \u2014 installed ({info.get('reason', '')})")
    elif st == "check_failed":
        plugin_lines.append(f"  \u26a0\ufe0f  {display} \u2014 check failed ({info.get('reason', '')})")
    else:
        plugin_lines.append(f"  \u2753 {display} \u2014 {st}")

if plugin_lines:
    lines.append("Plugins:")
    lines.extend(plugin_lines)

# NPM
npm_lines = []
for pkg, info in sorted(results["npm"].items()):
    if info.get("status") == "ok":
        latest = info["latest"]
        prev = prev_npm.get(pkg, "")
        if prev and prev != latest:
            has_updates = True
            npm_lines.append(f"  \U0001f538 {pkg} \u2014 {prev} \u2192 {latest}")
        else:
            npm_lines.append(f"  \u2705 {pkg} \u2014 {latest}")
    else:
        npm_lines.append(f"  \u26a0\ufe0f  {pkg} \u2014 check failed")

if npm_lines:
    lines.append("NPM packages:")
    lines.extend(npm_lines)

# Health
health_lines = []
for name, info in sorted(results["health"].items()):
    if info["status"] == "ok":
        health_lines.append(f"  \u2705 {name} \u2014 ok")
    else:
        health_lines.append(f"  \u274c {name} \u2014 unreachable (HTTP {info.get('code', '?')})")

if health_lines:
    lines.append("MCP servers:")
    lines.extend(health_lines)

# Watched repos
repo_lines = []
repo_significant = False
for repo, info in sorted(results["repos"].items()):
    if info["status"] == "changes_found":
        matches = info["matches"]
        repo_significant = True
        has_updates = True
        repo_lines.append(f"  \U0001f538 {repo} \u2014 {len(matches)} relevant commit(s):")
        for m in matches[:5]:
            kws = ", ".join(m["keywords"])
            repo_lines.append(f"    \u2022 {m['sha']} ({m['date']}) {m['message']} [{kws}]")
        if len(matches) > 5:
            repo_lines.append(f"    ... and {len(matches) - 5} more")
    elif info["status"] == "no_changes":
        repo_lines.append(f"  \u2705 {repo} \u2014 no relevant changes ({info['commits_checked']} commits checked)")
    else:
        repo_lines.append(f"  \u26a0\ufe0f  {repo} \u2014 check failed ({info.get('reason', '')})")

if repo_lines:
    lines.append("Watched repos:")
    lines.extend(repo_lines)

output = "\n".join(lines)
print(output)

if has_updates:
    print("\n\u26a1 Updates available. Run `/plugin` to update plugins.")

# macOS notification for significant repo changes
if repo_significant:
    try:
        import subprocess as sp
        sp.run([
            "osascript", "-e",
            'display notification "Watched repos have significant changes" '
            'with title "CoS Update Check" sound name "default"'
        ], timeout=5)
    except Exception:
        pass
PYTHON_SCRIPT

# Update timestamp
echo "$NOW" > "$LAST_CHECK"
