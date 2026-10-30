#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Nikita <it@aniops.by>
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Prefix titles of existing Deck cards with '#<card id>'.

The Nextcloud app in this repository numbers cards at creation time. Cards that
existed before the app was installed keep their titles - this script fills the
gap through the Deck REST API.

Credentials come from the environment:
    NC_URL           base URL, e.g. https://cloud.example.com
    NC_USER          Nextcloud login
    NC_APP_PASSWORD  app password (Settings -> Security -> App passwords)

Examples:
    python3 backfill.py --once                  # dry run, prints what would change
    python3 backfill.py --once --apply          # rename
    python3 backfill.py --loop --apply          # keep watching every 60 s
    python3 backfill.py --boards 2,4 --apply    # only boards 2 and 4
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time

import requests
from requests.auth import HTTPBasicAuth

HEADERS = {"OCS-APIRequest": "true", "Accept": "application/json", "Content-Type": "application/json"}


def numbered(title: str, card_id: int) -> str | None:
    """Return the title to write, or None when it is already correct.

    A leading '#<other id>' is replaced, not stacked: Deck's "copy card" copies
    the title together with the old number."""
    title = title or ""
    match = re.match(r"^#(\d+)(?:\s+|$)", title)
    if match:
        if int(match.group(1)) == card_id:
            return None
        return f"#{card_id} {title[match.end():]}".rstrip()
    return f"#{card_id} {title}".strip()


def rename(session: requests.Session, api: str, board_id: int, card: dict, title: str) -> bool:
    """PUT the card back with a new title. Deck's update resets the fields it does
    not receive (duedate, startdate), so pass everything the card already has."""
    payload = {
        "title": title,
        "type": card.get("type") or "plain",
        "owner": (card.get("owner") or {}).get("primaryKey") or "",
        "description": card.get("description") or "",
        "order": card.get("order") or 0,
        "duedate": card.get("duedate"),
        "startdate": card.get("startdate"),
        "archived": card.get("archived"),
    }
    url = f"{api}/boards/{board_id}/stacks/{card['stackId']}/cards/{card['id']}"
    response = session.put(url, headers=HEADERS, json=payload, timeout=30)
    if response.status_code != 200:
        print(f"  FAILED #{card['id']}: HTTP {response.status_code} {response.text[:160]}")
        return False
    return True


def pass_once(session: requests.Session, api: str, boards: list[int], apply: bool) -> int:
    changed = 0
    board_list = session.get(f"{api}/boards", headers=HEADERS, timeout=30).json()
    for board in [b for b in board_list if isinstance(b, dict)]:
        if boards and board["id"] not in boards:
            continue
        cards = []
        try:
            for stack in session.get(f"{api}/boards/{board['id']}/stacks", headers=HEADERS, timeout=30).json():
                cards.extend(stack.get("cards") or [])
        except requests.HTTPError as exc:
            print(f"board {board['id']}: cannot read stacks ({exc})")
            continue
        for card in sorted(cards, key=lambda c: c["id"]):
            new_title = numbered(card.get("title") or "", card["id"])
            if new_title is None:
                continue
            changed += 1
            if not apply:
                print(f"board {board['id']}: would rename #{card['id']} {card['title']!r} -> {new_title!r}")
                continue
            if rename(session, api, board["id"], card, new_title):
                print(f"board {board['id']}: #{card['id']} -> {new_title!r}")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Prefix Deck card titles with their id")
    parser.add_argument("--boards", default="", help="comma separated board ids (default: all accessible)")
    parser.add_argument("--apply", action="store_true", help="actually rename (default: dry run)")
    parser.add_argument("--once", action="store_true", help="single pass (default)")
    parser.add_argument("--loop", action="store_true", help="watch continuously")
    parser.add_argument("--interval", type=int, default=60, help="seconds between passes with --loop")
    args = parser.parse_args()

    url, user, password = (os.environ.get(k) for k in ("NC_URL", "NC_USER", "NC_APP_PASSWORD"))
    if not (url and user and password):
        parser.error("set NC_URL, NC_USER and NC_APP_PASSWORD")
    session = requests.Session()
    session.auth = HTTPBasicAuth(user, password)
    api = f"{url.rstrip('/')}/index.php/apps/deck/api/v1.0"
    boards = [int(x) for x in args.boards.split(",") if x.strip()]

    while True:
        changed = pass_once(session, api, boards, args.apply)
        print(f"{changed} card(s) {'renamed' if args.apply else 'to rename (dry run)'}")
        if not args.loop:
            return 0
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
