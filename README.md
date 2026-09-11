# 🚀 Auto Engagement X

**A smart, browser-based X (Twitter) engagement bot.** Skip the $0.05/read + $0.01/write X API fees — this uses Playwright with your existing browser cookies and Claude LLM to post natural, human-like replies, quotes, and tweets.

Built for creators who want organic reach without burning API credits.

---

## ✨ Features

- 🌐 **Browser automation** with Playwright — zero X API cost
- 🍪 **Cookie import** from your existing Chrome/browser (no re-login needed)
- 🧠 **Claude LLM** (Sonnet/Opus) — replies that sound like a real human, not a bot
- 🎯 **3-tier target picker** — Fresh > Recent Viral > Recent (engagement window first)
- 🕒 **Human-like delays** (60-100 min random between actions)
- 📊 **Daily cap** — max N tweets/day per account (default 12)
- 🔗 **Smart CTA** — LLM naturally inserts your link when the topic fits (no brutal spam)
- 📝 **Full JSONL transaction log** — every post/reply/quote tracked
- ⚙️ **Per-account YAML config** — targets, mix, delay, CTA rate

---

## 💡 Why This Method?

**X API v2 pricing:**
- Post/reply/quote = **$0.01/tweet** (write credit)
- Search/timeline = **$0.05/request** (read credit) — burns balance fast

**Browser bot = $0 X cost.** You only pay for the LLM (~$1-3/day with Claude Sonnet).

**Trade-off:** Higher suspension risk if misused. Best practices:
- Long delays (60-100 min between actions)
- Low daily cap (12/day max)
- Use cookies from a trusted browser (avoid "temporarily limited" errors)

---

## 📋 Prerequisites

