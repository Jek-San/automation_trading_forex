# src/core/telegram_handler.py
import asyncio
from pathlib import Path
from telethon import TelegramClient, events

from src.utils.logger import get_logger

from src.core.db.telegram_msg import record_telegram_message


class TelegramHandler:
    def __init__(self, api_id: str, api_hash: str, phone: str):
        self.api_id = api_id
        self.api_hash = api_hash
        self.phone = phone
        self.client: TelegramClient | None = None
        self.running = False
        self.paused = False
        self.should_reconnect = True
        self.logger = get_logger("core.telegram")

    async def start(self):
        """Main loop to connect and keep listening to Telegram."""
        # Use unique session file per account
        session_path = Path("sessions")
        session_path.mkdir(exist_ok=True)
        session_file = session_path / f"{self.phone}.session"

        self.client = TelegramClient(session_file, self.api_id, self.api_hash)

        # Register message handler ONCE (outside reconnect loop)
        self.client.add_event_handler(self._handle_message_event, events.NewMessage)

        while self.should_reconnect:
            try:
                self.logger.info("🚀 Connecting Telegram client...")
                await self.client.start(phone=self.phone)
                self.running = True
                self.logger.info("✅ Telegram client connected and listening.")
                await self.client.run_until_disconnected()
            except Exception as e:
                self.logger.error(f"❌ Telegram crashed: {e}")
                if not self.should_reconnect:
                    break
                self.logger.info("🔁 Attempting to reconnect in 10s...")
                await asyncio.sleep(10)
            finally:
                if not self.should_reconnect:
                    self.logger.info("🛑 Telegram listener permanently stopped.")
                    break

    async def _handle_message_event(self, event):
        """Internal wrapper for new messages."""
        try:
            self.logger.info("📩 New message received.")
            await self._handle_message(event)
        except Exception as e:
            self.logger.error(f"⚠️ Error handling message: {e}")

    async def _handle_message(self, event):
        """Process each incoming Telegram message."""
        if self.paused:
            self.logger.info("⏸️ Message ignored (paused mode).")
            return

        if not event.message or not event.message.text:
            self.logger.info("📷 Non-text message ignored.")
            return

        text = event.message.text.strip()
        sender = await event.get_sender()
        sender_username = sender.username or "unknown"

        self.logger.info(f"📩 Message from @{sender_username}: {text[:100]!r}")
        # record the message to db
        message = {
        'message_id': event.message.id,
        'sender_id': event.sender_id,
        'sender_username': sender_username,  # Add sender username here
        'text': event.message.text,
        'timestamp': event.message.date.isoformat(),  # Convert datetime to ISO format for JSON
        }
        record_telegram_message(**message)

        # Import here to avoid circular dependencies
        from src.core.telegram.signal_parser_manager import parse_signal_and_save
        await parse_signal_and_save(sender_username, text)

    async def stop(self):
        """Disconnect gracefully."""
        self.should_reconnect = False
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        self.running = False
        self.logger.info("🛑 Telegram listener stopped.")

    def pause(self):
        self.paused = True
        self.logger.info("⏸️ Telegram paused.")

    def resume(self):
        self.paused = False
        self.logger.info("▶️ Telegram resumed.")

    def get_status(self):
        return {
            "running": self.running,
            "paused": self.paused,
            "reconnect_enabled": self.should_reconnect,
        }
