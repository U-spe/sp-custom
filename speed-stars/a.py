
#!/usr/bin/env python3

"""
Speed Stars path rewriter

Rewrites local repository paths to use:
    /speed-stars/thefile-or-folder

Examples:
    Build/game.data       -> /speed-stars/Build/game.data
    files/scripts/app.js  -> /speed-stars/files/scripts/app.js
    content-style.css     -> /speed-stars/content-style.css

Run from the repository root:
    python3 rewrite.py
"""

from pathlib import Path
import re
import shutil
import sys


# ============================================================
# CONFIGURATION
# ============================================================

ROOT = Path(__file__).resolve().parent
URL_PREFIX = "/speed-stars"

BACKUP_ROOT = ROOT.parent / "speed-stars-backup"

TEXT_EXTENSIONS = {
    ".html",
    ".htm",
    ".css",
    ".js",
    ".mjs",
    ".cjs",
    ".json",
    ".xml",
    ".svg",
    ".txt",
    ".webmanifest",
    ".map",
}

SKIP_DIRECTORIES = {
    ".git",
    "node_modules",
    ".vercel",
    "speed-stars-backup",
}

# These are third-party references and must remain unchanged.
EXTERNAL_SCHEMES = (
    "http://",
    "https://",
    "data:",
    "blob:",
    "javascript:",
    "mailto:",
    "tel:",
)


# ============================================================
# BUILD PATH MATCHER FROM THE ACTUAL REPOSITORY
# ============================================================

def get_root_entries():
    """Get actual files and directories located at the repository root."""

    entries = []

    for item in ROOT.iterdir():
        if item.name == Path(__file__).name:
            continue

        if item.name in SKIP_DIRECTORIES:
            continue

        if item.is_file() or item.is_dir():
            entries.append(item.name)

    # Match longer names first to avoid partial matches.
    return sorted(entries, key=len, reverse=True)


def build_path_pattern():
    entries = get_root_entries()

    if not entries:
        raise RuntimeError("No repository files or directories found.")

    alternatives = "|".join(
        re.escape(name) for name in entries
    )

    # Match:
    # Build/example.data
    # files/scripts/poki/sdk.js
    # content-style.css
    #
    # Do not match URLs already starting with / or a URL scheme.
    return re.compile(
        r"(?<![A-Za-z0-9:/])"
        r"(?P<path>(?:\./)?(?:"
        + alternatives
        + r")(?:/[A-Za-z0-9._~!$&()*+,;=@%-]+)*)"
        r"(?=$|[\s\"'`<>),;?#!\]])"
    )


PATH_PATTERN = build_path_pattern()


# ============================================================
# PATH REWRITING
# ============================================================

def rewrite_path(match):
    original = match.group("path")

    # Remove a leading ./ because the result is root-relative.
    normalized = original

    if normalized.startswith("./"):
        normalized = normalized[2:]

    # Do not double-prefix an already rewritten path.
    if normalized.startswith(URL_PREFIX + "/"):
        return original

    return URL_PREFIX + "/" + normalized


def rewrite_content(content):
    """Rewrite recognized local paths without changing external URLs."""

    return PATH_PATTERN.sub(rewrite_path, content)


# ============================================================
# FILE PROCESSING
# ============================================================

def should_skip(path):
    if not path.is_file():
        return True

    if path.suffix.lower() not in TEXT_EXTENSIONS:
        return True

    if path.name == Path(__file__).name:
        return True

    if any(part in SKIP_DIRECTORIES for part in path.parts):
        return True

    return False


def save_backup(path):
    """Back up the original file while preserving its directory structure."""

    relative = path.relative_to(ROOT)
    backup_path = BACKUP_ROOT / relative

    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup_path)


def process_file(path):
    try:
        original = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        print(f"[SKIP] Could not read as UTF-8: {path.relative_to(ROOT)}")
        return False

    updated = rewrite_content(original)

    if updated == original:
        return False

    save_backup(path)
    path.write_text(updated, encoding="utf-8")

    print(f"[UPDATED] {path.relative_to(ROOT)}")
    return True


def main():
    if not ROOT.is_dir():
        print("[ERROR] Repository directory not found.")
        sys.exit(1)

    if not (ROOT / "index.html").is_file():
        print("[ERROR] index.html not found.")
        print("Place rewrite.py in the Speed Stars repository root.")
        sys.exit(1)

    print("=" * 60)
    print("SPEED STARS PATH REWRITER")
    print("=" * 60)
    print(f"Repository: {ROOT}")
    print(f"URL prefix: {URL_PREFIX}/")
    print(f"Backup:     {BACKUP_ROOT}")
    print()

    files = []

    for path in ROOT.rglob("*"):
        if should_skip(path):
            continue

        files.append(path)

    changed = 0

    for path in sorted(files):
        if process_file(path):
            changed += 1

    print()
    print("=" * 60)
    print("REWRITE COMPLETE")
    print("=" * 60)
    print(f"Files scanned:  {len(files)}")
    print(f"Files changed:  {changed}")

    if changed:
        print(f"Backups saved:  {BACKUP_ROOT}")
    else:
        print("No matching relative paths needed rewriting.")

    print()
    print("Unity binary assets were not modified.")
    print("External URLs and Poki SDK references were preserved.")
    print()
    print("IMPORTANT:")
    print("Review the resulting paths before deploying.")
    print("The site must be hosted with /speed-stars/ mapped")
    print("to this game's repository root.")


if __name__ == "__main__":
    main()
