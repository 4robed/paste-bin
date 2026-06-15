#!/usr/bin/env python3
"""
pastebin-cli – post code snippets to your Pastebin instance from the terminal.

Usage:
    pastebin-cli post <file>               Post a file
    pastebin-cli post -                    Post from stdin
    pastebin-cli post <file> -p <pass>     Post with password
    pastebin-cli post <file> -e 1d         Post with 1-day expiry
    pastebin-cli get <short-code>          Print paste content
    pastebin-cli info <short-code>         Show paste metadata

Environment variables:
    PASTEBIN_URL    Base URL of your pastebin (default: http://localhost:8000)
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse

BASE_URL = os.environ.get("PASTEBIN_URL", "http://localhost:8000").rstrip("/")

LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".go": "go",
    ".rs": "rust",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".html": "html",
    ".css": "css",
    ".json": "json",
    ".sh": "bash",
    ".bash": "bash",
    ".sql": "sql",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".rb": "ruby",
    ".php": "php",
}


def detect_language(filename: str) -> str:
    if not filename or filename == "-":
        return "plaintext"
    ext = os.path.splitext(filename)[1].lower()
    return LANGUAGE_MAP.get(ext, "plaintext")


def api_post(payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{BASE_URL}/api/pastes",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to {BASE_URL}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def api_get(code: str) -> dict:
    req = urllib.request.Request(f"{BASE_URL}/api/pastes/{code}", method="GET")
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"Paste '{code}' not found or has expired.", file=sys.stderr)
        elif e.code == 403:
            print(f"Paste '{code}' is password-protected (use the web UI to unlock).", file=sys.stderr)
        else:
            print(f"Error {e.code}: {e.read().decode()}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Cannot connect to {BASE_URL}: {e.reason}", file=sys.stderr)
        sys.exit(1)


def cmd_post(args):
    if args.file == "-":
        content = sys.stdin.read()
        language = args.language or "plaintext"
        filename = "-"
    else:
        if not os.path.isfile(args.file):
            print(f"File not found: {args.file}", file=sys.stderr)
            sys.exit(1)
        with open(args.file, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
        filename = args.file
        language = args.language or detect_language(filename)

    if not content.strip():
        print("Error: file is empty.", file=sys.stderr)
        sys.exit(1)

    payload = {
        "content": content,
        "language": language,
        "expiry": args.expiry or "never",
    }
    if args.title:
        payload["title"] = args.title
    if args.password:
        payload["password"] = args.password

    result = api_post(payload)
    print(result["url"])
    if args.verbose:
        print(f"  code:     {result['short_code']}")
        print(f"  language: {result['language']}")
        print(f"  expires:  {result.get('expires_at') or 'never'}")
        print(f"  protected:{result['is_protected']}")


def cmd_get(args):
    data = api_get(args.code)
    print(data["content"], end="")


def cmd_info(args):
    data = api_get(args.code)
    print(f"Short code : {data['short_code']}")
    print(f"Title      : {data.get('title') or '(untitled)'}")
    print(f"Language   : {data['language']}")
    print(f"Views      : {data['views']}")
    print(f"Created    : {data['created_at']}")
    print(f"Expires    : {data.get('expires_at') or 'never'}")
    print(f"Protected  : {data['is_protected']}")
    print(f"URL        : {BASE_URL}/{data['short_code']}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pastebin-cli",
        description="Post and retrieve pastes from your Pastebin instance.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    post_p = sub.add_parser("post", help="Create a new paste")
    post_p.add_argument("file", help="File to post, or '-' for stdin")
    post_p.add_argument("-t", "--title", help="Paste title")
    post_p.add_argument("-l", "--language", help="Language (auto-detected from extension if omitted)")
    post_p.add_argument("-p", "--password", help="Password-protect the paste")
    post_p.add_argument("-e", "--expiry", choices=["never", "1h", "1d", "7d", "30d"], default="never", help="Expiry window")
    post_p.add_argument("-v", "--verbose", action="store_true", help="Print extra metadata")
    post_p.set_defaults(func=cmd_post)

    get_p = sub.add_parser("get", help="Print paste content to stdout")
    get_p.add_argument("code", help="Short code of the paste")
    get_p.set_defaults(func=cmd_get)

    info_p = sub.add_parser("info", help="Show paste metadata")
    info_p.add_argument("code", help="Short code of the paste")
    info_p.set_defaults(func=cmd_info)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
