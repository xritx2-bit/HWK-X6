import asyncio
import logging
import aiohttp
from config import config
from freefire_client import FreeFireApiClient, FreeFireMockClient, BaseFreeFireClient
from guild_tracker import GuildTracker
from discord_embeds import (
    build_status_change_embed,
    build_member_joined_embed,
    build_member_left_embed,
    build_invite_sent_embed
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("WebhookRunner")

async def send_embed_via_webhook(session: aiohttp.ClientSession, webhook_url: str, embed_dict: dict):
    """Deliver a rich Discord embed to a Discord Webhook URL via direct HTTP POST."""
    payload = {
        "username": "Free Fire Guild Monitor",
        "avatar_url": "https://play-lh.googleusercontent.com/47s91mYk6v8gQeC6g61CqjB6l0Vz8oY1w8zC5n0c7c0b0a8e=s256",
        "embeds": [embed_dict]
    }
    try:
        async with session.post(webhook_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status in (200, 204):
                logger.info("Discord Webhook notification sent successfully.")
            elif resp.status == 429:
                retry_after = (await resp.json()).get("retry_after", 2.0)
                logger.warning(f"Rate limited by Discord. Waiting {retry_after}s...")
                await asyncio.sleep(retry_after)
                await session.post(webhook_url, json=payload)
            else:
                text = await resp.text()
                logger.error(f"Failed to post to Discord Webhook: HTTP {resp.status} - {text}")
    except Exception as e:
        logger.error(f"Exception posting to Discord Webhook: {e}")

async def run_webhook_monitor():
    webhook_url = config.DISCORD_WEBHOOK_URL.strip()
    if not webhook_url:
        print("\n" + "=" * 65)
        print(" [!] ACTION REQUIRED: DISCORD WEBHOOK URL MISSING")
        print("=" * 65)
        print(" 1. In your Discord server, go to Channel Settings -> Integrations -> Webhooks")
        print(" 2. Click 'New Webhook', name it 'Free Fire Guild Monitor', and copy the URL.")
        print(" 3. Paste the URL into your .env file:")
        print("    DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        print("=" * 65 + "\n")
        return

    # Choose between Live API Gateway or Mock Mode
    client: BaseFreeFireClient
    if config.MOCK_MODE or not config.FF_API_GATEWAY_URL:
        logger.info("Running in SIMULATION MODE (Testing Webhook alerts).")
        client = FreeFireMockClient(guild_id=config.FF_GUILD_ID or "772183921")
    else:
        logger.info(f"Connecting to Free Fire API Gateway at: {config.FF_API_GATEWAY_URL}")
        client = FreeFireApiClient(
            gateway_url=config.FF_API_GATEWAY_URL,
            access_token=config.FF_ACCESS_TOKEN,
            account_uid=config.FF_BOT_UID,
            region=config.FF_REGION,
            api_key=config.FF_API_KEY,
            user_uid=config.FF_USER_UID
        )

    tracker = GuildTracker()
    guild_id = config.FF_GUILD_ID or "772183921"

    print("\n" + "=" * 65)
    print(f"  FREE FIRE GUILD MONITOR (WEBHOOK MODE)")
    print(f"  Target Guild ID: {guild_id}")
    print(f"  Poll Interval  : {config.POLL_INTERVAL_SECONDS} seconds")
    print(f"  Mode           : {'SIMULATION' if config.MOCK_MODE else 'LIVE GATEWAY'}")
    print("=" * 65 + "\n")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                snapshot = await client.get_guild_snapshot(guild_id)
                if snapshot:
                    status_events, joined_events, left_events, invite_events = tracker.process_snapshot(snapshot)

                    # 1. Status changes (Playing CS, BR, Lobby, Offline)
                    for event in status_events:
                        embed = build_status_change_embed(event)
                        await send_embed_via_webhook(session, webhook_url, embed.to_dict())
                        await asyncio.sleep(1)

                    # 2. Member Joined & Approvals
                    for event in joined_events:
                        embed = build_member_joined_embed(event)
                        await send_embed_via_webhook(session, webhook_url, embed.to_dict())
                        await asyncio.sleep(1)

                    # 3. Member Left / Kicked
                    for event in left_events:
                        embed = build_member_left_embed(event)
                        await send_embed_via_webhook(session, webhook_url, embed.to_dict())
                        await asyncio.sleep(1)

                    # 4. Guild Invites Sent
                    for event in invite_events:
                        embed = build_invite_sent_embed(event)
                        await send_embed_via_webhook(session, webhook_url, embed.to_dict())
                        await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Error in monitor loop: {e}", exc_info=True)

            await asyncio.sleep(config.POLL_INTERVAL_SECONDS)

if __name__ == "__main__":
    asyncio.run(run_webhook_monitor())
