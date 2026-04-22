"""Webhook channel for trader agent - receives messages via HTTP POST."""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

from aiohttp import web
from loguru import logger

from nanobot.bus.events import InboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel


logger = logging.getLogger(__name__)


class WebhookChannel(BaseChannel):
    """Webhook channel that receives messages via HTTP POST and sends replies back.
    
    Usage in config:
        channels:
          trader-webhook:
            enabled: true
            host: 0.0.0.0
            port: 18976
            secret: "your-secret-token"
    """

    name: str = "trader-webhook"
    display_name: str = "Trader Webhook"

    def __init__(self, config: dict[str, Any], bus: MessageBus):
        super().__init__(config, bus)
        self.host = config.get("host", "0.0.0.0")
        self.port = config.get("port", 18976)
        self.secret = config.get("secret", "")
        self.app = web.Application()
        self._setup_routes()
        self._runner: Optional[web.AppRunner] = None

    def _setup_routes(self):
        """Setup webhook routes."""
        self.app.router.add_post("/webhook", self._handle_webhook)
        self.app.router.add_get("/health", self._handle_health)

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """Handle incoming webhook messages."""
        try:
            if self.secret:
                token = request.headers.get("X-Secret-Token", "")
                if token != self.secret:
                    return web.Response(status=401, text="Unauthorized")

            data = await request.json()
            message_text = data.get("message", {}).get("text", "")
            chat_id = str(data.get("message", {}).get("chat", {}).get("id", ""))
            sender_id = str(data.get("message", {}).get("from", {}).get("id", ""))

            if not message_text:
                return web.Response(status=400, text="No message text")

            inbound = InboundMessage(
                channel=self.name,
                sender_id=sender_id,
                chat_id=chat_id,
                content=message_text,
                metadata={"raw": data}
            )
            await self._handle_message(inbound)

            return web.Response(status=200, text=json.dumps({"ok": True}))

        except Exception as exc:
            logger.error(f"Webhook error: {exc}")
            return web.Response(status=500, text=str(exc))

    async def _handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.Response(status=200, text=json.dumps({"status": "ok"}))

    async def start(self) -> None:
        """Start the webhook server."""
        self._runner = web.AppRunner(self.app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self.host, self.port)
        await site.start()
        logger.info(f"Webhook channel started on {self.host}:{self.port}")

    async def stop(self) -> None:
        """Stop the webhook server."""
        if self._runner:
            await self._runner.cleanup()
            logger.info("Webhook channel stopped")