- **macOS / Linux** (Playwright fully supported)
- **Python 3.9+**
- **Chrome / Brave / Edge** — for cookie export
- **"Cookie-Editor" extension** in browser: [Chrome Store](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
- **LLM API access** — Claude via Anthropic API or a proxy (OpenRouter, LiteLLM, etc.)

---

## 🛠 Setup — Step by Step

### 1. Clone & Install

```bash
git clone https://github.com/Faresapn/auto-engagement-x.git ~/auto-engagement-x
cd ~/auto-engagement-x

# Setup Python venv
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Chromium (for Playwright)
python -m playwright install chromium
```

### 2. Configure LLM API Key

Copy the example env file:

```bash
cp .env.example .env
```

Edit `.env`:

```bash
# Option A: Direct Anthropic
LLM_API_KEY=sk-ant-your-key-here
LLM_MODEL=claude-sonnet-4-5-20250929
LLM_BASE_URL=https://api.anthropic.com/v1

# Option B: Via OpenRouter
# LLM_API_KEY=sk-or-your-key
# LLM_MODEL=anthropic/claude-3.5-sonnet
# LLM_BASE_URL=https://openrouter.ai/api/v1
```

### 3. Create Per-Account Config

Copy the example and customize:

```bash
cp config/example.yaml config/<handle>.yaml
```

Edit `config/<handle>.yaml`:

```yaml
handle: yourhandle    # X handle without @

# Target accounts to scrape (their audience = your target market)
targets:
  - shadcn
  - v0
  - rauchg
  # ... add relevant accounts for your niche

# 3-TIER target picker (see explanation below)
fresh_max_age_min: 60
fresh_min_likes: 100

viral_max_age_hours: 6
viral_min_likes: 500

recent_max_age_hours: 6
recent_min_likes: 20

# Rate limiting
daily_max: 12              # max tweets/day
min_delay_sec: 3600        # 60 min
max_delay_sec: 6000        # 100 min

# Action mix (total = 1.0)
mix:
  reply: 0.60
  quote: 0.30
  post: 0.10

# Topics for standalone posts (randomly picked)
post_topics:
  - "one prompt shipped a better landing page than 3 weeks of agency work"
  - "the real bottleneck in shipping isnt code, its knowing what to prompt"

# Optional CTA (LLM naturally inserts if topic matches)
cta_url: https://yoursite.com
cta_rate: 0.35             # 35% chance CTA is inserted
```

### 4. Import Cookies from Browser

**No re-login needed!** Just import your existing session cookies from Chrome.

**a.** Install the **Cookie-Editor** Chrome extension ([link above ↑](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm))

**b.** Open `x.com` in Chrome, make sure you're **logged in** to the target account

**c.** Click the extension icon → **Export** → select **JSON** → copy/download

**d.** Save to `~/auto-engagement-x/import/<handle>.json`

Or if it copied to clipboard:
```bash
pbpaste > import/<handle>.json                     # macOS
xclip -selection clipboard -o > import/<handle>.json  # Linux
```

**e.** Import into Playwright session:
```bash
./run.sh import <handle>
```

The bot will:
1. Parse cookies
2. Save to `sessions/<handle>.json` (Playwright storage_state format)
3. Open a headed browser → verify home timeline loads
4. If ✅ VALID → ready to use
5. If ❌ INVALID → re-export cookies (make sure you're logged in on Chrome)

### 5. Dry-Run Test (No Actual Posting)

```bash
./run.sh dry <handle>
```

The bot will:
- Pick a random action (reply/quote/post)
- Scan targets via Playwright
- Generate text with LLM
- **Print `[DRY-RUN] would ...`** — NO actual post

### 6. Live 1-Shot Test

If dry-run looks good:
```bash
./run.sh test <handle>
```

This actually posts 1 tweet. Check `x.com/<handle>` — should see the new tweet.

### 7. Production Loop

```bash
./run.sh loop <handle>
```

Runs until `daily_max` is reached, with random delays. To run in background:
```bash
nohup ./run.sh loop <handle> > logs/loop.out 2>&1 &
tail -f logs/loop.out
```

---

## ⚙️ Commands (via `run.sh`)

```bash
./run.sh login <handle>              # Interactive login (backup if import fails)
./run.sh import <handle>             # Import cookies from import/<handle>.json
./run.sh dry <handle>                # Dry-run 1 action (no post)
./run.sh test <handle>               # Live 1 action
./run.sh loop <handle>               # Production loop
./run.sh read <handle> <target>      # Test scrape a target's timeline
./run.sh status <handle>             # Check today's post count
```

---

## 🎯 3-Tier Target Picker (The Smart Part)

Every iteration, the bot scans all targets and classifies each tweet:

| Tier | Criteria | Selection Strategy |
|---|---|---|
| **🔥 T1 FRESH** | age ≤60m + likes ≥100 | Highest velocity (likes/min) |
| **🚀 T2 VIRAL** | age ≤6h + likes ≥500 | Highest velocity (sustained momentum) |
| **🕐 T3 RECENT** | age ≤6h + likes ≥20 | Youngest (fallback engagement) |
| **❌ SKIP** | No match | Wait for next iteration |

**Why this works:**
- **T1**: Reply to a 30-min-old tweet with 300 likes that's climbing → if it goes viral, your reply is at the top (potentially hundreds of thousands of impressions)
- **T2**: If no fresh tweets, grab a viral one that's still young (<6h) with strong momentum
- **T3**: When everything is quiet, at least reply to something recent (engagement window still open) — never reply to old tweets where engagement has died

---

## 🧠 LLM Rules (Inspired by @achmadbeny's viral method)

The bot uses a system prompt that enforces:
- Casual English, 10-50 words
- Mostly lowercase
- No hashtags, no @mentions, no period at end
- 1-2 emojis when they fit (💀 🥴 😂 🔥)
- **React to the tweet content** (not generic "amazing", "wow")
- Sound HUMAN, not AI

**Smart CTA mode** (when `cta_rate > 0`):
- LLM decides whether to insert the link **organically** — only if the topic matches
- Example: `"shipped mine last week in 2h. found the prompt here: https://site.com"`
- If the topic doesn't fit, LLM **skips the link** (no brutal append)

---

## 📁 Project Structure

```
auto-engagement-x/
├── run.sh                     # Main wrapper (activates venv + loads env)
├── main.py                    # Orchestrator (loop, action picker, sleep)
├── browser_poster.py          # Playwright: login/post/reply/quote/read
├── llm_writer.py              # Claude LLM: gen_reply/quote/post
├── import_cookies.py          # Import Chrome cookies → Playwright session
├── config/
│   ├── example.yaml           # Config template
│   └── <handle>.yaml          # Per-account config (gitignored)
├── sessions/
│   └── <handle>.json          # Playwright storage_state (cookie + localStorage)
├── import/
│   └── <handle>.json          # Chrome-exported cookies (source, gitignored)
├── state/
│   └── replied-<handle>.log   # Dedup: URLs already replied to
├── logs/
│   └── tx-<handle>.jsonl      # Transaction log (per action)
├── venv/                      # Python virtualenv
└── README.md                  # This file
```

---

## 🛡 Best Practices (to avoid bans)

1. **Long delays** — 60+ min between actions. Default is 60-100min
2. **Low daily cap** — 12-15/day max. Don't exceed 20/day
3. **Cookies from trusted browser** — never fresh login (hits "temporarily limited")
4. **Start with 1 sacrificial account** — test 1-2 weeks, if it survives then replicate
5. **Rotate user-agent** if paranoid (edit `browser_poster.py`)
6. **Don't post 24/7** — add day/night breaks (edit `main.py` with time-of-day check)
7. **Skip some tweets** — natural mixing, don't reply to everything

---

## 🐛 Troubleshooting

### `session expired for @xxx`

Cookies expired. Re-import:
```bash
# 1. Open Chrome, x.com (make sure you're logged in)
# 2. Cookie-Editor → Export JSON → save to import/<handle>.json
# 3.
./run.sh import <handle>
```

### `LLM client not configured`

`LLM_API_KEY` env not set. Check:
```bash
echo $LLM_API_KEY   # should have value
```

Set in `.env` or `~/.zshrc`.

### `no hot target found`

All tiers empty. Solutions:
- Lower `recent_min_likes` (e.g., 20 → 10)
- Add more active accounts to `targets`
- Check `logs/tx-<handle>.jsonl` — maybe `daily_max` is hit

### `We've temporarily limited your login` during interactive login

X detected a fresh browser. Solution: **use the cookie import method** (step 4), don't login manually.

### Bot got suspended

- Check delays (must be 60+ min)
- Check daily_max (never >20/day)
- Check post content — if too spammy, refine LLM system prompt
- If suspended: (1) try appealing to X, (2) create a new account

---

## 🗺 Roadmap

- [ ] Separate scanner — scan every 5-10 min, queue fresh tweets, main loop picks from queue
- [ ] Time-of-day filter — post only during peak hours (e.g., 9AM-11PM local)
- [ ] Per-target min_likes — smaller accounts get lower threshold
- [ ] Multi-persona LLM — voice.md per account for different tones
- [ ] Image reply — if tweet has media, LLM reads image + generates visual-aware reply
- [ ] Analytics dashboard — track impressions from X native (not API)

---

## ⚖️ Legal & Ethical Notes

**This violates X's Terms of Service** (automation without their API). Risks:
- Permanent account suspension
- Loss of followers & content
- No dispute options if flagged

**Use at your own risk.** The author is not responsible for suspensions or losses.

Use for research/experimentation. Do NOT use for spam, scams, or your main important account.

---

## 🙏 Credits

- Method inspired by [@AchmadBeny](https://facebook.com/) — viral post about Playwright + browser bots for X monetization
- Reply rules adapted from his post + LLM tuning
- Made with ❤️ by [@Faresapn](https://github.com/Faresapn)

---

## 📄 License

MIT — do whatever you want, at your own risk. See [LICENSE](./LICENSE) for full text.

---

## ⭐ If This Helped You

Give it a star on GitHub! And consider trying **[PromptedSite](https://promptedsite.com)** — 500+ AI design prompts for shipping beautiful websites fast.
