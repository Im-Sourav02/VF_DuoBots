# VF Duo — two-bot Telegram file store

One process runs two Kurigram clients that share this codebase and the `plugins/` load path:

| Setting prefix | Display name | Username (default) | Role |
| --- | --- | --- | --- |
| `BOT1_*` | Sadie Sink | `@VeloraFileShareRoBot` | Filestore, shortener, **credits** |
| `BOT2_*` | Wanda | `@VFFileBot` | Link protector, **no credits** |

Both clients use Kurigram. Kurigram keeps the `pyrogram` import namespace, so plugin imports stay `from pyrogram import …`. Do not install `pyrofork` or upstream `pyrogram` alongside it (`start.sh` uninstalls them first).

## Bot mapping

Prompt numbering called Sadie Sink “Bot 2” and Wanda “Bot 1”. Deployed wiring is the other way around:

- `.env` labels `BOT1_*` as the filestore (Sadie Sink) and `BOT2_*` as the link protector (Wanda / Scarlet Witch).
- `BOT1_BOT_USERNAME` is the file-delivery bot; `BOT2_BOT_USERNAME` is the deep-link wrapper.
- Runtime: Bot 1 stores files, runs the shortener, and auto-chains a Bot 2 link. Bot 2 only returns that stored Bot 1 URL.
- Credits belong on the filestore/shortener client (`credits_enabled=True` on Bot 1 only). Wanda never awards, spends, or displays a credit balance.

Display names can be overridden with `BOT1_DISPLAY_NAME` / `BOT2_DISPLAY_NAME` without changing routing.

## Credits (Sadie Sink only)

Non-premium users on Bot 1:

1. Open a file/batch deep link (`/start <base64>`).
2. If the shortener is on and they are not premium/owner, Bot 1 tries to **atomically spend 1 credit**.
3. Insufficient balance (or no balance row) → shortener verification screen (`Open Link`, `Tutorial`, `Skip Ads`).
4. A one-time random token is stored in MongoDB, bound to that user and that file payload, with a TTL. The shortened URL is the only copy of `t.me/<bot>?start=v_<token>`. Crafted `v_` parameters and the old `yu3elk…7` marker are not treated as a completed bypass.
5. After the shortener, Bot 1 claims the token (`issued` → `claimed`) for that user, awards **2 credits once** (unique `credit_rewards` ledger), then shows `Click Here` back to the same file link.
6. The file link spend in step 2 then deducts **1 credit** and delivers. Failed delivery refunds the spend. Database errors refuse delivery instead of giving files away.

Premium users and the owner skip ads and neither earn nor spend credits. Wanda (`BOT2_*`) has no credit collections written and no verification tokens.

Replaying a rewarded token does not add credits again. Replaying a token that was claimed but not yet marked rewarded also does not double-award; the verified screen is shown so the user can still open the file.

## UI

Both bots share `helper/ui.py`: photo on top, uppercase section headings, quote/blockquote panels, colored action buttons (Bot API `style` with Kurigram markup fallback). Screens:

- Home — How to Use, Channels, Premium Plans, Close (Settings for admins)
- How to Use — Premium, Owner, Support, Back, Close
- Official network — Back, Close
- Premium — Buy Premium, Back, Close
- Shortener verification (Sadie Sink) — Open Link, Tutorial, Skip Ads, Close
- Verification success (Sadie Sink) — Click Here, Skip Ads, Close

Button destinations (`PREMIUM_LINK`, `OWNER_LINK`, `SUPPORT_LINK`, tutorial URL from shortener settings) are omitted when unset. Per-screen photos are env-overridable (`BOT1_HELP_PHOTO`, `BOT2_START_PHOTO`, …) and fall back to that bot’s start photo.

## Setup

Python 3.10+ (Kurigram requirement). `runtime.txt` is 3.11.9.

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -U pip
pip install -r requirements.txt
cp .env.example .env            # then fill in secrets
python main.py
```

Official Kurigram install is `pip install kurigram` ([PyPI](https://pypi.org/project/Kurigram/), [site](https://kurigram.icu)). This repo pins `kurigram==2.2.26`.

Docker / Heroku use `Dockerfile` + `start.sh`, which force-removes `pyrofork`/`pyrogram` before installing requirements.

### Required environment

| Variable | Purpose |
| --- | --- |
| `API_ID`, `API_HASH` | Telegram API credentials |
| `OWNER_ID` | Owner Telegram user ID |
| `BOT1_TOKEN` | Sadie Sink bot token |
| `BOT1_DB_URI` | MongoDB URI for Bot 1 |
| `BOT1_DB_CHANNEL` | Private channel where Bot 1 stores files (bot must be admin) |

### Strongly recommended

| Variable | Purpose |
| --- | --- |
| `BOT1_BOT_USERNAME` | Used when chaining Bot 2 links from Bot 1 |
| `BOT2_TOKEN`, `BOT2_DB_CHANNEL`, `BOT2_BOT_USERNAME` | Enable Wanda; skip all three to run Bot 1 alone |
| `BOT2_DB_URI`, `BOT2_DB_NAME` | Must be a **different database name** than Bot 1 |
| `SHORT_URL`, `SHORT_API`, `SHORT_TUT` | Shortener used by Sadie Sink (also editable in `/shortner`) |
| `PREMIUM_LINK`, `OWNER_LINK`, `SUPPORT_LINK`, `PREMIUM_PRICE_TEXT` | UI buttons |

See `.env.example` for photo keys and credit TTL knobs. Tokens, MongoDB URIs, and API keys have **no source defaults**.

## Commands (unchanged)

Users: `/start`, `/profile`, `/request` (premium, Sadie Sink).  
Admins: `/batch`, `/genlink`, `/nbatch`, `/shortner` (Sadie Sink), `/broadcast`, `/ban`, `/addpremium`, `/db`, …

Force-sub, auto-delete, custom caption, broadcast, and Bot 1 → Bot 2 link chaining are unchanged. Channel posts on Bot 1 still generate a Bot 1 file link and store it in Bot 2’s DB channel.

## Remaining configuration

1. Fill `.env` from `.env.example`. Older git history still contains credential defaults — **rotate bot tokens, MongoDB passwords, shortener API keys, and Telegram API credentials** if this repo was ever pushed or shared.
2. Confirm Bot 1 is admin in `BOT1_DB_CHANNEL` and Bot 2 is admin in `BOT2_DB_CHANNEL`.
3. Keep `BOT1_DB_NAME` and `BOT2_DB_NAME` distinct.
4. Set screen photos (`BOT1_HELP_PHOTO`, `BOT2_PREMIUM_PHOTO`, …) if you do not want every screen to reuse the start image.
5. Configure the shortener from `/shortner` on Sadie Sink after first boot if MongoDB should override env fallbacks.

## License

GPLv3. Originally derived from [Codeflix Filestore](https://github.com/codeflix-bots/filestore).
