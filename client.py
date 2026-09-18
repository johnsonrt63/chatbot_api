import argparse
import json
import os
import sys
from typing import Any, Dict, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = os.getenv("CHATBOT_API_BASE_URL", "http://127.0.0.1:8000")


def send_request(base_url: str, api_key: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    url = f"{base_url.rstrip('/')}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json", "X-API-Key": api_key}
    if data is not None:
        headers["Content-Type"] = "application/json"

    request = Request(url=url, data=data, headers=headers, method="POST" if data is not None else "GET")
    try:
        with urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code}: {body}") from exc
    except URLError as exc:
        raise SystemExit(f"Request failed: {exc}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CLI client for the chatbot API")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="Base URL of the chatbot service")
    parser.add_argument(
        "--api-key",
        default=os.getenv("SERVICE_API_KEY", ""),
        help="API key for X-API-Key header (defaults to SERVICE_API_KEY env var)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    open_parser = subparsers.add_parser("open-session", help="Open a session")
    open_parser.add_argument("session_id")

    chat_parser = subparsers.add_parser("chat", help="Send a chat message")
    chat_parser.add_argument("session_id")
    chat_parser.add_argument("message")

    close_parser = subparsers.add_parser("close-session", help="Close a session")
    close_parser.add_argument("session_id")

    subparsers.add_parser("health", help="Check service health")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.api_key and args.command != "health":
        raise SystemExit("An API key is required. Provide --api-key or set SERVICE_API_KEY.")

    if args.command == "open-session":
        response = send_request(args.base_url, args.api_key, "/open-session", {"session_id": args.session_id})
    elif args.command == "chat":
        response = send_request(
            args.base_url,
            args.api_key,
            "/chat",
            {"session_id": args.session_id, "message": args.message},
        )
    elif args.command == "close-session":
        response = send_request(args.base_url, args.api_key, "/close-session", {"session_id": args.session_id})
    elif args.command == "health":
        response = send_request(args.base_url, args.api_key, "/health", None)
    else:
        raise SystemExit(f"Unsupported command: {args.command}")

    json.dump(response, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
