"""
main.py — Orchestrator untuk 1 akun tumbal.
Loop: pick action (reply/quote/post) → fetch target → LLM → post → sleep.
Enforce daily_max & human-like delay.
"""
from __future__ import annotations
import argparse
import json
import random
import time
import sys
import datetime as dt
from pathlib import Path
import yaml

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))

from browser_poster import (
    post_tweet, reply_tweet, quote_tweet, read_timeline, _session_file,
)
from llm_writer import gen_reply, gen_quote, gen_post


LOGS = BASE / "logs"
LOGS.mkdir(exist_ok=True)
STATE = BASE / "state"
STATE.mkdir(exist_ok=True)


def load_config(handle: str) -> dict:
    cfg_path = BASE / "config" / f"{handle}.yaml"
    if not cfg_path.exists():
        raise FileNotFoundError(f"config not found: {cfg_path}")
    return yaml.safe_load(cfg_path.read_text())


def _today_utc() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%d")


def _tx_log_path(handle: str) -> Path:
    return LOGS / f"tx-{handle}.jsonl"


def _replied_log_path(handle: str) -> Path:
    return STATE / f"replied-{handle}.log"


def today_count(handle: str) -> int:
    """Count tweets posted today (UTC)."""
    path = _tx_log_path(handle)
    if not path.exists():
        return 0
    today = _today_utc()
    count = 0
    for line in path.read_text().splitlines():
        try:
            r = json.loads(line)
            if r.get("ts", "").startswith(today) and r.get("ok"):
                count += 1
        except Exception:
            continue
    return count


def append_tx(handle: str, entry: dict):
    entry["ts"] = dt.datetime.utcnow().isoformat() + "Z"
    with open(_tx_log_path(handle), "a") as f:
        f.write(json.dumps(entry) + "\n")


def replied_set(handle: str) -> set:
    p = _replied_log_path(handle)
    if not p.exists():
        return set()
    return set(p.read_text().split())


def mark_replied(handle: str, tweet_url: str):
    with open(_replied_log_path(handle), "a") as f:
        f.write(tweet_url + "\n")


def pick_action(mix: dict) -> str:
    """Weighted random pick from mix probabilities."""
    r = random.random()
    cum = 0.0
    for action, prob in mix.items():
        cum += prob
        if r < cum:
            return action
    return list(mix.keys())[0]


def maybe_add_cta(text: str, cta_url: str, cta_rate: float) -> str:
    """Occasionally append CTA link naturally."""
    if random.random() < cta_rate:
        return f"{text}\n\n{cta_url}"
    return text


def fetch_hot_target(handle: str, targets: list, exclude: set,
                     fresh_max_age_min: int = 60, fresh_min_likes: int = 100,
                     viral_max_age_hours: int = 6, viral_min_likes: int = 500,
                     recent_max_age_hours: int = 6, recent_min_likes: int = 20
                     ) -> tuple[str, dict] | None:
    """
    3-TIER target picker:

    🔥 TIER 1 - FRESH: age <= fresh_max_age_min + likes >= fresh_min_likes
       → pilih velocity tertinggi (likes/age) = paling nanjak

    🚀 TIER 2 - RECENT VIRAL: age <= viral_max_age_hours + likes >= viral_min_likes
       → pilih velocity tertinggi = "potensi viral berkelanjutan"

    🕐 TIER 3 - RECENT (fallback): age <= recent_max_age_hours + likes >= recent_min_likes
       → pilih paling muda (biar tetep engagement window)

    ❌ SKIP: kalau semua kosong.

    Returns (target_user, tweet_dict) or None.
    """
    random.shuffle(targets)
    fresh_pool = []
    viral_pool = []
    recent_pool = []
    for target in targets:
        try:
            tweets = read_timeline(handle, target, limit=6)
        except Exception as e:
            print(f"[fetch] err reading @{target}: {e}", file=sys.stderr)
            continue
        for t in tweets:
            if t["url"] in exclude:
                continue
            age = t.get("age_min", 99999)
            likes = t["likes"]
            # T1 FRESH
            if age <= fresh_max_age_min and likes >= fresh_min_likes:
                fresh_pool.append((target, t))
            # T2 RECENT VIRAL (harus < viral_max_age_hours, likes tinggi)
            elif age <= viral_max_age_hours * 60 and likes >= viral_min_likes:
                viral_pool.append((target, t))
            # T3 RECENT (fallback: masih hangat, ada trafik dikit)
            elif age <= recent_max_age_hours * 60 and likes >= recent_min_likes:
                recent_pool.append((target, t))

    # TIER 1: pilih velocity tertinggi
    if fresh_pool:
        fresh_pool.sort(key=lambda x: -x[1]["likes"] / max(x[1].get("age_min", 1), 1))
        target, tw = fresh_pool[0]
        vel = tw["likes"] / max(tw.get("age_min", 1), 1)
        print(f"[fetch] 🔥 T1 FRESH: @{target} — {tw['likes']} likes, {tw.get('age_min','?')}min old, velocity={vel:.1f}/min")
        return (target, tw)

    # TIER 2: pilih velocity tertinggi (potensi viral berkelanjutan)
    if viral_pool:
        viral_pool.sort(key=lambda x: -x[1]["likes"] / max(x[1].get("age_min", 1), 1))
        target, tw = viral_pool[0]
        vel = tw["likes"] / max(tw.get("age_min", 1), 1)
        print(f"[fetch] 🚀 T2 VIRAL: @{target} — {tw['likes']} likes, {tw.get('age_min','?')}min old, velocity={vel:.1f}/min")
        return (target, tw)

    # TIER 3: paling muda (fallback engagement)
    if recent_pool:
        recent_pool.sort(key=lambda x: x[1].get("age_min", 99999))
        target, tw = recent_pool[0]
        print(f"[fetch] 🕐 T3 RECENT: @{target} — {tw['likes']} likes, {tw.get('age_min','?')}min old")
        return (target, tw)

    return None


