#!/usr/bin/env python3
"""Semantic version and build metadata helper for CI workflows.

Conventions:
- Primary version source: package.json `version` when present and valid.
- Fallback version source: root `VERSION` file.
- Required version format: MAJOR.MINOR.PATCH
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
BUMP_PRIORITY = {"patch": 0, "minor": 1, "major": 2}


class VersionError(RuntimeError):
    """Raised when version source is missing or invalid."""


@dataclass(frozen=True)
class VersionSource:
    source: str
    path: Path
    version: str


def require_semver(value: str) -> str:
    cleaned = value.strip()
    if not SEMVER_RE.fullmatch(cleaned):
        raise VersionError(
            f"Invalid semantic version '{cleaned}'. Expected MAJOR.MINOR.PATCH."
        )
    return cleaned


def detect_version_source(repo_root: Path) -> VersionSource:
    package_path = repo_root / "package.json"
    if package_path.exists():
        try:
            package_data = json.loads(package_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise VersionError(f"Failed to parse package.json: {exc}") from exc

        package_version = str(package_data.get("version", "")).strip()
        if package_version:
            return VersionSource(
                source="package.json",
                path=package_path,
                version=require_semver(package_version),
            )

    version_path = repo_root / "VERSION"
    if version_path.exists():
        version_value = version_path.read_text(encoding="utf-8").strip()
        return VersionSource(
            source="VERSION",
            path=version_path,
            version=require_semver(version_value),
        )

    raise VersionError(
        "No canonical version source found. Add package.json version or VERSION file."
    )


def bump_semver(version: str, level: str) -> str:
    major, minor, patch = [int(part) for part in version.split(".")]
    if level == "major":
        major += 1
        minor = 0
        patch = 0
    elif level == "minor":
        minor += 1
        patch = 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def max_bump(current: str, candidate: str) -> str:
    if BUMP_PRIORITY[candidate] > BUMP_PRIORITY[current]:
        return candidate
    return current


def write_version(source: VersionSource, new_version: str) -> None:
    if source.source == "package.json":
        package_data = json.loads(source.path.read_text(encoding="utf-8"))
        package_data["version"] = new_version
        source.path.write_text(
            json.dumps(package_data, indent=2, ensure_ascii=True) + "\n",
            encoding="utf-8",
        )
        return

    source.path.write_text(f"{new_version}\n", encoding="utf-8")


def git_sha() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"], text=True)
            .strip()
            .lower()
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return os.environ.get("GITHUB_SHA", "unknown").strip().lower() or "unknown"


def utc_timestamp() -> str:
    return (
        dt.datetime.now(dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def git_log_messages(repo_root: Path, commit_range: str) -> list[str]:
    try:
        output = subprocess.check_output(
            [
                "git",
                "-C",
                str(repo_root),
                "log",
                "--format=%s%n%b%n---COMMIT-END---",
                commit_range,
            ],
            text=True,
        )
    except subprocess.SubprocessError as exc:
        raise VersionError(f"Failed reading git history for range '{commit_range}'") from exc

    raw_entries = output.split("---COMMIT-END---")
    return [entry.strip() for entry in raw_entries if entry.strip()]


def resolve_bump_level(repo_root: Path, commit_range: str, default_level: str) -> tuple[str, str]:
    entries = git_log_messages(repo_root, commit_range)
    if not entries:
        return default_level, f"no_commits_detected(default={default_level})"

    level = default_level
    reasons: list[str] = []

    for entry in entries:
        lines = entry.splitlines()
        subject = lines[0].strip() if lines else ""

        semver_overrides = re.findall(r"(?im)^semver:\s*(major|minor|patch)\s*$", entry)
        for override in semver_overrides:
            level = max_bump(level, override.lower())
            reasons.append(f"semver_trailer:{override.lower()}")

        if re.search(r"(?im)^breaking change:\s", entry):
            level = max_bump(level, "major")
            reasons.append("breaking_change")

        if re.match(r"(?i)^[a-z]+(?:\([^)]+\))?!:", subject):
            level = max_bump(level, "major")
            reasons.append("conventional_bang")

        if re.match(r"(?i)^feat(?:\([^)]+\))?:", subject):
            level = max_bump(level, "minor")
            reasons.append("feat")

    if not reasons:
        reasons.append(f"default:{default_level}")

    reason = ",".join(sorted(set(reasons)))
    return level, reason


def emit_env(data: dict[str, str]) -> None:
    for key, value in data.items():
        print(f"{key}={value}")


def cmd_current(repo_root: Path) -> int:
    source = detect_version_source(repo_root)
    print(source.version)
    return 0


def cmd_bump(repo_root: Path, level: str, write: bool) -> int:
    source = detect_version_source(repo_root)
    new_version = bump_semver(source.version, level)
    if write:
        write_version(source, new_version)

    output = {
        "version_source": source.source,
        "version_source_path": source.path.relative_to(repo_root).as_posix(),
        "current_version": source.version,
        "new_version": new_version,
        "tag": f"v{new_version}",
    }
    emit_env(output)
    return 0


def cmd_metadata(repo_root: Path, version_override: str | None) -> int:
    source = detect_version_source(repo_root)
    version = require_semver(version_override) if version_override else source.version
    full_sha = git_sha()
    short_sha = full_sha[:7] if len(full_sha) >= 7 else full_sha
    output = {
        "app_version": version,
        "app_git_sha": full_sha,
        "app_git_sha_short": short_sha,
        "app_build_date": utc_timestamp(),
    }
    emit_env(output)
    return 0


def cmd_resolve_bump(repo_root: Path, commit_range: str, default_level: str) -> int:
    if default_level not in BUMP_PRIORITY:
        raise VersionError(
            f"Invalid default bump level '{default_level}'. Use patch|minor|major."
        )
    level, reason = resolve_bump_level(repo_root, commit_range, default_level)
    output = {
        "bump_level": level,
        "bump_reason": reason,
        "bump_range": commit_range,
    }
    emit_env(output)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repository root containing package.json or VERSION (default: .)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("current", help="Print current semantic version")

    bump = subparsers.add_parser("bump", help="Bump semantic version")
    bump.add_argument(
        "--level",
        choices=["patch", "minor", "major"],
        default="patch",
        help="Semantic version bump level (default: patch)",
    )
    bump.add_argument(
        "--write",
        action="store_true",
        help="Write the bumped version back to package.json or VERSION",
    )

    metadata = subparsers.add_parser(
        "metadata", help="Emit build metadata env values for CI"
    )
    metadata.add_argument(
        "--version",
        default=None,
        help="Override app version (must be MAJOR.MINOR.PATCH)",
    )

    resolve_bump = subparsers.add_parser(
        "resolve-bump",
        help="Resolve semantic bump level from commit messages",
    )
    resolve_bump.add_argument(
        "--range",
        default="HEAD",
        help="Git commit range to inspect (for example <before>..<after>)",
    )
    resolve_bump.add_argument(
        "--default-level",
        choices=["patch", "minor", "major"],
        default="patch",
        help="Fallback level when no commit signal is found",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()

    try:
        if args.command == "current":
            return cmd_current(repo_root)
        if args.command == "bump":
            return cmd_bump(repo_root, args.level, args.write)
        if args.command == "metadata":
            return cmd_metadata(repo_root, args.version)
        if args.command == "resolve-bump":
            return cmd_resolve_bump(repo_root, args.range, args.default_level)
        raise VersionError(f"Unsupported command: {args.command}")
    except VersionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
