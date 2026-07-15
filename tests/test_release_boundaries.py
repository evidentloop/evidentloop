from pathlib import Path

from scripts.check_release_boundaries import _check_archive_content


def test_archive_content_scan_rejects_sensitive_text() -> None:
    violations = _check_archive_content(
        Path("evidentloop.whl"),
        "generated.txt",
        b"source=/"
        + b"Users/example/project\n-----BEGIN "
        + b"PRIVATE KEY-----\n",
    )

    assert violations == [
        "private key material in evidentloop.whl: generated.txt",
        "macOS home path in evidentloop.whl: generated.txt",
    ]
