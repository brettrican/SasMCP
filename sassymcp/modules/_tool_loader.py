"""SassyMCP Smart Tool Loader — Adaptive tool registration with usage tracking.

Tracks which tools are actually called, scores them, and enables
dynamic tool set management via MCP notifications/tools/list_changed.

Features:
- Usage frequency tracking (persisted to JSON)
- Exponential decay scoring (recent usage weighted higher)
- Tool group enable/disable at runtime
- Context window estimation
- Response minification for GitHub API payloads

Storage: ~/.sassymcp/tool_usage.json
"""

import json
import logging
import math
import os
import time
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("sassymcp.loader")

USAGE_DIR = Path.home() / ".sassymcp"
USAGE_FILE = USAGE_DIR / "tool_usage.json"
DECAY_HALF_LIFE = 7 * 86400  # 7 days in seconds — older usage decays


class ToolUsageTracker:
    """Tracks tool invocations with timestamps for ML-lite scoring."""

    def __init__(self):
        self._data: dict[str, list[float]] = {}
        self._load()

    def _load(self):
        try:
            if USAGE_FILE.exists():
                raw = json.loads(USAGE_FILE.read_text())
                self._data = raw.get("tools", {})
        except Exception as e:
            logger.warning(f"Failed to load tool usage: {e}")
            self._data = {}

    def _save(self):
        try:
            USAGE_DIR.mkdir(parents=True, exist_ok=True)
            # Prune: keep only last 500 invocations per tool, last 90 days
            cutoff = time.time() - 90 * 86400
            pruned = {}
            for tool, timestamps in self._data.items():
                recent = [t for t in timestamps if t > cutoff][-500:]
                if recent:
                    pruned[tool] = recent
            USAGE_FILE.write_text(json.dumps({"tools": pruned, "updated": time.time()}, indent=1))
        except Exception as e:
            logger.warning(f"Failed to save tool usage: {e}")

    def record(self, tool_name: str):
        """Record a tool invocation."""
        if tool_name not in self._data:
            self._data[tool_name] = []
        self._data[tool_name].append(time.time())
        self._save()

    def score(self, tool_name: str) -> float:
        """Score a tool 0.0-1.0 based on recency-weighted usage frequency.
        
        Uses exponential decay: recent invocations count more.
        Score formula: sum(e^(-lambda * age)) where lambda = ln(2) / half_life
        """
        timestamps = self._data.get(tool_name, [])
        if not timestamps:
            return 0.0
        now = time.time()
        lam = math.log(2) / DECAY_HALF_LIFE
        raw = sum(math.exp(-lam * (now - t)) for t in timestamps)
        # Normalize: 10+ weighted calls in last week = score 1.0
        return min(raw / 10.0, 1.0)

    def top_tools(self, n: int = 20) -> list[tuple[str, float]]:
        """Return top N tools by score."""
        scores = [(name, self.score(name)) for name in self._data]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:n]

    def get_stats(self) -> dict:
        """Return usage statistics."""
        now = time.time()
        day_cutoff = now - 86400
        week_cutoff = now - 7 * 86400

        total_calls = sum(len(v) for v in self._data.values())
        today_calls = sum(
            sum(1 for t in v if t > day_cutoff)
            for v in self._data.values()
        )
        week_calls = sum(
            sum(1 for t in v if t > week_cutoff)
            for v in self._data.values()
        )
        unique_tools = len(self._data)

        return {
            "unique_tools_ever": unique_tools,
            "total_invocations": total_calls,
            "invocations_today": today_calls,
            "invocations_this_week": week_calls,
            "top_10": self.top_tools(10),
        }


# Module-level singleton
_tracker: Optional[ToolUsageTracker] = None


def get_tracker() -> ToolUsageTracker:
    global _tracker
    if _tracker is None:
        _tracker = ToolUsageTracker()
    return _tracker


# ── Tool Groups ────────────────────────────────────────────────────────

