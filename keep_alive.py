import os
import time
import logging
import aiohttp
from aiohttp import web
from datetime import datetime

logger = logging.getLogger("KeepAlive")

START_TIME = time.time()

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HWK X6 - Free Fire Manager Bot</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; }
        body { background: #0f111a; color: #ffffff; display: flex; align-items: center; justify-content: center; min-height: 100vh; padding: 20px; }
        .card { background: rgba(26, 29, 45, 0.9); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 16px; padding: 36px; max-width: 480px; width: 100%; box-shadow: 0 12px 40px rgba(0, 0, 0, 0.5); backdrop-filter: blur(10px); }
        .badge { display: inline-flex; align-items: center; gap: 8px; background: rgba(46, 204, 113, 0.15); color: #2ecc71; padding: 6px 14px; border-radius: 20px; font-weight: 600; font-size: 14px; margin-bottom: 20px; }
        .dot { width: 8px; height: 8px; background: #2ecc71; border-radius: 50%; box-shadow: 0 0 10px #2ecc71; animation: pulse 2s infinite; }
        @keyframes pulse { 0% { opacity: 1; } 50% { opacity: 0.4; } 100% { opacity: 1; } }
        h1 { font-size: 24px; font-weight: 700; margin-bottom: 8px; }
        p { color: #8f9cae; font-size: 14px; margin-bottom: 24px; }
        .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 24px; }
        .stat-box { background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.05); padding: 14px; border-radius: 10px; }
        .stat-label { font-size: 12px; color: #6e7c91; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
        .stat-value { font-size: 16px; font-weight: 600; color: #ffffff; }
        .footer { font-size: 12px; color: #586576; text-align: center; }
    </style>
</head>
<body>
    <div class="card">
        <div class="badge">
            <div class="dot"></div>
            Online 24/7 on Render
        </div>
        <h1>Free Fire Manager Bot</h1>
        <p>Discord bot actively monitoring Free Fire guild activity & real-time member matches.</p>
        
        <div class="stats">
            <div class="stat-box">
                <div class="stat-label">Discord Server</div>
                <div class="stat-value">HWK X6</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">FF Guild ID</div>
                <div class="stat-value">3008075139</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Service Health</div>
                <div class="stat-value" style="color: #2ecc71;">Operational</div>
            </div>
            <div class="stat-box">
                <div class="stat-label">Bot ID</div>
                <div class="stat-value">15209232058</div>
            </div>
        </div>
        
        <div class="footer">
            Keep-Alive Server Active • Auto-Ping Enabled
        </div>
    </div>
</body>
</html>
"""

async def handle_root(request):
    """Serve the status web page for Render health checks and visitors."""
    return web.Response(text=HTML_TEMPLATE, content_type="text/html")

async def handle_health(request):
    """JSON health endpoint for automated uptime monitors (e.g. UptimeRobot, Cron-job.org)."""
    uptime_seconds = int(time.time() - START_TIME)
    return web.json_response({
        "status": "online",
        "bot": "Free Fire Manager",
        "guild": "HWK X6",
        "ff_guild_id": "3008075139",
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.utcnow().isoformat()
    })

async def start_keep_alive_server(port: int = None):
    """Start the lightweight web server to satisfy Render's Web Service requirements."""
    if port is None:
        port = int(os.getenv("PORT", "10000"))

    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Keep-Alive HTTP server running on http://0.0.0.0:{port}")
    return runner

async def self_ping_task():
    """
    Render spins down free web services after 15 minutes of inactivity.
    This background task pings the service every 10 minutes to keep it awake 24/7.
    """
    url = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("PING_URL")
    if not url:
        logger.info("RENDER_EXTERNAL_URL not yet detected. Auto-ping will activate once deployed on Render.")
        return

    url = url.rstrip("/") + "/health"
    logger.info(f"Auto-ping keep-alive loop enabled for: {url}")
    
    async with aiohttp.ClientSession() as session:
        while True:
            await asyncio.sleep(600)  # Ping every 10 minutes (600 seconds)
            try:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    logger.info(f"Render keep-alive ping successful (Status: {resp.status})")
            except Exception as e:
                logger.warning(f"Render keep-alive ping attempt: {e}")
