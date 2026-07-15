#!/usr/bin/env python3
"""Build and verify one EvidentLoop GitHub Release evidence archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import tomllib
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from evidentloop.renderers.html import validate_html_trace  # noqa: E402
from evidentloop.validation import assert_valid_audit  # noqa: E402


REPOSITORY_URL = "https://github.com/evidentloop/evidentloop"
EXPECTED_FILES = {
    "audit.html",
    "audit.json",
    "checksums.sha256",
    "manifest.json",
    "test-summary.json",
}
CHECKSUMMED_FILES = (
    "audit.html",
    "audit.json",
    "manifest.json",
    "test-summary.json",
)
SENSITIVE_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"/" + r"Users/[^/\s]+/"),
    re.compile(r"/" + r"home/[^/\s]+/"),
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+\\"),
)
SANITIZATION_CHECKS = (
    "private-key-header",
    "macos-user-home-path",
    "linux-user-home-path",
    "windows-user-home-path",
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit-dir", type=Path, required=True)
    parser.add_argument("--test-summary", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--release-tag", required=True)
    parser.add_argument("--out", type=Path, required=True)
    return parser.parse_args()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain one JSON object")
    return value


def _assert_sanitized(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if any(pattern.search(text) for pattern in SENSITIVE_PATTERNS):
        raise ValueError(f"sensitive local content remains in {path.name}")


def _resolve_commit(repository: Path, source_commit: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        raise ValueError("source commit must be a full lowercase Git SHA")
    result = subprocess.run(
        ["git", "rev-parse", f"{source_commit}^{{commit}}"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    resolved = result.stdout.strip()
    if resolved != source_commit:
        raise ValueError("source commit did not resolve exactly")
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != source_commit:
        raise ValueError("source commit must equal the repository HEAD")
    for command in (
        ["git", "diff", "--quiet"],
        ["git", "diff", "--cached", "--quiet"],
    ):
        result = subprocess.run(command, cwd=repository, check=False)
        if result.returncode != 0:
            raise ValueError("tracked working tree must be clean")
    return resolved


def _validate_evidence_provenance(
    audit: dict[str, object],
    *,
    source_commit: str,
    release_tag: str,
    package_version: str,
) -> str:
    expected_tag = f"v{package_version}"
    if release_tag != expected_tag:
        raise ValueError(f"release tag must equal {expected_tag}")

    source = audit.get("source")
    if not isinstance(source, dict):
        raise ValueError("audit source must be an object")
    source_ref = source.get("ref")
    if not isinstance(source_ref, str) or not (
        source_ref == source_commit or source_ref.endswith(f"..{source_commit}")
    ):
        raise ValueError("audit source ref must end at the full source commit")

    source_extensions = source.get("extensions", {})
    if not isinstance(source_extensions, dict):
        raise ValueError("audit source extensions must be an object")
    provenance = source_extensions.get("evidentloop", {})
    if not isinstance(provenance, dict):
        raise ValueError("audit source provenance must be an object")
    if (
        provenance.get("execution_mode") == "demo_replay"
        or provenance.get("reviewer") == "frozen_replay"
        or provenance.get("live_ai_review") is False
    ):
        raise ValueError("demo or frozen replay cannot be release evidence")
    return source_ref


def _write_manifest(
    root: Path,
    *,
    source_commit: str,
    source_ref: str,
    release_tag: str,
    package_version: str,
    audit: dict[str, object],
) -> None:
    summary = audit["summary"]
    extensions = audit["extensions"]
    evidentloop_extension = extensions["evidentloop"]  # type: ignore[index]
    reviewer_prompt = evidentloop_extension["reviewer_prompt"]  # type: ignore[index]
    manifest = {
        "product": "EvidentLoop",
        "repository": REPOSITORY_URL,
        "release_tag": release_tag,
        "source_commit": source_commit,
        "package_version": package_version,
        "schema_version": audit["schema_version"],
        "prompt_version": reviewer_prompt["version"],  # type: ignore[index]
        "audit": {
            "source_ref": source_ref,
            "run_id": evidentloop_extension["run_id"],  # type: ignore[index]
            "review_status": summary["review_status"],  # type: ignore[index]
            "verdict": summary["verdict"],  # type: ignore[index]
        },
        "sanitization": {
            "result": "passed",
            "checks": list(SANITIZATION_CHECKS),
        },
        "files": {
            name: {"sha256": _sha256(root / name)}
            for name in ("audit.json", "audit.html", "test-summary.json")
        },
    }
    (root / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _write_checksums(root: Path) -> None:
    content = "".join(
        f"{_sha256(root / name)}  {name}\n" for name in CHECKSUMMED_FILES
    )
    (root / "checksums.sha256").write_text(content, encoding="utf-8")


def _normalize_tar_info(info: tarfile.TarInfo) -> tarfile.TarInfo:
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    info.mtime = 0
    return info


def _verify_archive(path: Path, root_name: str) -> None:
    with tarfile.open(path, mode="r:gz") as archive:
        files = {
            member.name.removeprefix(f"{root_name}/"): member
            for member in archive.getmembers()
            if member.isfile()
        }
        if set(files) != EXPECTED_FILES:
            raise ValueError(f"release archive manifest mismatch: {sorted(files)}")
        checksum_text = archive.extractfile(files["checksums.sha256"]).read().decode()  # type: ignore[union-attr]
        expected = {
            line.split("  ", 1)[1]: line.split("  ", 1)[0]
            for line in checksum_text.splitlines()
        }
        if set(expected) != set(CHECKSUMMED_FILES):
            raise ValueError("checksum manifest mismatch")
        for name, digest in expected.items():
            content = archive.extractfile(files[name]).read()  # type: ignore[union-attr]
            if hashlib.sha256(content).hexdigest() != digest:
                raise ValueError(f"checksum mismatch for {name}")


def main() -> int:
    args = _parse_args()
    repository = REPOSITORY_ROOT
    audit_dir = args.audit_dir.resolve()
    output = args.out.resolve()
    if output.exists():
        raise FileExistsError(f"output already exists: {output}")
    if not output.name.endswith(".tar.gz"):
        raise ValueError("output must end with .tar.gz")

    project = tomllib.loads((repository / "pyproject.toml").read_text(encoding="utf-8"))
    version = str(project["project"]["version"])
    source_commit = _resolve_commit(repository, args.source_commit)
    audit_path = audit_dir / "audit.json"
    html_path = audit_dir / "audit.html"
    audit = _read_json_object(audit_path)
    test_summary = _read_json_object(args.test_summary.resolve())
    if test_summary.get("result") != "passed":
        raise ValueError("test summary result must be passed")
    assert_valid_audit(audit)
    source_ref = _validate_evidence_provenance(
        audit,
        source_commit=source_commit,
        release_tag=args.release_tag,
        package_version=version,
    )
    html = html_path.read_text(encoding="utf-8")
    trace_errors = validate_html_trace(html, audit)
    if trace_errors:
        raise ValueError("audit HTML trace validation failed: " + "; ".join(trace_errors))
    _assert_sanitized(audit_path)
    _assert_sanitized(html_path)
    _assert_sanitized(args.test_summary.resolve())

    root_name = f"evidentloop-evidence-{version}"
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="evidentloop-evidence-") as temporary:
        root = Path(temporary) / root_name
        root.mkdir()
        shutil.copyfile(audit_path, root / "audit.json")
        shutil.copyfile(html_path, root / "audit.html")
        shutil.copyfile(args.test_summary.resolve(), root / "test-summary.json")
        _write_manifest(
            root,
            source_commit=source_commit,
            source_ref=source_ref,
            release_tag=args.release_tag,
            package_version=version,
            audit=audit,
        )
        _write_checksums(root)
        with tarfile.open(output, mode="w:gz") as archive:
            archive.add(root, arcname=root_name, filter=_normalize_tar_info)
    _verify_archive(output, root_name)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
