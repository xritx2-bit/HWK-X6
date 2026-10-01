import asyncio
import aiohttp
from config import config
from freefire_client import FreeFireMockClient
from guild_tracker import GuildTracker
from discord_embeds import (
    build_status_change_embed,
    build_member_joined_embed,
    build_invite_sent_embed
)
from webhook_runner import send_embed_via_webhook

async def main():
    webhook_url = config.DISCORD_WEBHOOK_URL
    if not webhook_url:
        print("No webhook URL configured.")
        return

    print(f"Sending live demo alerts to your Discord Webhook...")
    tracker = GuildTracker()
    client = FreeFireMockClient(guild_id=config.FF_GUILD_ID)

    async with aiohttp.ClientSession() as session:
        for step in range(1, 6):
            snapshot = await client.get_guild_snapshot(config.FF_GUILD_ID)
            status_events, joined_events, left_events, invite_events = tracker.process_snapshot(snapshot)

            for event in status_events:
                embed = build_status_change_embed(event)
                await send_embed_via_webhook(session, webhook_url, embed.to_dict())
                await asyncio.sleep(1)

            for event in invite_events:
                embed = build_invite_sent_embed(event)
                await send_embed_via_webhook(session, webhook_url, embed.to_dict())
                await asyncio.sleep(1)

            for event in joined_events:
                embed = build_member_joined_embed(event)
                await send_embed_via_webhook(session, webhook_url, embed.to_dict())
                await asyncio.sleep(1)

    print("Demo alerts successfully sent to your Discord channel!")

if __name__ == "__main__":
    asyncio.run(main())
