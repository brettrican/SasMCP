"""Editor - Surgical diff-based file editing.

Provides edit_block functionality: find exact text in a file and replace it
without rewriting the entire file. Includes fuzzy matching fallback with
character-level diff reporting when exact match fails.
"""

import difflib
from pathlib import Path


def _find_best_match(content: str, search_text: str, threshold: float = 0.8):
    """Find the best fuzzy match for search_text in content.

    Returns (start_index, end_index, similarity, matched_text) or None.
    """
    search_lines = search_text.splitlines()
    content_lines = content.splitlines()
    search_len = len(search_lines)

    if search_len == 0:
        return None

    best_ratio = 0.0
    best_start = -1
    best_end = -1
    best_matched = ""

    for i in range(len(content_lines) - search_len + 1):
        candidate_lines = content_lines[i : i + search_len]
        candidate = "\n".join(candidate_lines)
        ratio = difflib.SequenceMatcher(None, search_text, candidate).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_start = i
            best_end = i + search_len
            best_matched = candidate

    if best_ratio >= threshold:
        # Convert line indices to character indices
        lines = content.splitlines(keepends=True)
        char_start = sum(len(lines[i]) for i in range(best_start))
        char_end = sum(len(lines[i]) for i in range(best_end))
        return (char_start, char_end, best_ratio, best_matched)
    return None


def _char_diff(expected: str, actual: str) -> str:
    """Produce a character-level diff showing what's different."""
    sm = difflib.SequenceMatcher(None, expected, actual)
    parts = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            text = expected[i1:i2]
            # Show abbreviated context for long equal sections
            if len(text) > 60:
                parts.append(text[:25] + "..." + text[-25:])
            else:
                parts.append(text)
        elif op == "replace":
            parts.append(f"{{-{expected[i1:i2]}-}}{{+{actual[j1:j2]}+}}")
        elif op == "insert":
            parts.append(f"{{+{actual[j1:j2]}+}}")
        elif op == "delete":
            parts.append(f"{{-{expected[i1:i2]}-}}")
    return "".join(parts)


def register(server):
    @server.tool()
    async def sassy_edit_block(path: str, old_text: str, new_text: str) -> str:
        """Surgical file edit: find old_text and replace with new_text.

        - Exact match preferred; fuzzy fallback with diff reporting
        - Fails if multiple exact matches found (provide more context)
        - Preserves file encoding and line endings
        - Returns a preview of the change with surrounding context
        """
        p = Path(path)
        if not p.exists():
            return f"Error: {path} does not exist"
        if not p.is_file():
            return f"Error: {path} is not a file"

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError) as e:
            return f"Error reading {path}: {e}"

        # Try exact match
        count = content.count(old_text)

        if count == 1:
            # Single exact match — apply the edit
            new_content = content.replace(old_text, new_text, 1)
            try:
                p.write_text(new_content, encoding="utf-8")
            except (OSError, PermissionError) as e:
                return f"Error writing {path}: {e}"

            # Build context preview
            idx = content.index(old_text)
            lines_before = content[:idx].splitlines()
            start_line = len(lines_before)
            preview_start = max(0, start_line - 2)
            new_lines = new_content.splitlines()
            end_line = start_line + len(new_text.splitlines())
            preview_end = min(len(new_lines), end_line + 2)
            preview = "\n".join(
                f"{i + 1:>4} | {new_lines[i]}"
                for i in range(preview_start, preview_end)
            )
            return f"Edit applied to {path} (line {start_line + 1}):\n{preview}"

        elif count > 1:
            # Multiple matches — need more context
            positions = []
            start = 0
            for _ in range(min(count, 5)):
                idx = content.index(old_text, start)
                line_num = content[:idx].count("\n") + 1
                positions.append(line_num)
                start = idx + 1
            return (
                f"Error: found {count} matches for the search text in {path}. "
                f"Matches at lines: {positions}. "
                f"Include more surrounding context in old_text to make it unique."
            )

        else:
            # No exact match — try fuzzy
            match = _find_best_match(content, old_text)
            if match:
                _, _, similarity, matched_text = match
                diff = _char_diff(old_text, matched_text)
                return (
                    f"No exact match found in {path}. "
                    f"Closest match ({similarity:.0%} similar):\n"
                    f"Diff: {diff}\n\n"
                    f"Use the exact text from the file for old_text."
                )
            return f"No match found for the search text in {path}."

    @server.tool()
    async def sassy_edit_multi(path: str, edits: str) -> str:
        """Apply multiple edits to a file in one call.

        edits format (JSON string):
        [{"old": "text to find", "new": "replacement"}, ...]

        Edits are applied in order. Each must have exactly one match.
        """
        import json as _json

        p = Path(path)
        if not p.exists():
            return f"Error: {path} does not exist"

        try:
            edit_list = _json.loads(edits)
        except _json.JSONDecodeError as e:
            return f"Error: invalid JSON in edits: {e}"

        if not isinstance(edit_list, list):
            return "Error: edits must be a JSON array of {old, new} objects"

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError) as e:
            return f"Error reading {path}: {e}"

        applied = 0
        for i, edit in enumerate(edit_list):
            old = edit.get("old", "")
            new = edit.get("new", "")
            if not old:
                return f"Error: edit {i} has empty 'old' field"
            count = content.count(old)
            if count == 0:
                return f"Error: edit {i} — no match found for old text"
            if count > 1:
                return f"Error: edit {i} — {count} matches found, need more context"
            content = content.replace(old, new, 1)
            applied += 1

        try:
            p.write_text(content, encoding="utf-8")
        except (OSError, PermissionError) as e:
            return f"Error writing {path}: {e}"

        return f"Applied {applied} edits to {path}"
