"""
llm_writer.py — Claude Sonnet generator utk reply/quote/post di X.
Rules diadaptasi dari post Beny: casual English, react ke content, 10-50 kata.
"""
from __future__ import annotations
import os
from anthropic import Anthropic

# Pake key & base_url yang lo udah punya (9router → cc/claude-sonnet-5)
BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:20128/v1")
API_KEY = os.getenv("LLM_API_KEY", os.getenv("HERMES_CUSTOM_BANDELBANGET_XYZ_API_KEY", ""))
MODEL = os.getenv("LLM_MODEL", "cc/claude-sonnet-5")

_client = Anthropic(base_url=BASE_URL, api_key=API_KEY) if API_KEY else None


REPLY_RULES = """Your job:
1. Look at the tweet carefully and understand what it's actually saying
2. Write a reply as a real person reacting to THIS specific tweet

REPLY RULES:
- Reply in casual English. Relaxed, like texting someone in a group chat.
- 10 to 50 words. Match length to how much the tweet has going on.
- React to what's actually IN the tweet — the idea, the take, the news, the joke.
- Match the emotion — hype tweet → energy or contrarian. Meme → play along. News → give your take.
- Use 1-2 emojis if they fit the mood. 💀 🥴 😂 🔥 are good. Zero is also fine.
- Lowercase almost always. No hashtags. No @mentions. No period at end.
- Sound like a human, NOT a bot. No generic AI-sounding phrases.
- Output ONLY the reply text. Nothing else."""


REPLY_RULES_CTA = """Your job:
1. Look at the tweet carefully and understand what it's saying
2. Write a reply as a real person, and NATURALLY mention promptedsite.com

REPLY RULES:
- Reply in casual English. Relaxed, like texting in a group chat.
- 10 to 50 words.
- React to what's actually IN the tweet FIRST — dont start with "check out X".
- ONLY mention https://promptedsite.com if it makes sense given the topic:
  * Tweet about design/AI/prompts/shipping → mention it as helpful resource
  * Tweet about pain point (bad design, slow shipping) → mention as solution
  * Tweet unrelated → DONT force the link, output reply WITHOUT link
- Format: react → transition → link. Example:
  "shipped mine last week in 2 hours. found a prompt that killed it for landing pages: https://promptedsite.com"
- 1-2 emojis if they fit. Zero is fine.
- Lowercase mostly. No hashtags. No @mentions. No period at end.
- Sound human. NO "check this out", "you should try", "this is amazing".
- Output ONLY the reply text. Nothing else."""


QUOTE_RULES = """Your job:
1. Look at the tweet and understand its point
2. Write a quote-tweet that adds your own take on it

QUOTE RULES:
- Casual English. Feels like a real hot take, not a summary.
- 15 to 60 words. Punchy first sentence, then the take.
- Don't just restate — add angle, contrast, or extend the idea.
- 1-2 emojis if they fit. Zero is fine.
- Lowercase mostly. No hashtags. No @mentions. No period at end.
- Sound human. Skip AI phrases like "this is fascinating", "wow", "amazing".
- Output ONLY the quote text. Nothing else."""


QUOTE_RULES_CTA = """Your job:
1. Look at the tweet and understand its point
2. Write a quote-tweet with your take, and NATURALLY mention promptedsite.com

QUOTE RULES:
- Casual English. Hot take, not summary.
- 15 to 60 words.
- Give YOUR take first — dont lead with the link.
- ONLY mention https://promptedsite.com if the topic fits:
  * Design / prompts / AI shipping / building → mention as resource
  * Pain point (bad UI, slow work) → mention as solve
  * Off-topic → SKIP link, just write the take
- Format: hot take → context → link on last line
- 1-2 emojis if they fit. Zero is fine.
- Lowercase mostly. No hashtags. No @mentions. No period at end.
- Sound human. NO "amazing tool", "check this out", "you gotta try".
- Output ONLY the quote text. Nothing else."""


POST_RULES = """Your job: Write ONE standalone tweet.

POST RULES:
- Casual English. Sounds like a real observation from a human.
- 10 to 50 words.
- Topic given below. Say something interesting, personal, or contrarian.
- 1-2 emojis if they fit. Zero is fine.
- Lowercase mostly. No hashtags. No @mentions. No period at end.
- No AI-sounding phrases. Sound like a real crypto/tech person.
- Output ONLY the tweet text. Nothing else."""


POST_RULES_CTA = """Your job: Write ONE standalone tweet that ends with promptedsite.com naturally.

POST RULES:
- Casual English. Sounds like a real observation from a human.
- 15 to 55 words (leave room for URL).
- Topic given below. Personal insight → then the tool that helped.
- Format: hook/insight → concrete example → link on last line
- Example: "spent 3 weeks on hero copy that flopped. one prompt shipped better in 30 min. found it here: https://promptedsite.com"
- 1-2 emojis if they fit. Zero is fine.
- Lowercase mostly. No hashtags. No @mentions. No period at end.
- Sound human. NO "amazing site", "you should check", "highly recommend".
- Output ONLY the tweet text. Nothing else."""


def _call_llm(system: str, user: str, max_tokens: int = 300) -> str:
    if not _client:
        raise RuntimeError("LLM client not configured — set LLM_API_KEY env")
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = ""
    for block in resp.content:
        if hasattr(block, "text"):
            text += block.text
    return text.strip().strip('"').strip("'")


def _persona_prefix(persona: str | None) -> str:
    """Prefix persona to any rule set, if provided."""
    if not persona or not persona.strip():
        return ""
    return f"PERSONA (adopt this voice):\n{persona.strip()}\n\n"


def gen_reply(tweet_text: str, author: str = "someone", likes: int = 0, with_cta: bool = False, persona: str | None = None) -> str:
    system = _persona_prefix(persona) + (REPLY_RULES_CTA if with_cta else REPLY_RULES)
    user = f"Tweet by @{author} ({likes} likes):\n\"{tweet_text}\"\n\nWrite the reply."
    return _call_llm(system, user)


def gen_quote(tweet_text: str, author: str = "someone", likes: int = 0, with_cta: bool = False, persona: str | None = None) -> str:
    system = _persona_prefix(persona) + (QUOTE_RULES_CTA if with_cta else QUOTE_RULES)
    user = f"Tweet by @{author} ({likes} likes):\n\"{tweet_text}\"\n\nWrite the quote-tweet."
    return _call_llm(system, user)


def gen_post(topic: str, with_cta: bool = False, persona: str | None = None) -> str:
    system = _persona_prefix(persona) + (POST_RULES_CTA if with_cta else POST_RULES)
    user = f"Topic: {topic}\n\nWrite the tweet."
    return _call_llm(system, user)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python llm_writer.py {reply|quote|post} '<text/topic>'")
        sys.exit(1)
    cmd, text = sys.argv[1], sys.argv[2]
    if cmd == "reply":
        print(gen_reply(text))
    elif cmd == "quote":
        print(gen_quote(text))
    elif cmd == "post":
        print(gen_post(text))
