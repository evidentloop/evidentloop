#!/usr/bin/env python3
"""Check repository, distribution, and installed-Skill release boundaries."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath


EXPECTED_SKILL_FILES = {
    "SKILL.md",
    "agents/openai.yaml",
    "references/codex-cli-isolation.md",
}
FORBIDDEN_TRACKED_PREFIXES = (".sopify/state/", ".sopify/user/")
FORBIDDEN_FILENAMES = {
    ".env",
    "id_ed25519",
    "id_rsa",
    "raw-analysis.md",
}
FORBIDDEN_SUFFIXES = (".key", ".pem")
SENSITIVE_TEXT_PATTERNS = {
    "private key material": re.compile(
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"
    ),
    "macOS home path": re.compile(r"/" + r"Users/[^/\s]+/"),
    "Linux home path": re.compile(r"/" + r"home/[^/\s]+/"),
    "Windows home path": re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--dist-dir", type=Path, required=True)
    parser.add_argument("--skill-dir", type=Path, required=True)
    return parser.parse_args()


def _tracked_files(repository: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    return [path.decode("utf-8") for path in result.stdout.split(b"\0") if path]


def _forbidden_filename(path: PurePosixPath) -> bool:
    name = path.name.lower()
    return (
        name in FORBIDDEN_FILENAMES
        or (
            name.startswith(".env.")
            and name not in {".env.example", ".env.sample", ".env.template"}
        )
        or name.endswith(FORBIDDEN_SUFFIXES)
    )


def _check_repository(repository: Path) -> list[str]:
    violations: list[str] = []
    for relative_path in _tracked_files(repository):
        normalized = PurePosixPath(relative_path)
        if relative_path.startswith(FORBIDDEN_TRACKED_PREFIXES):
            violations.append(f"tracked runtime/user state: {relative_path}")
            continue
        if _forbidden_filename(normalized):
            violations.append(f"tracked sensitive artifact: {relative_path}")
            continue

        path = repository / relative_path
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for label, pattern in SENSITIVE_TEXT_PATTERNS.items():
            if pattern.search(text):
                violations.append(f"{label}: {relative_path}")
    return violations


def _safe_archive_path(name: str) -> bool:
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts


def _check_archive(path: Path, names: list[str]) -> list[str]:
    violations: list[str] = []
    for name in names:
        member = PurePosixPath(name)
        if not _safe_archive_path(name):
            violations.append(f"unsafe archive member in {path.name}: {name}")
        if ".sopify" in member.parts:
            violations.append(f".sopify leaked into {path.name}: {name}")
        if _forbidden_filename(member):
            violations.append(f"sensitive artifact in {path.name}: {name}")
    return violations


def _check_archive_content(path: Path, name: str, content: bytes) -> list[str]:
    text = content.decode("utf-8", errors="ignore")
    return [
        f"{label} in {path.name}: {name}"
        for label, pattern in SENSITIVE_TEXT_PATTERNS.items()
        if pattern.search(text)
    ]


def _check_distributions(dist_dir: Path) -> list[str]:
    wheels = sorted(dist_dir.glob("*.whl"))
    sdists = sorted(dist_dir.glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        return [
            "dist directory must contain exactly one wheel and one .tar.gz sdist"
        ]

    wheel = wheels[0]
    with zipfile.ZipFile(wheel) as archive:
        wheel_names = archive.namelist()
        violations = _check_archive(wheel, wheel_names)
        for name in wheel_names:
            if not name.endswith("/"):
                violations.extend(_check_archive_content(wheel, name, archive.read(name)))
    wheel_roots = {PurePosixPath(name).parts[0] for name in wheel_names if name}
    if "evidentloop" not in wheel_roots or not any(
        root.startswith("evidentloop-") and root.endswith(".dist-info")
        for root in wheel_roots
    ):
        violations.append(f"unexpected wheel roots: {sorted(wheel_roots)}")
    if any(root == "skills" or root.startswith(".sopify") for root in wheel_roots):
        violations.append(f"non-runtime content in wheel: {sorted(wheel_roots)}")

    sdist = sdists[0]
    with tarfile.open(sdist, mode="r:gz") as archive:
        sdist_names = archive.getnames()
        violations.extend(_check_archive(sdist, sdist_names))
        for member in archive.getmembers():
            if member.isfile():
                stream = archive.extractfile(member)
                if stream is not None:
                    violations.extend(
                        _check_archive_content(sdist, member.name, stream.read())
                    )
    sdist_roots = {PurePosixPath(name).parts[0] for name in sdist_names if name}
    if len(sdist_roots) != 1 or not next(iter(sdist_roots), "").startswith(
        "evidentloop-"
    ):
        violations.append(f"unexpected sdist roots: {sorted(sdist_roots)}")
    return violations


def _check_skill(skill_dir: Path) -> list[str]:
    actual_files = {
        path.relative_to(skill_dir).as_posix()
        for path in skill_dir.rglob("*")
        if path.is_file()
    }
    violations: list[str] = []
    if actual_files != EXPECTED_SKILL_FILES:
        violations.append(
            "installed Skill manifest mismatch: "
            f"expected {sorted(EXPECTED_SKILL_FILES)}, got {sorted(actual_files)}"
        )
    for relative_path in sorted(actual_files):
        path = PurePosixPath(relative_path)
        if ".sopify" in path.parts or _forbidden_filename(path):
            violations.append(f"forbidden installed Skill file: {relative_path}")
    return violations


def main() -> int:
    args = _parse_args()
    repository = args.repository.resolve()
    violations = [
        *_check_repository(repository),
        *_check_distributions(args.dist_dir.resolve()),
        *_check_skill(args.skill_dir.resolve()),
    ]
    if violations:
        print("release boundary check failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1
    print("release boundaries: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
