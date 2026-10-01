# Free Fire Guild Monitor Discord Bot

An automated Discord bot that monitors Garena Free Fire guilds:
- 🎮 **Real-time Member Activity**: Tracks when members start playing (Battle Royale, Clash Squad, Lone Wolf, Custom Rooms) or return to the lobby.
- 📥 **Join & Approval Tracking**: Detects when new members join and logs **who approved them** through the approval queue.
- ✉️ **Invite Tracking**: Logs when guild members send invitations to their friends along with their UIDs.
- 📊 **Discord Embeds**: Clean, color-coded Discord embeds for every guild event.

---

## ⚠️ Important Technical & Safety Notice

### 1. Can Free Fire be monitored using only a UID?
**No.** A Free Fire UID (User ID) is a public number. Unauthenticated requests to Garena servers can only read public profile stats (Level, Likes, Nickname, Badges). 

Private guild data—such as **who is currently in a match**, **guild approval queues**, **who accepted an invite**, and **internal activity logs**—is strictly protected on Garena's game servers. It can only be seen by an **authenticated account session** that is a member (or Officer/Leader) inside that specific guild.

### 2. Account Safety Warning (Ban Prevention)
> **NEVER use your main Free Fire account's login credentials or tokens for automated bots!**
> 
> Garena's anti-cheat systems actively monitor unusual client activity and automated requests. If you connect your main account to an automated script, **your main account risks a permanent ban.**
> 
> **The Safe Standard Approach:**
> 1. Create a fresh **Alt / Dummy Account** (Guest or secondary Google/Facebook account).
> 2. Invite this alt account into your guild.
> 3. Grant this alt account the **Officer** or **Elder** role so it has permission to view the guild member status, approval list, and activity log.
> 4. Use this alt account's session token for the bot. If Garena ever restricts the session, your main account remains 100% safe.

---

## Architecture Overview

```
[ Free Fire Game Servers ]
           ▲
           │ Encrypted Protobuf / Gateway API
           ▼
[ FreeFireApiClient / Alt Session ]
           │
           ▼
   [ GuildTracker ]  <-- Compares state snapshots (In Match, Lobby, Approvals, Invites)
           │
           ▼
   [ Discord Bot / Webhook ]
           │
           ▼
[ Discord Server (#guild-logs) ]
```

---

## Quick Start & Verification

### Step 1: Install Dependencies
Create a Python virtual environment and install the required packages:

```bash
cd "/home/ritesh/Documents/FF BOT"
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Run the Simulation Test (No credentials required!)
To verify the tracking and Discord embed formatting immediately:

```bash
python3 test_bot.py
```

This runs a 5-step simulation validating:
- Member status transitions (`In Match (CS-Ranked)`, `In Match (BR-Ranked)`, `Online (Lobby)`).
- Friend invitations (`Hunter_007` invited UID `99887766`).
- Guild approvals (`亗_SHADOW_亗` approved `SniperGod_Op`).

---

## How to Deliver Logs to Discord

### Option A: Discord Webhook (Simplest & Recommended)
No need to register a bot on the Developer Portal or set up tokens:
1. Open your Discord server.
2. Go to your target channel settings (e.g., `#guild-logs`) -> **Integrations** -> **Webhooks**.
3. Click **New Webhook**, name it `Free Fire Guild Monitor`, and click **Copy Webhook URL**.
4. In your `.env` file, set:
   ```env
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook/url
   ```
5. Run the webhook monitor:
   ```bash
   python3 webhook_runner.py
   ```

### Option B: Full Discord Bot
If you want slash commands like `!status` and `!playing`:
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, give it a name (e.g. `Free Fire Guild Tracker`).
3. Under the **Bot** tab:
   - Click **Reset Token** and copy your **Bot Token**.
   - Enable **Message Content Intent** under Privileged Gateway Intents.
4. Under **OAuth2 -> URL Generator**:
   - Check `bot` and `applications.commands`.
   - Permissions: Check `Send Messages`, `Embed Links`, `Read Message History`.
   - Copy the generated URL and invite the bot to your Discord server.
5. In your Discord server:
   - Create a dedicated channel (e.g., `#guild-activity-logs`).
   - Enable Developer Mode in Discord Settings, right-click the channel, and click **Copy Channel ID**.
6. Paste the Token and Channel ID into your `.env` file:
   ```env
   DISCORD_BOT_TOKEN=your_token_here
   DISCORD_CHANNEL_ID=your_channel_id_here
   ```

---

## Connecting Live Free Fire Data

Once your Discord bot is ready, you can switch from `MOCK_MODE=true` to live mode in `.env`:

1. Set `MOCK_MODE=false`.
2. Configure your Guild ID:
   ```env
   FF_GUILD_ID=123456789
   FF_REGION=IND
   ```
3. Set your alt account credentials or point to your Free Fire API gateway:
   ```env
   FF_BOT_UID=your_alt_uid
   FF_ACCESS_TOKEN=your_alt_session_token
   FF_API_GATEWAY_URL=http://localhost:8080
   ```

### Slash Commands in Discord
- `/setup_channels` - Automatically creates dedicated channels (`#🎮・playing-status`, `#✉・guild-invites`, `#📥・guild-joins`, `#📤・guild-leaves`).
- `/set_channel` - Set a custom channel for playing, invites, joins, or leaves.
- `/channels` - View current channel configuration.
- `/track_player <uid>` - Check player profile and what guild they currently belong to.
- `/status` - Displays guild member count, online, in-match, and offline summary.
- `/playing` - Lists all guild members currently in match with their game mode.

---

## 🚀 How to Host 24/7 on Render (Free Tier)

Render puts free web services to sleep after 15 minutes of inactivity. This bot comes with a built-in **Keep-Alive Web Server** and **Self-Ping loop** to stay online 24/7 for free!

### 1. Deploy on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) and click **New +** ➔ **Web Service**.
2. Select your repository: **`xritx2-bit/HWK-X6`**.
3. Set the following settings:
   - **Name:** `hwk-x6-bot`
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python discord_bot.py`
   - **Instance Type:** `Free`
4. Under **Environment Variables**, add:
   - `DISCORD_BOT_TOKEN`: `your_discord_bot_token`
   - `DISCORD_CHANNEL_ID`: `1544672536661590046`
   - `FF_GUILD_ID`: `3008075139`
   - `FF_BOT_UID`: `15209232058`
   - `FF_REGION`: `IND`
   - `MOCK_MODE`: `true`
5. Click **Deploy Web Service**.

### 2. Keep It Awake 24/7 (Prevent Render Sleeping)
Once deployed, Render gives you a free URL (e.g., `https://hwk-x6-bot.onrender.com`).

* **Built-in Auto-Ping:** The bot automatically pings itself every 10 minutes to stay awake.
* **External Free Pinger (Recommended Backup):**
  1. Go to [UptimeRobot.com](https://uptimerobot.com) (free forever).
  2. Click **Add New Monitor**.
  3. **Monitor Type:** `HTTP(s)`
  4. **Friendly Name:** `HWK X6 Bot`
  5. **URL:** `https://your-app-name.onrender.com/health`
  6. **Monitoring Interval:** `5 minutes`
  7. Click **Create Monitor**.

UptimeRobot will send an HTTP ping every 5 minutes, ensuring Render **never spins down or goes to sleep**!

