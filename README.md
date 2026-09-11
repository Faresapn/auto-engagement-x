# Auto Engagement X

**Playwright-based X (Twitter) auto engagement bot.** Zero X API cost. Uses browser cookies + Claude LLM to post smart replies/quotes/tweets that look human.

Built for accounts where you want organic engagement without paying X API credits ($0.01/write, $0.05/read).

## Fitur utama

- 🌐 **Browser automation** (Playwright) — no X API, no credits
- 🍪 **Cookie import** dari Chrome/browser existing (ga perlu login ulang)
- 🧠 **Claude LLM** (Sonnet/Opus) — reply/quote/post yang natural, casual, ga bot-ish
- 🎯 **3-tier target picker** — fresh > viral > recent (prioritas engagement window)
- 🕒 **Human-like delays** (60-100 menit random antar aksi)
- 📊 **Daily cap** — max N tweet/hari per akun (default 12)
- 🔗 **Smart CTA** — LLM sisipkan link natural (bukan brutal append)
- 📝 **Full transaction log** — tiap post/reply/quote ke-log JSONL
- ⚙️ **Per-account YAML config** — target, mix, delay, CTA rate

---

## Kenapa metode ini?

**X API v2 pricing:**
- Post/reply/quote = **$0.01/tweet** (write credit)
- Search/timeline = **$0.05/request** (read credit) — cepet nguras balance!

**Browser bot = $0 X cost.** Kamu cuma bayar LLM (~$1-3/hari kalau pake Claude Sonnet).

**Trade-off:** rawan suspend kalau ga hati-hati. Best practice:
- Delay panjang (60-100 menit antar aksi)
- Daily cap rendah (12/hari max)
- Cookie dari browser trusted (bukan fresh login)

---

## Prerequisites

