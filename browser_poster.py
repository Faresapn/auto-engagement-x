"""
browser_poster.py — Playwright-based X poster (no API, no credits).
Handles: login (interactive), post, reply, quote, read_timeline.

Uses persistent storage_state per account (sessions/<handle>.json).
"""
from __future__ import annotations
import json
import time
import random
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout, Page

BASE = Path(__file__).resolve().parent
SESSIONS = BASE / "sessions"
SESSIONS.mkdir(exist_ok=True)


def _session_file(handle: str) -> Path:
    return SESSIONS / f"{handle}.json"


def _human_delay(min_ms=800, max_ms=2200):
    """Random delay to look human."""
    time.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


def _new_context(pw, handle: str, headless: bool):
    """New browser context — load session if exists."""
    sf = _session_file(handle)
    browser = pw.chromium.launch(headless=headless)
    if sf.exists():
        context = browser.new_context(
            storage_state=str(sf),
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
    else:
        context = browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
    return browser, context


def _save_session(context, handle: str):
    """Save cookies + localStorage to session file."""
    sf = _session_file(handle)
    context.storage_state(path=str(sf))


def login_interactive(handle: str):
    """
    Open a HEADED browser so user can login manually.
    After login, press ENTER in terminal to save session.
    """
    with sync_playwright() as pw:
        browser, context = _new_context(pw, handle, headless=False)
        page = context.new_page()
        page.goto("https://x.com/login")
        print(f"\n👉 Login manual sebagai @{handle} di browser yang muncul.")
        print(f"   Setelah login sukses (masuk ke home timeline),")
        print(f"   BALIK ke terminal ini dan tekan ENTER.\n")
        input("Press ENTER after login is done... ")
        _save_session(context, handle)
        print(f"✅ Session saved: {_session_file(handle)}")
        browser.close()


def _verify_logged_in(page: Page, handle: str) -> bool:
    """Check if session is still valid. More tolerant to slow loads / UI changes."""
    try:
        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
        _human_delay(2000, 3500)
        # If redirected to login page, session dead
        if "/login" in page.url or "/i/flow/login" in page.url:
            return False
        # Multi-selector fallback (X sometimes changes testids)
        selectors = [
            '[data-testid="SideNav_NewTweet_Button"]',
            '[data-testid="SideNav_AccountSwitcher_Button"]',
            'a[data-testid="AppTabBar_Home_Link"]',
            'nav[role="navigation"]',
        ]
        for sel in selectors:
            try:
                page.wait_for_selector(sel, timeout=6000)
                return True
            except PWTimeout:
                continue
        # None matched — probably logged out. But double-check URL not redirected
        if "x.com/home" in page.url or "x.com/i/" in page.url:
            # Still on home even if selectors missed — likely session OK, X just slow
            print(f"[verify] selectors missed but URL={page.url} — assuming OK", file=sys.stderr)
            return True
        return False
    except Exception as e:
        print(f"[verify] err: {e}", file=sys.stderr)
        return False


def post_tweet(handle: str, text: str, headless: bool = True, dry_run: bool = False) -> str | None:
    """Post standalone tweet. Returns tweet URL or None."""
    if dry_run:
        print(f"[DRY-RUN] would POST as @{handle}:\n  {text}")
        return None
    with sync_playwright() as pw:
        browser, context = _new_context(pw, handle, headless=headless)
        page = context.new_page()
        try:
            if not _verify_logged_in(page, handle):
                raise RuntimeError(f"session expired for @{handle} — re-run login_interactive")
            # Go to home & click compose
            page.click('[data-testid="SideNav_NewTweet_Button"]')
            _human_delay(1000, 2000)
            # Type into compose area
            page.click('[data-testid="tweetTextarea_0"]')
            _human_delay()
            # Type char-by-char to look human
            for ch in text:
                page.keyboard.type(ch)
                time.sleep(random.uniform(0.01, 0.05))
            _human_delay(1500, 3000)
            # Click post
            page.click('[data-testid="tweetButton"]')
            _human_delay(3000, 5000)
            # Save updated session (fresh cookies)
            _save_session(context, handle)
            # Try to get tweet URL by navigating to profile
            page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=15000)
            _human_delay(2000, 3000)
            first_tweet = page.query_selector('article a[href*="/status/"]')
            url = first_tweet.get_attribute("href") if first_tweet else None
            return f"https://x.com{url}" if url else "posted (url unknown)"
        finally:
            browser.close()


def reply_tweet(handle: str, tweet_url: str, text: str, headless: bool = True, dry_run: bool = False) -> str | None:
    """Reply to a tweet by URL."""
    if dry_run:
        print(f"[DRY-RUN] would REPLY as @{handle} to {tweet_url}:\n  {text}")
        return None
    with sync_playwright() as pw:
        browser, context = _new_context(pw, handle, headless=headless)
        page = context.new_page()
        try:
            if not _verify_logged_in(page, handle):
                raise RuntimeError(f"session expired for @{handle}")
            page.goto(tweet_url, wait_until="domcontentloaded", timeout=20000)
            _human_delay(2000, 3500)
            # Click the reply button on the main tweet
            page.click('[data-testid="reply"]')
            _human_delay(1500, 2500)
            # Type reply
            page.click('[data-testid="tweetTextarea_0"]')
            _human_delay()
            for ch in text:
                page.keyboard.type(ch)
                time.sleep(random.uniform(0.01, 0.05))
            _human_delay(1500, 3000)
            page.click('[data-testid="tweetButton"]')
            _human_delay(3000, 5000)
            _save_session(context, handle)
            return "reply posted"
        finally:
            browser.close()


