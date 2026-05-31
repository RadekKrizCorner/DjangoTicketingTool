"""Validate local commit and GitHub merge request metadata."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TICKET_RE = re.compile(r"\b(PROJECT-\d+|HOTFIX-[A-Za-z0-9][A-Za-z0-9-]*)\b")
MESSAGE_MODE = "message"
PULL_REQUEST_TARGET_MODE = "pull-request-target"


def contains_allowed_ticket(value: str) -> bool:
    """Return whether text contains a valid project or hotfix token."""
    return bool(TICKET_RE.search(value or ""))


def is_allowed_pull_request_target(*, base_ref: str, head_ref: str) -> bool:
    """Return whether a pull request target branch is allowed."""
    if base_ref == "release":
        return True
    if base_ref == "master":
        return head_ref == "release" or head_ref.startswith("hotfix/")
    return False


def read_message(path: Path | None, value: str | None) -> str:
    """Read a message from a direct value or a commit message file."""
    if value is not None:
        return value
    if path is None:
        return ""
    return path.read_text(encoding="utf-8")


def first_line(value: str) -> str:
    """Return the first line from text."""
    lines = value.splitlines()
    if not lines:
        return ""
    return lines[0]


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("message_file", nargs="?", type=Path)
    parser.add_argument("--value")
    parser.add_argument("--kind", default="commit")
    parser.add_argument(
        "--mode",
        choices=(MESSAGE_MODE, PULL_REQUEST_TARGET_MODE),
        default=MESSAGE_MODE,
    )
    parser.add_argument("--base-ref", default="")
    parser.add_argument("--head-ref", default="")
    return parser.parse_args(argv)


def validate_message(*, message: str, kind: str) -> int:
    """Validate a commit or merge request title."""
    title = first_line(message)
    if contains_allowed_ticket(title):
        return 0
    print(f"{kind} title must contain PROJECT-NNN or HOTFIX-text.", file=sys.stderr)
    return 1


def validate_pull_request_target(*, base_ref: str, head_ref: str) -> int:
    """Validate allowed pull request target branches."""
    if is_allowed_pull_request_target(base_ref=base_ref, head_ref=head_ref):
        return 0
    print(
        "New work must target release. Master accepts only release or hotfix/* merge requests.",
        file=sys.stderr,
    )
    return 1


def main(argv: list[str] | None = None) -> int:
    """Validate supplied Git metadata."""
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.mode == PULL_REQUEST_TARGET_MODE:
        return validate_pull_request_target(base_ref=args.base_ref, head_ref=args.head_ref)
    message = read_message(args.message_file, args.value)
    return validate_message(message=message, kind=args.kind)


if __name__ == "__main__":
    raise SystemExit(main())