- **macOS/Linux** (Playwright didukung penuh)
- **Python 3.9+**
- **Chrome/Brave/Edge** — buat export cookie
- **Extension "Cookie-Editor"** di browser: [Chrome Store link](https://chromewebstore.google.com/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm)
- **LLM API access** — Claude via Anthropic API atau proxy (OpenRouter, 9router, dll)

---

## Setup — Step by Step

### 1. Clone repo & install

```bash
git clone https://github.com/Faresapn/auto-engagement-x.git ~/auto-engagement-x
cd ~/auto-engagement-x

# Setup Python venv
python3 -m venv venv
source venv/bin/activate

# Install deps
pip install --upgrade pip
pip install playwright anthropic pyyaml

# Install Chromium browser (buat Playwright)
python -m playwright install chromium
```

### 2. Set LLM API key

Bot pakai Claude (Anthropic). Set env var:

```bash
# Opsi A: langsung Anthropic
export LLM_API_KEY="sk-ant-xxx"
export LLM_MODEL="claude-sonnet-4-5-20250929"
export LLM_BASE_URL="https://api.anthropic.com/v1"

# Opsi B: via proxy (OpenRouter, 9router, dll)
export LLM_API_KEY="sk-or-xxx"
export LLM_MODEL="anthropic/claude-3.5-sonnet"
export LLM_BASE_URL="https://openrouter.ai/api/v1"
```

Simpan di `~/.zshrc` atau `~/.bashrc` biar persistent. Atau edit `run.sh` (lihat step 5).

### 3. Buat config per akun

Copy template & edit:

```bash
cp config/example.yaml config/<handle>.yaml
```

Edit `config/<handle>.yaml`:

```yaml
handle: yourhandle    # X handle tanpa @

# Target akun buat scrape tweet (yang audiens-nya cocok sama kamu)
targets:
  - shadcn
  - v0
  - rauchg
  # ... tambahin sesuai niche

# 3-TIER target picker
fresh_max_age_min: 60      # T1: tweet umur ≤60 menit
fresh_min_likes: 100

viral_max_age_hours: 6     # T2: tweet umur ≤6 jam
viral_min_likes: 500

recent_max_age_hours: 6    # T3: fallback
recent_min_likes: 20

# Limit & pace
daily_max: 12              # max post/hari
min_delay_sec: 3600        # 60 menit
max_delay_sec: 6000        # 100 menit

# Mix: reply/quote/post (total = 1.0)
mix:
  reply: 0.60
  quote: 0.30
  post: 0.10

# Standalone post topics (dipilih random tiap aksi post)
post_topics:
  - "topic 1"
  - "topic 2"

# CTA (optional)
cta_url: https://yoursite.com
cta_rate: 0.35             # 35% chance CTA disisipkan LLM natural
```

### 4. Import cookie dari browser

**Ga perlu login ulang!** Import cookie session dari Chrome yang udah login.

**a.** Install extension **"Cookie-Editor"** di Chrome (link atas ↑)

**b.** Buka `x.com` di Chrome, pastikan **udah login** di akun target

**c.** Klik icon extension → **Export** → pilih **JSON** → copy/download

**d.** Save ke `~/auto-engagement-x/import/<handle>.json`

Atau kalau ke-copy ke clipboard:
```bash
pbpaste > import/<handle>.json    # macOS
xclip -selection clipboard -o > import/<handle>.json  # Linux
```

**e.** Import ke session Playwright:
```bash
./run.sh import <handle>
```

Bot bakal:
1. Parse cookie
2. Save ke `sessions/<handle>.json` (format Playwright)
3. Buka browser headed → verify masuk ke home timeline
4. Kalau ✅ VALID → siap dipake
5. Kalau ❌ INVALID → re-export cookie (pastikan login di Chrome)

### 5. Test dry-run (ga beneran post)

```bash
./run.sh dry <handle>
```

Bot bakal:
- Pilih random action (reply/quote/post)
- Scan target via Playwright
- Generate teks pake LLM
- **Print `[DRY-RUN] would ...`** — GA post beneran

### 6. Test live 1-shot

Kalau dry-run OK:
```bash
./run.sh test <handle>
```

Ini beneran post 1x. Cek `x.com/<handle>` — muncul tweet baru?

### 7. Production loop

```bash
./run.sh loop <handle>
```

Loop sampai `daily_max`, delay random. Kalau mau background:
```bash
nohup ./run.sh loop <handle> > logs/loop.out 2>&1 &
tail -f logs/loop.out
```

---

## Commands (via `run.sh`)

```bash
./run.sh login <handle>              # Login interactive (backup kalau import gagal)
./run.sh import <handle>             # Import cookie dari import/<handle>.json
./run.sh dry <handle>                # Dry-run 1 aksi (ga post)
./run.sh test <handle>               # Live 1 aksi
./run.sh loop <handle>               # Production loop
./run.sh read <handle> <target>      # Test scrape timeline target
./run.sh status <handle>             # Cek berapa post hari ini
```

---

## 3-Tier Target Picker (yang bikin bot pinter)

Tiap iterasi, bot scan semua target dan klasifikasi tiap tweet:

| Tier | Kriteria | Yang dipilih |
|---|---|---|
| **🔥 T1 FRESH** | age ≤60m + likes ≥100 | Velocity tertinggi (likes/menit) |
| **🚀 T2 VIRAL** | age ≤6h + likes ≥500 | Velocity tertinggi (momentum kuat) |
| **🕐 T3 RECENT** | age ≤6h + likes ≥20 | Paling muda (fallback engagement) |
| **❌ SKIP** | Ga ada match | Tunggu iterasi berikutnya |

**Kenapa ini bagus?**
- **T1**: Reply tweet 30 menit umur, 300 likes, lagi naik → kalau tweet jadi viral, reply lo di top (ratusan ribu impressions)
- **T2**: Kalau ga ada fresh, ambil viral yg masih muda (< 6 jam) & momentum kuat
- **T3**: Kalau kering banget, minimal reply tweet baru biar engagement window masih terbuka

---

## LLM Rules (adapted dari post @beny)

Bot pake system prompt yang enforce:
- Casual English, 10-50 kata
- Lowercase mostly
- No hashtags, no @mentions, no period at end
- 1-2 emoji kalau fit (💀 🥴 😂 🔥)
- **React ke isi tweet** (bukan generic "amazing", "wow")
- Sound HUMAN, bukan AI

**Smart CTA mode** (kalau `cta_rate` > 0):
- LLM decide sisipkan link **organik** — kalau topic match
- Contoh: "shipped mine last week in 2h. found the prompt here: https://site.com"
- Kalau topic ga related, LLM **skip link** (bukan brutal append)

---

## Struktur folder

```
auto-engagement-x/
├── run.sh                     # Main wrapper (activate venv + env)
├── main.py                    # Orchestrator (loop, action picker, sleep)
├── browser_poster.py          # Playwright: login/post/reply/quote/read
├── llm_writer.py              # Claude LLM: gen_reply/quote/post
├── import_cookies.py          # Import Chrome cookies → Playwright session
├── config/
│   ├── example.yaml           # Template config
│   └── <handle>.yaml          # Per-account config
├── sessions/
│   └── <handle>.json          # Playwright storage_state (cookie + localStorage)
├── import/
│   └── <handle>.json          # Chrome-exported cookies (source)
├── state/
│   └── replied-<handle>.log   # Dedup: URL tweet yg udah di-reply
├── logs/
│   └── tx-<handle>.jsonl      # Transaction log (per aksi)
├── venv/                      # Python virtualenv
└── README.md                  # File ini
```

---

## Best practices (biar ga banned)

1. **Delay panjang** — 60+ menit antar aksi. Bot delay lo ke 60-100m default
2. **Daily cap rendah** — 12-15/hari max. Jangan lebih dari 20/hari
3. **Cookie dari browser trusted** — jangan fresh login (kena "temporarily limited")
4. **Tumbal 1 akun dulu** — tes 1-2 minggu, kalau survive baru replicate
5. **Ganti user-agent random** kalau paranoid (edit `browser_poster.py`)
6. **Ga usah post 24/7** — kasih jeda malam/pagi (edit `main.py` add time-of-day check)
7. **Ga usah balas semua tweet** — mix natural, ada yg skip

---

## Troubleshooting

### `session expired for @xxx`

Cookie kadaluarsa. Re-import:
```bash
# 1. Buka Chrome, x.com (pastikan login)
# 2. Cookie-Editor → Export JSON → save ke import/<handle>.json
# 3.
./run.sh import <handle>
```

### `LLM client not configured`

Env `LLM_API_KEY` ga ke-set. Cek:
```bash
echo $LLM_API_KEY   # harus ada
```

Set di `~/.zshrc` atau edit `run.sh` inline.

### `no hot target found`

Semua tier kering. Solusi:
- Turunin `recent_min_likes` (misal dari 20 → 10)
- Tambahin `targets` yang lebih aktif
- Cek `logs/tx-<handle>.jsonl` — mungkin `daily_max` udah kena

### `We've temporarily limited your login` pas login interactive

X detect fresh browser. Solusi: **gunakan cara import cookie** (step 4), jangan login manual.

### Bot ke-suspend

- Cek delay (harus 60+ menit)
- Cek daily_max (jangan >20/hari)
- Cek isi post — kalau spammy, LLM prompt harus di-refine
- Kalau kena, lo cuma bisa: (1) coba unsuspend via appeal X, (2) bikin akun baru

---

## Roadmap / Ideas

- [ ] Scanner terpisah — scan tiap 5-10 menit, queue fresh tweets, main loop pilih dari queue
- [ ] Time-of-day filter — post cuma jam sibuk (misal 9AM-11PM local)
- [ ] Per-target min_likes — akun kecil threshold lebih rendah
- [ ] Multi-persona LLM — voice.md per akun biar tone beda-beda
- [ ] Image reply — kalau tweet ada gambar, LLM baca image + reply visual
- [ ] Analytics dashboard — impression tracking dari X native (bukan API)

---

## Legal & Ethical Notes

**Ini melanggar Terms of Service X** (automation without API). Risk:
- Akun ke-suspend permanen
- Kehilangan follower & konten
- Ga bisa dispute kalau kena flagged

**Tanggung jawab lo sepenuhnya.** Author repo ga bertanggung jawab atas suspend / loss.

Gunakan buat riset / eksperimen. Jangan buat spam, scam, atau akun utama yang penting.

---

## Credits

- Metode terinspirasi dari [@AchmadBeny](https://facebook.com/) — post viral tentang Playwright + browser bot untuk kejar impressions X monetisasi
- Rules reply diadaptasi dari post beliau + LLM tuning
- Made with ❤️ by [@Faresapn](https://github.com/Faresapn)

---

## License

MIT — do whatever you want, at your own risk.
