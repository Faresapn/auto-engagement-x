"""
import_cookies.py — Import cookies from Chrome (via exported JSON) → Playwright session.

Cara pake:
1. Install extension Chrome "Cookie-Editor" atau "Get cookies.txt LOCALLY"
2. Buka x.com di Chrome (harus lagi LOGIN di akun target)
3. Klik extension → Export → pilih "JSON" format
4. Save file ke ~/x-browser-bot/import/anastasiavlkvv.json
5. Jalanin: python import_cookies.py anastasiavlkvv

Script bakal validate cookie & save ke sessions/<handle>.json (format Playwright).
"""
from __future__ import annotations
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(__file__).resolve().parent
IMPORT_DIR = BASE / "import"
SESSIONS = BASE / "sessions"
IMPORT_DIR.mkdir(exist_ok=True)
SESSIONS.mkdir(exist_ok=True)


def load_exported_cookies(path: Path) -> list[dict]:
    """
    Parse cookie file. Support 2 formats:
    - Cookie-Editor JSON export (array of dicts)
    - EditThisCookie / manual export
    """
    raw = json.loads(path.read_text())
    if isinstance(raw, dict) and "cookies" in raw:
        raw = raw["cookies"]
    if not isinstance(raw, list):
        raise ValueError(f"expected list of cookies, got {type(raw)}")

    out = []
    for c in raw:
        # Playwright format
        cookie = {
            "name": c.get("name") or c.get("Name"),
            "value": c.get("value") or c.get("Value"),
            "domain": c.get("domain") or c.get("Domain") or ".x.com",
            "path": c.get("path") or c.get("Path") or "/",
        }
        # Normalize domain (Chrome exports ".x.com", Playwright wants ".x.com" or "x.com")
        if cookie["domain"] and not cookie["domain"].startswith("."):
            if cookie["domain"] not in ("x.com", "twitter.com"):
                cookie["domain"] = "." + cookie["domain"]

        # Expires (Playwright wants number seconds since epoch)
        exp = c.get("expirationDate") or c.get("expires") or c.get("expiry")
        if exp:
            cookie["expires"] = float(exp)
        else:
            cookie["expires"] = -1  # session cookie

        # HttpOnly / Secure / SameSite
        cookie["httpOnly"] = bool(c.get("httpOnly") or c.get("HttpOnly") or False)
        cookie["secure"] = bool(c.get("secure") or c.get("Secure") or True)
        ss = c.get("sameSite") or c.get("SameSite")
        if ss:
            # Playwright expects "Strict" | "Lax" | "None"
            ss_map = {
                "strict": "Strict", "lax": "Lax", "no_restriction": "None",
                "none": "None", "unspecified": "Lax",
            }
            cookie["sameSite"] = ss_map.get(str(ss).lower(), "Lax")
        else:
            cookie["sameSite"] = "Lax"

        # Skip invalid entries
        if not cookie["name"] or not cookie["value"]:
            continue
        # Only keep x.com / twitter.com cookies
        dom = cookie["domain"].lstrip(".")
        if dom not in ("x.com", "twitter.com") and not dom.endswith(".x.com") and not dom.endswith(".twitter.com"):
            continue
        out.append(cookie)
    return out


def import_and_save(handle: str, cookie_json_path: Path):
    """Load Chrome-exported cookies → save as Playwright storage_state."""
    if not cookie_json_path.exists():
        raise FileNotFoundError(f"Cookie file not found: {cookie_json_path}")

    cookies = load_exported_cookies(cookie_json_path)
    print(f"[import] loaded {len(cookies)} cookies from {cookie_json_path.name}")

    # Build Playwright storage_state format
    storage = {
        "cookies": cookies,
        "origins": [],  # localStorage — usually not needed for X
    }

    session_path = SESSIONS / f"{handle}.json"
    session_path.write_text(json.dumps(storage, indent=2))
    print(f"[import] saved to {session_path}")

    # Verify with headed browser
    print(f"[verify] opening x.com/home to check session...")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        context = browser.new_context(
            storage_state=str(session_path),
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        )
        page = context.new_page()
        page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
        import time
        time.sleep(4)
        url = page.url
        if "/login" in url or "/i/flow/login" in url:
            print(f"❌ session INVALID — redirected to login ({url})")
            print("   Coba re-export cookies dari Chrome (pastikan lagi login di x.com)")
        else:
            print(f"✅ session VALID — masuk ke {url}")
            print(f"   Save session updated & ready to use.")
            # Re-save biar cookies fresh
            context.storage_state(path=str(session_path))
        print(f"\nTutup browser manually, atau tekan ENTER buat close.")
        input()
        browser.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_cookies.py <handle>")
        print("       (looks for import/<handle>.json)")
        sys.exit(1)
    handle = sys.argv[1]
    cookie_file = IMPORT_DIR / f"{handle}.json"
    import_and_save(handle, cookie_file)
