#!/usr/bin/env python3
"""
AI Telegram Bot using Groq API (free, fast)
"""

import asyncio
import logging
import os
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    import groq

    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False
    print("⚠️  groq не установлена. Установите: pip install groq")

try:
    from telegram import Bot, Update
    from telegram.ext import (Application, CommandHandler, ContextTypes,
                              MessageHandler, filters)

    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️  python-telegram-bot не установлена")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Configuration
TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN", "8914072806:AAH2XGYGbVAZsh0O-vAV4DrlelybQnDMzPo"
)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ADMIN_IDS = os.getenv("ADMIN_IDS", "").split(",")


class IntentType(Enum):
    GENERAL = "general"
    ORDER = "order"
    SUPPORT = "support"
    NOTIFICATION = "notification"
    DATABASE = "database"


@dataclass
class Order:
    order_id: str
    user_id: str
    description: str
    status: str = "pending"
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)


@dataclass
class SupportTicket:
    ticket_id: str
    user_id: str
    issue: str
    priority: str = "medium"
    status: str = "open"
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)


class AdvancedTelegramAgent:
    KEYWORDS = {
        IntentType.ORDER: [
            "заказ",
            "купить",
            "бронь",
            "бронировать",
            "доставка",
            "цена",
            "стоимость",
            "прайс",
            "заказать",
        ],
        IntentType.SUPPORT: [
            "помощь",
            "проблема",
            "ошибка",
            "не работает",
            "баг",
            "support",
            "помогите",
            "сбой",
            "технич",
        ],
        IntentType.NOTIFICATION: ["уведомл", "напомни", "оповести", "отправь", "рассылка"],
        IntentType.DATABASE: [
            "сохрани",
            "запомни",
            "добавь",
            "удали",
            "профиль",
            "данные",
            "информацию",
        ],
    }

    SYSTEM_PROMPTS = {
        IntentType.GENERAL: "Ты - профессиональный AI ассистент. Отвечай на русском языке кратко и по делу. Будь дружелюбным.",
        IntentType.ORDER: "Ты - специалист по продажам. Помогай оформлять заказы. Уточняй детали. На русском.",
        IntentType.SUPPORT: "Ты - специалист поддержки. Помогай решать проблемы. Спрашивай детали. На русском.",
        IntentType.NOTIFICATION: "Ты - диспетчер уведомлений. Создавай короткие уведомления. На русском.",
        IntentType.DATABASE: "Ты - менеджер данных. Сохраняй информацию. Подтверждай действия. На русском.",
    }

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.groq_key = GROQ_API_KEY
        self.admin_ids = [aid.strip() for aid in ADMIN_IDS if aid.strip()]

        if GROQ_AVAILABLE and self.groq_key:
            self.client = groq.Groq(api_key=self.groq_key)
        else:
            self.client = None

        if TELEGRAM_AVAILABLE:
            self.bot = Bot(token=self.bot_token) if self.bot_token else None
        else:
            self.bot = None

        self.orders: Dict[str, Order] = {}
        self.tickets: Dict[str, SupportTicket] = {}
        self.conversation_history: Dict[str, List[Dict]] = {}

        logger.info("🚀 AI Telegram Bot инициализирован (Groq)")
        logger.info(f"   Groq API: {'✅' if self.client else '❌'}")
        logger.info(f"   Telegram Bot: {'✅' if self.bot else '❌'}")

    def detect_intent(self, message: str) -> IntentType:
        message_lower = message.lower()
        for intent, keywords in self.KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        return IntentType.GENERAL

    def get_system_prompt(self, intent: IntentType) -> str:
        return self.SYSTEM_PROMPTS.get(
            intent, self.SYSTEM_PROMPTS[IntentType.GENERAL])

    async def process_message(self, user_id: str, message: str) -> str:
        try:
            intent = self.detect_intent(message)
            logger.info(f"👤 {user_id}: '{message}' -> {intent.value}")

            system_prompt = self.get_system_prompt(intent)

            # Get conversation history
            history = self.conversation_history.get(user_id, [])

            # Build messages list
            messages = [{"role": "system", "content": system_prompt}]
            for msg in history[-10:]:
                messages.append(msg)
            messages.append({"role": "user", "content": message})

            if not self.client:
                answer = self._get_fallback_response(intent)
            else:
                response = self.client.chat.completions.create(
                    model="llama-3.1-70b-versatile",
                    messages=messages,
                    max_tokens=512,
                    temperature=0.7,
                )
                answer = response.choices[0].message.content

            # Save to history
            if user_id not in self.conversation_history:
                self.conversation_history[user_id] = []
            self.conversation_history[user_id].append(
                {"role": "user", "content": message})
            self.conversation_history[user_id].append(
                {"role": "assistant", "content": answer})
            self.conversation_history[user_id] = self.conversation_history[user_id][-20:]

            # Handle special intents
            if intent == IntentType.ORDER:
                await self._process_order(user_id, message)
            elif intent == IntentType.SUPPORT:
                await self._create_ticket(user_id, message)

            return answer

        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return "❌ Произошла ошибка. Попробуйте позже."

    def _get_fallback_response(self, intent: IntentType) -> str:
        responses = {
            IntentType.GENERAL: "Спасибо! Я получил ваше сообщение.",
            IntentType.ORDER: "Заказ принят! Свяжемся с вами.",
            IntentType.SUPPORT: "Тикет создан. Поможем!",
            IntentType.DATABASE: "Информация сохранена.",
            IntentType.NOTIFICATION: "Уведомление отправлено.",
        }
        return responses.get(intent, responses[IntentType.GENERAL])

    async def _process_order(self, user_id: str, message: str):
        order_id = f"ORD-{user_id[-4:]}-{int(datetime.now().timestamp())}"
        self.orders[order_id] = Order(
            order_id=order_id,
            user_id=user_id,
            description=message)
        logger.info(f"✅ Заказ: {order_id}")

    async def _create_ticket(self, user_id: str, issue: str):
        ticket_id = f"TKT-{user_id[-4:]}-{int(datetime.now().timestamp())}"
        self.tickets[ticket_id] = SupportTicket(
            ticket_id=ticket_id, user_id=user_id, issue=issue)
        logger.info(f"✅ Тикет: {ticket_id}")

    async def handle_message(self, update: Update,
                             context: ContextTypes.DEFAULT_TYPE):
        try:
            if not update.message or not update.message.text:
                return
            user_id = str(update.message.from_user.id)
            message_text = update.message.text

            if self.bot:
                await self.bot.send_chat_action(chat_id=update.message.chat_id, action="typing")

            response = await self.process_message(user_id, message_text)

            if update.message:
                await update.message.reply_text(response)
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            if update.message:
                await update.message.reply_text("Error occurred.")

    async def handle_start(self, update: Update,
                           context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text("🤖 Привет! Я AI-ассистент. Напиши мне сообщение.")

    async def handle_help(self, update: Update,
                          context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text("📖 Команды: /start /help /status")

    async def handle_status(self, update: Update,
                            context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text(
                f"📊 Заказов: {len(self.orders)}, Тикетов: {len(self.tickets)}"
            )

    async def run(self):
        if not TELEGRAM_AVAILABLE or not self.bot_token:
            logger.error("❌ Telegram Bot Token не установлен")
            return

        app = Application.builder().token(self.bot_token).build()
        app.add_handler(CommandHandler("start", self.handle_start))
        app.add_handler(CommandHandler("help", self.handle_help))
        app.add_handler(CommandHandler("status", self.handle_status))
        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self.handle_message))

        logger.info("✅ Bot запущен!")
        await app.run_polling()


async def main():
    agent = AdvancedTelegramAgent()
    await agent.run()


if __name__ == "__main__":
    print("\n🤖 AI Telegram Bot (Groq)\n")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
