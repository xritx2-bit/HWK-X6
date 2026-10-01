import asyncio
from freefire_client import FreeFireMockClient
from guild_tracker import GuildTracker
from discord_embeds import (
    build_status_change_embed,
    build_member_joined_embed,
    build_invite_sent_embed
)

async def test_simulation_pipeline():
    print("=" * 60)
    print("  FREE FIRE GUILD MONITOR - VERIFICATION & SIMULATION TEST")
    print("=" * 60)

    tracker = GuildTracker()
    client = FreeFireMockClient(guild_id="772183921")

    # Run 5 simulated polling steps
    for step in range(1, 6):
        print(f"\n--- [Cycle #{step}] Fetching Guild Snapshot ---")
        snapshot = await client.get_guild_snapshot("772183921")
        assert snapshot is not None, "Snapshot failed!"

        status_events, joined_events, left_events, invite_events = tracker.process_snapshot(snapshot)

        if step == 1:
            print(f"✓ Cycle 1 Initialized known roster with {len(snapshot.members)} members. (0 alerts, as expected)")
            assert len(status_events) == 0 and len(joined_events) == 0, "Initial cycle should not emit alerts"

        if status_events:
            for ev in status_events:
                embed = build_status_change_embed(ev)
                print(f"  [DISCORD ALERT] Status Change: {ev.member.nickname} -> {ev.new_state.value} (Mode: {ev.member.game_mode})")
                print(f"    Embed Title: {embed.title}")
                print(f"    Embed Color: {hex(embed.color.value)}")

        if invite_events:
            for ev in invite_events:
                embed = build_invite_sent_embed(ev)
                print(f"  [DISCORD ALERT] Guild Invite: {ev.inviter_name} (UID: {ev.inviter_uid}) invited UID {ev.target_uid}")
                print(f"    Embed Title: {embed.title}")

        if joined_events:
            for ev in joined_events:
                embed = build_member_joined_embed(ev)
                print(f"  [DISCORD ALERT] Member Joined: {ev.nickname} (UID: {ev.uid})")
                print(f"    Approved By: {ev.approved_by_name} (UID: {ev.approved_by_uid})")
                print(f"    Embed Title: {embed.title}")

        if left_events:
            for ev in left_events:
                print(f"  [DISCORD ALERT] Member Left: {ev.nickname} (UID: {ev.uid})")

    print("\n" + "=" * 60)
    print("✓ ALL SIMULATED EVENTS SUCCESSFULLY GENERATED AND VALIDATED!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_simulation_pipeline())
