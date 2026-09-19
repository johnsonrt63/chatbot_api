import argparse
import os
import sys

import requests


def build_headers(api_key: str) -> dict:
    return {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }


def send_chat(base_url: str, api_key: str, session_id: str, message: str) -> int:
    response = requests.post(
        f"{base_url.rstrip('/')}/chat",
        headers=build_headers(api_key),
        json={"message": message, "session_id": session_id},
        timeout=30,
    )
    try:
        payload = response.json()
    except ValueError:
        print(response.text)
        return 1

    if response.ok:
        print(payload.get("reply", ""))
        return 0

    print(payload)
    return 1


def check_health(base_url: str) -> int:
    response = requests.get(f"{base_url.rstrip('/')}/health", timeout=10)
    print(response.text)
    return 0 if response.ok else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CLI client for the chatbot API")
    parser.add_argument("--base-url", default=os.getenv("CHATBOT_API_URL", "http://127.0.0.1:8000"))

    subparsers = parser.add_subparsers(dest="command", required=True)

    chat_parser = subparsers.add_parser("chat", help="Send a chat message")
    chat_parser.add_argument("--api-key", default=os.getenv("SERVICE_API_KEY"), required=os.getenv("SERVICE_API_KEY") is None)
    chat_parser.add_argument("--session-id", required=True)
    chat_parser.add_argument("message")

    subparsers.add_parser("health", help="Check health endpoint")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "health":
        return check_health(args.base_url)
    if args.command == "chat":
        return send_chat(args.base_url, args.api_key, args.session_id, args.message)
    return 1


if __name__ == "__main__":
    sys.exit(main())
