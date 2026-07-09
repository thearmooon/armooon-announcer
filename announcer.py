#!/usr/bin/env python3
"""
Armooon cloud announcer — runs on GitHub Actions every few minutes.

- New YouTube upload  -> @everyone post in #youtube (Discord webhook)
- Twitch goes live    -> @everyone post in #livestreams (Discord webhook)

Stateless-server friendly: remembers what it already announced in state.json,
which the workflow commits back to the repo after each run.

No external dependencies — Python 3.10+ stdlib only.
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone

# ---------------------------------------------------------------- config ---
YT_CHANNEL_ID = os.environ.get("YT_CHANNEL_ID", "UCgFLAH9i3I1qIzMnOM9Nglg")
TWITCH_USER = os.environ.get("TWITCH_USER", "armooonlol")
WEBHOOK_YOUTUBE = os.environ.get("DISCORD_YOUTUBE_WEBHOOK", "")
WEBHOOK_LIVE = os.environ.get("DISCORD_LIVESTREAMS_WEBHOOK", "")
DRY_RUN = os.environ.get("DRY_RUN", "") == "1"
STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.json")

RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={YT_CHANNEL_ID}"
TWITCH_URL = f"https://www.twitch.tv/{TWITCH_USER}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

# Max age for a video to still be worth announcing (protects against
# announcing something ancient on a state reset).
MAX_VIDEO_AGE_HOURS = 48


# --------------------------------------------------------------- helpers ---
def http_get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", errors="replace")


def post_webhook(webhook_url: str, content: str) -> None:
    if DRY_RUN:
        print(f"[DRY RUN] would post: {content!r}")
        return
    if not webhook_url:
        print("WARNING: webhook URL missing, skipping post", file=sys.stderr)
        return
    payload = json.dumps({
        "content": content,
        "allowed_mentions": {"parse": ["everyone"]},
    }).encode()
    req = urllib.request.Request(
        webhook_url, data=payload,
        headers={"Content-Type": "application/json", "User-Agent": UA},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        r.read()


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"last_video_id": None, "was_live": False}


def save_state(state: dict) -> None:
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")


def parse_latest_video(rss_xml: str):
    """Return (video_id, title, published_dt) of the newest feed entry, or None."""
    entry_match = re.search(r"<entry>(.*?)</entry>", rss_xml, re.DOTALL)
    if not entry_match:
        return None
    entry = entry_match.group(1)
    vid = re.search(r"<yt:videoId>([^<]+)</yt:videoId>", entry)
    title = re.search(r"<title>([^<]*)</title>", entry)
    published = re.search(r"<published>([^<]+)</published>", entry)
    if not vid:
        return None
    pub_dt = None
    if published:
        try:
            pub_dt = datetime.fromisoformat(published.group(1))
        except ValueError:
            pass
    return (
        vid.group(1).strip(),
        (title.group(1).strip() if title else "new video"),
        pub_dt,
    )


# ------------------------------------------------------------------ main ---
def main() -> int:
    state = load_state()
    summary = []

    # --- YouTube -----------------------------------------------------------
    try:
        latest = parse_latest_video(http_get(RSS_URL))
    except Exception as e:
        print(f"RSS check failed: {e}", file=sys.stderr)
        latest = None

    if latest:
        video_id, title, pub_dt = latest
        if state["last_video_id"] is None:
            # First ever run: seed silently so we never re-announce history.
            state["last_video_id"] = video_id
            summary.append(f"seeded state with {video_id}, no announcement")
        elif video_id != state["last_video_id"]:
            fresh = True
            if pub_dt is not None:
                age_h = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
                fresh = age_h <= MAX_VIDEO_AGE_HOURS
            if fresh:
                post_webhook(
                    WEBHOOK_YOUTUBE,
                    f"@everyone new video just dropped \U0001f525 **{title}**\n"
                    f"https://youtu.be/{video_id}",
                )
                summary.append(f"announced video {video_id}")
            else:
                summary.append(f"saw {video_id} but too old, skipped")
            state["last_video_id"] = video_id
        else:
            summary.append("no new video")
    else:
        summary.append("rss unavailable")

    # --- Twitch --------------------------------------------------------------
    try:
        live_now = "isLiveBroadcast" in http_get(TWITCH_URL)
    except Exception as e:
        print(f"Twitch check failed: {e}", file=sys.stderr)
        live_now = state["was_live"]  # inconclusive: keep previous, no edge

    if live_now and not state["was_live"]:
        post_webhook(
            WEBHOOK_LIVE,
            f"@everyone armooon is LIVE, come hang out ➡️ {TWITCH_URL}",
        )
        summary.append("announced live")
    elif live_now:
        summary.append("still live")
    else:
        summary.append("not live")
    state["was_live"] = live_now

    save_state(state)
    print("; ".join(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main())