# Define which modules belong to which load tier
TOOL_GROUPS = {
    "meta": {
        "modules": ["meta"],
        "description": "Context estimation, tool usage stats, group management (always loaded)",
        "always_load": True,
    },
    "core": {
        "modules": ["fileops", "shell", "ui_automation", "editor", "audit", "session"],
        "description": "File operations, shell commands, desktop automation, surgical editing, audit logging, persistent terminal sessions",
        "always_load": True,
    },
    "android": {
        "modules": ["adb", "phone_screen"],
        "description": "ADB device control, screen mirroring",
        "always_load": False,
    },
    "system": {
        "modules": ["network_audit", "process_manager", "security_audit",
                     "registry", "bluetooth", "eventlog", "clipboard"],
        "description": "System monitoring, security, networking",
        "always_load": False,
    },
    "github_quick": {
        "modules": ["github_quick"],
        "description": "Daily-driver GitHub tools (6 tools)",
        "always_load": True,
    },
    "github_full": {
        "modules": ["github_ops"],
        "description": "Full GitHub API (80 tools) — heavy context cost",
        "always_load": False,
    },
    "v020": {
        "modules": ["vision", "app_launcher", "web_inspector", "crosslink"],
        "description": "Vision, app launcher, web inspector, crosslink",
        "always_load": False,
    },
    "persona": {
        "modules": ["persona"],
        "description": "SaS workflow persona and dev practices",
        "always_load": True,
    },
    "utility": {
        "modules": ["utility"],
        "description": "Env vars, toast notifications, zip/tar archives, file diff, HTTP requests",
        "always_load": True,
    },
}


def get_default_modules() -> list[str]:
    """Return modules that should load by default (always_load=True)."""
    modules = []
    for group in TOOL_GROUPS.values():
        if group["always_load"]:
            modules.extend(group["modules"])
    return modules


def get_all_modules() -> list[str]:
    """Return all known module names."""
    modules = []
    for group in TOOL_GROUPS.values():
        modules.extend(group["modules"])
    return modules


def get_group_info() -> dict:
    """Return group info for display."""
    return {
        name: {
            "description": g["description"],
            "modules": g["modules"],
            "always_load": g["always_load"],
            "tool_count": "varies",
        }
        for name, g in TOOL_GROUPS.items()
    }


# ── Context Window Estimation ────────────────────────────────────────

def estimate_tool_context_tokens(tool_definitions: list[dict]) -> dict:
    """Estimate how many tokens the tool definitions consume.
    
    Each tool definition includes: name, description, parameter JSON schema.
    Rough estimate: 1 token ≈ 4 chars of JSON.
    """
    total_chars = 0
    tool_sizes = []
    for tool in tool_definitions:
        tool_json = json.dumps(tool, separators=(",", ":"))
        chars = len(tool_json)
        total_chars += chars
        tool_sizes.append({
            "name": tool.get("name", "unknown"),
            "chars": chars,
            "est_tokens": chars // 4,
        })

    tool_sizes.sort(key=lambda x: x["chars"], reverse=True)

    return {
        "total_chars": total_chars,
        "est_tokens": total_chars // 4,
        "est_percent_of_200k": round((total_chars // 4) / 200000 * 100, 1),
        "tool_count": len(tool_definitions),
        "top_10_heaviest": tool_sizes[:10],
    }


# ── Response Minification ────────────────────────────────────────────

# Keys to strip from GitHub API responses to save context
GITHUB_STRIP_KEYS = {
    "node_id", "gravatar_id", "followers_url", "following_url",
    "gists_url", "starred_url", "subscriptions_url", "organizations_url",
    "repos_url", "events_url", "received_events_url", "forks_url",
    "keys_url", "collaborators_url", "teams_url", "hooks_url",
    "issue_events_url", "assignees_url", "branches_url", "tags_url",
    "blobs_url", "git_tags_url", "git_refs_url", "trees_url",
    "statuses_url", "languages_url", "stargazers_url", "contributors_url",
    "subscribers_url", "subscription_url", "commits_url", "git_commits_url",
    "comments_url", "issue_comment_url", "contents_url", "compare_url",
    "merges_url", "archive_url", "downloads_url", "issues_url",
    "pulls_url", "milestones_url", "notifications_url", "labels_url",
    "releases_url", "deployments_url", "git_url", "ssh_url",
    "clone_url", "svn_url", "mirror_url", "review_comments_url",
    "review_comment_url", "timeline_url", "members_url",
    "public_members_url", "avatar_url", "diff_url", "patch_url",
    "_links",
}


def minify_github_response(data: Any, depth: int = 0) -> Any:
    """Strip URL-heavy metadata from GitHub API responses.
    
    Saves 40-70% of tokens on typical responses.
    Preserves all actionable data (ids, shas, names, states, bodies).
    """
    if depth > 15:
        return data

    if isinstance(data, dict):
        return {
            k: minify_github_response(v, depth + 1)
            for k, v in data.items()
            if k not in GITHUB_STRIP_KEYS
        }
    elif isinstance(data, list):
        return [minify_github_response(item, depth + 1) for item in data]
    else:
        return data


def minify_file_listing(data: Any) -> Any:
    """Minify directory listing responses — keep only name, path, sha, type, size."""
    if isinstance(data, list):
        return [
            {k: item[k] for k in ("name", "path", "sha", "type", "size") if k in item}
            for item in data
            if isinstance(item, dict)
        ]
    return data