def do_action(handle: str, action: str, cfg: dict, dry_run: bool) -> bool:
    """Execute one action. Returns True if posted successfully."""
    cta_rate = cfg.get("cta_rate", 0.0)
    # LLM decide sisipkan CTA organik atau nggak, based on topic match + probability
    with_cta = random.random() < cta_rate

    if action == "post":
        topic = random.choice(cfg["post_topics"])
        print(f"[post] topic: {topic} (with_cta={with_cta})")
        text = gen_post(topic, with_cta=with_cta)
        print(f"[post] text: {text!r}")
        try:
            url = post_tweet(handle, text, dry_run=dry_run)
            append_tx(handle, {"type": "post", "text": text, "cta": with_cta, "url": url, "ok": True})
            print(f"✅ posted: {url}")
            return True
        except Exception as e:
            append_tx(handle, {"type": "post", "text": text, "err": str(e)[:200], "ok": False})
            print(f"❌ post FAILED: {e}", file=sys.stderr)
            return False

    # reply or quote — both need a hot target
    exclude = replied_set(handle)
    picked = fetch_hot_target(
        handle,
        list(cfg["targets"]),
        exclude,
        fresh_max_age_min=cfg.get("fresh_max_age_min", 60),
        fresh_min_likes=cfg.get("fresh_min_likes", 100),
        viral_max_age_hours=cfg.get("viral_max_age_hours", 6),
        viral_min_likes=cfg.get("viral_min_likes", 500),
        recent_max_age_hours=cfg.get("recent_max_age_hours", 6),
        recent_min_likes=cfg.get("recent_min_likes", 20),
    )
    if not picked:
        print("[fetch] no hot target found — semua target ga match tier fresh/viral/recent")
        return False
    target, tw = picked
    print(f"[fetch] target: @{target} ({tw['likes']} likes) with_cta={with_cta}")

    if action == "reply":
        text = gen_reply(tw["text"], author=target, likes=tw["likes"], with_cta=with_cta)
        print(f"[reply] text: {text!r}")
        try:
            r = reply_tweet(handle, tw["url"], text, dry_run=dry_run)
            append_tx(handle, {"type": "reply", "target": target, "src": tw["url"], "text": text, "cta": with_cta, "ok": True})
            if not dry_run:
                mark_replied(handle, tw["url"])
            print(f"✅ replied to @{target}: {r}")
            return True
        except Exception as e:
            append_tx(handle, {"type": "reply", "target": target, "src": tw["url"], "err": str(e)[:200], "ok": False})
            print(f"❌ reply FAILED: {e}", file=sys.stderr)
            return False

    if action == "quote":
        text = gen_quote(tw["text"], author=target, likes=tw["likes"], with_cta=with_cta)
        print(f"[quote] text: {text!r}")
        try:
            r = quote_tweet(handle, tw["url"], text, dry_run=dry_run)
            append_tx(handle, {"type": "quote", "target": target, "src": tw["url"], "text": text, "cta": with_cta, "ok": True})
            if not dry_run:
                mark_replied(handle, tw["url"])
            print(f"✅ quoted @{target}: {r}")
            return True
        except Exception as e:
            append_tx(handle, {"type": "quote", "target": target, "src": tw["url"], "err": str(e)[:200], "ok": False})
            print(f"❌ quote FAILED: {e}", file=sys.stderr)
            return False

    return False


def main_loop(handle: str, dry_run: bool = False, one_shot: bool = False):
    cfg = load_config(handle)
    if not _session_file(handle).exists():
        raise RuntimeError(f"No session for @{handle}. Run: python browser_poster.py login {handle}")

    print(f"=== x-browser-bot loop: @{handle} ===")
    print(f"   daily_max: {cfg['daily_max']}, delay: {cfg['min_delay_sec']}-{cfg['max_delay_sec']}s")
    print(f"   mix: {cfg['mix']}, min_likes: {cfg['min_likes']}")
    print(f"   dry_run: {dry_run}, one_shot: {one_shot}")

    while True:
        cnt = today_count(handle)
        if cnt >= cfg["daily_max"]:
            print(f"[cap] daily cap reached ({cnt}/{cfg['daily_max']}) — sleep 30m then re-check")
            if one_shot:
                return
            time.sleep(30 * 60)
            continue

        action = pick_action(cfg["mix"])
        print(f"\n[{dt.datetime.now().strftime('%H:%M:%S')}] action={action} count={cnt}/{cfg['daily_max']}")
        try:
            ok = do_action(handle, action, cfg, dry_run=dry_run)
        except Exception as e:
            print(f"[action] uncaught: {e}", file=sys.stderr)
            ok = False

        if one_shot:
            return

        # Sleep random
        sleep_s = random.randint(cfg["min_delay_sec"], cfg["max_delay_sec"])
        print(f"[sleep] {sleep_s}s")
        time.sleep(sleep_s)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("handle", help="handle (e.g. anastasiavlkvv)")
    ap.add_argument("--dry-run", action="store_true", help="don't actually post")
    ap.add_argument("--one-shot", action="store_true", help="run 1 action then exit")
    args = ap.parse_args()
    try:
        main_loop(args.handle, dry_run=args.dry_run, one_shot=args.one_shot)
    except KeyboardInterrupt:
        print("\n[quit]")