def quote_tweet(handle: str, tweet_url: str, text: str, headless: bool = True, dry_run: bool = False) -> str | None:
    """Quote-tweet by URL (retweet with comment)."""
    if dry_run:
        print(f"[DRY-RUN] would QUOTE as @{handle} of {tweet_url}:\n  {text}")
        return None
    with sync_playwright() as pw:
        browser, context = _new_context(pw, handle, headless=headless)
        page = context.new_page()
        try:
            if not _verify_logged_in(page, handle):
                raise RuntimeError(f"session expired for @{handle}")
            page.goto(tweet_url, wait_until="domcontentloaded", timeout=20000)
            _human_delay(2000, 3500)
            # Click retweet button
            page.click('[data-testid="retweet"]')
            _human_delay(700, 1200)
            # Click "Quote" option
            page.click('[data-testid="Dropdown"] a[href*="/compose/post"]')
            _human_delay(1500, 2500)
            # Type quote text
            page.click('[data-testid="tweetTextarea_0"]')
            _human_delay()
            for ch in text:
                page.keyboard.type(ch)
                time.sleep(random.uniform(0.01, 0.05))
            _human_delay(1500, 3000)
            page.click('[data-testid="tweetButton"]')
            _human_delay(3000, 5000)
            _save_session(context, handle)
            return "quote posted"
        finally:
            browser.close()


def read_timeline(handle: str, target_user: str, limit: int = 10, headless: bool = True) -> list[dict]:
    """
    Read latest tweets from target_user's profile via browser.
    Returns list of {url, text, likes, age_min} (age_min = umur tweet dalam menit).
    NO X API used.
    """
    import datetime as _dt
    with sync_playwright() as pw:
        browser, context = _new_context(pw, handle, headless=headless)
        page = context.new_page()
        try:
            if not _verify_logged_in(page, handle):
                raise RuntimeError(f"session expired for @{handle} — re-run login_interactive")
            page.goto(f"https://x.com/{target_user}", wait_until="domcontentloaded", timeout=20000)
            _human_delay(2500, 4000)
            # Scroll a bit to load tweets
            for _ in range(2):
                page.mouse.wheel(0, 800)
                _human_delay(700, 1400)
            articles = page.query_selector_all('article[data-testid="tweet"]')
            results = []
            now = _dt.datetime.now(_dt.timezone.utc)
            for art in articles[:limit]:
                try:
                    link_el = art.query_selector('a[href*="/status/"]')
                    if not link_el:
                        continue
                    href = link_el.get_attribute("href")
                    url = f"https://x.com{href}"
                    # Text
                    text_el = art.query_selector('[data-testid="tweetText"]')
                    text = text_el.inner_text() if text_el else ""
                    # Like count (aria-label like "42 Likes")
                    like_el = art.query_selector('[data-testid="like"]')
                    likes = 0
                    if like_el:
                        aria = like_el.get_attribute("aria-label") or ""
                        parts = aria.split()
                        for p in parts:
                            if p.isdigit():
                                likes = int(p)
                                break
                    # Age (menit) from <time datetime="...">
                    age_min = 99999  # default: super old kalau ga bisa parse
                    time_el = art.query_selector('time')
                    if time_el:
                        dt_str = time_el.get_attribute('datetime')
                        if dt_str:
                            try:
                                # ISO 8601 UTC
                                posted = _dt.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
                                age_min = int((now - posted).total_seconds() / 60)
                            except Exception:
                                pass
                    results.append({"url": url, "text": text, "likes": likes, "age_min": age_min})
                except Exception:
                    continue
            return results
        finally:
            browser.close()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_login = sub.add_parser("login", help="Interactive login for account")
    p_login.add_argument("handle")

    p_post = sub.add_parser("post")
    p_post.add_argument("handle")
    p_post.add_argument("text")
    p_post.add_argument("--dry-run", action="store_true")

    p_reply = sub.add_parser("reply")
    p_reply.add_argument("handle")
    p_reply.add_argument("url")
    p_reply.add_argument("text")
    p_reply.add_argument("--dry-run", action="store_true")

    p_read = sub.add_parser("read")
    p_read.add_argument("handle")
    p_read.add_argument("target")
    p_read.add_argument("--limit", type=int, default=5)

    args = ap.parse_args()

    if args.cmd == "login":
        login_interactive(args.handle)
    elif args.cmd == "post":
        r = post_tweet(args.handle, args.text, dry_run=args.dry_run)
        print(r)
    elif args.cmd == "reply":
        r = reply_tweet(args.handle, args.url, args.text, dry_run=args.dry_run)
        print(r)
    elif args.cmd == "read":
        r = read_timeline(args.handle, args.target, limit=args.limit)
        for t in r:
            print(f"  {t['likes']:>4} ❤ {t['url']}")
            print(f"       {t['text'][:80]}")
