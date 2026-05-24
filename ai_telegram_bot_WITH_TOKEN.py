#!/usr/bin/env python3
"""
🤖 Professional AI Business Telegram Bot
Powered by Claude API (Anthropic)
"""

import asyncio
import json
import logging
import os
import re
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from anthropic import Anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  Установите: pip install anthropic")

try:
    from telegram import (Bot, InlineKeyboardButton, InlineKeyboardMarkup,
                          Update)
    from telegram.ext import (Application, CallbackQueryHandler,
                              CommandHandler, ContextTypes, MessageHandler,
                              filters)
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️  Установите: pip install python-telegram-bot")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN",
    "8914072806:AAH2XGYGbVAZsh0O-vAV4DrlelybQnDMzPo"
)

ANTHROPIC_API_KEY = os.getenv(
    "ANTHROPIC_API_KEY",
    ""
)

ADMIN_IDS = [int(aid.strip()) for aid in os.getenv(
    "ADMIN_IDS", "").split(",") if aid.strip()]


class IntentType(Enum):
    GENERAL = "general"
    ORDER = "order"
    SUPPORT = "support"
    INFO = "info"
    PRODUCT = "product"
    PAYMENT = "payment"
    DELIVERY = "delivery"
    COMPLAINT = "complaint"


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"


class TicketStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class Order:
    order_id: str
    user_id: int
    description: str
    items: List[str] = field(default_factory=list)
    total_price: float = 0.0
    status: OrderStatus = OrderStatus.PENDING
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def to_dict(self):
        data = asdict(self)
        data['status'] = self.status.value
        return data

    def update_status(self, new_status: OrderStatus):
        self.status = new_status
        self.updated_at = datetime.now().isoformat()


@dataclass
class SupportTicket:
    ticket_id: str
    user_id: int
    issue: str
    priority: TicketPriority = TicketPriority.MEDIUM
    status: TicketStatus = TicketStatus.OPEN
    category: str = "general"
    messages: List[Dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = datetime.now().isoformat()

    def to_dict(self):
        data = asdict(self)
        data['priority'] = self.priority.value
        data['status'] = self.status.value
        return data

    def add_message(self, role: str, content: str):
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.updated_at = datetime.now().isoformat()

    def update_status(self, new_status: TicketStatus):
        self.status = new_status
        self.updated_at = datetime.now().isoformat()


@dataclass
class UserProfile:
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    total_orders: int = 0
    total_spent: float = 0.0
    created_at: str = ""
    last_active: str = ""
    preferences: Dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        self.update_activity()

    def update_activity(self):
        self.last_active = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)


class ProfessionalAIAgent:
    INTENT_KEYWORDS = {
        IntentType.ORDER: [
            "заказ", "купить", "заказать", "бронь", "бронировать",
            "товар", "продукт", "хочу", "нужен", "могу ли я"
        ],
        IntentType.PRODUCT: [
            "характеристики", "описание", "цена", "стоимость", "сколько стоит",
            "есть ли", "наличие", "доступно", "в наличии"
        ],
        IntentType.PAYMENT: [
            "оплата", "платёж", "оплатить", "карта", "счёт",
            "способ оплаты", "принимаете", "через что"
        ],
        IntentType.DELIVERY: [
            "доставка", "доставить", "отправка", "пошлина", "когда приедет",
            "адрес", "где получить", "в какой город"
        ],
        IntentType.SUPPORT: [
            "помощь", "проблема", "ошибка", "не работает", "баг",
            "support", "поддержка", "помогите", "сбой", "ошибка"
        ],
        IntentType.COMPLAINT: [
            "жалоба", "недовольны", "плохо", "ужасно", "разочарован",
            "вернуть", "деньги", "компенсация", "возврат"
        ],
        IntentType.INFO: [
            "информация", "подробнее", "расскажи", "объясни",
            "как это работает", "что это"
        ],
    }

    SYSTEM_PROMPTS = {
        IntentType.GENERAL: """Ты - профессиональный AI ассистент компании.
Помогай пользователям дружелюбно и эффективно.
Всегда отвечай на русском языке.
Будь вежлив и профессионален.
Если не знаешь - предложи помощь специалиста.""",

        IntentType.ORDER: """Ты - менеджер по продажам.
Помогай оформлять заказы.
Уточняй детали заказа (количество, характеристики).
Предлагай похожие товары.
Решай любые вопросы по заказам.
На русском языке, профессионально.""",

        IntentType.SUPPORT: """Ты - специалист поддержки.
Помогай решать проблемы быстро и эффективно.
Спрашивай детали проблемы.
Предлагай решения.
Если не можешь решить - предложи встречу со специалистом.
На русском, вежливо и профессионально.""",

        IntentType.PRODUCT: """Ты - консультант по товарам.
Подробно описывай товары.
Сравнивай характеристики.
Даёшь советы по выбору.
Указываешь цены и наличие.
На русском, информативно.""",

        IntentType.COMPLAINT: """Ты - менеджер по работе с жалобами.
Слушай жалобы внимательно.
Предлагай решение проблемы.
Предлагай компенсацию если нужно.
Решай конфликты мирно.
На русском, с сочувствием.""",

        IntentType.INFO: """Ты - информационный консультант.
Даёшь полную информацию.
Объясняешь просто и понятно.
Приводишь примеры.
Помогаешь разобраться.
На русском, доступно.""",

        IntentType.PAYMENT: """Ты - специалист по платежам.
Объясняешь способы оплаты.
Помогаешь выбрать удобный способ.
Решаешь проблемы с платежами.
На русском, профессионально.""",

        IntentType.DELIVERY: """Ты - специалист по доставке.
Объясняешь варианты доставки.
Даёшь сроки и стоимость доставки.
Помогаешь с адресом.
На русском, точно.""",
    }

    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.api_key = ANTHROPIC_API_KEY
        self.admin_ids = ADMIN_IDS

        if ANTHROPIC_AVAILABLE and self.api_key:
            try:
                self.client = Anthropic(api_key=self.api_key)
                logger.info("✅ Claude API initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Claude API: {e}")
                self.client = None
        else:
            logger.warning("⚠️  Claude API key not configured")
            self.client = None

        if TELEGRAM_AVAILABLE and self.bot_token:
            try:
                self.bot = Bot(token=self.bot_token)
                logger.info("✅ Telegram Bot initialized successfully")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Telegram Bot: {e}")
                self.bot = None
        else:
            logger.warning("⚠️  Telegram Bot token not configured")
            self.bot = None

        self.users: Dict[int, UserProfile] = {}
        self.orders: Dict[str, Order] = {}
        self.tickets: Dict[str, SupportTicket] = {}
        self.conversations: Dict[int, List[Dict]] = {}

        self.stats = {
            "total_messages": 0,
            "total_orders": 0,
            "total_tickets": 0,
            "total_users": 0
        }

        logger.info("🚀 Professional AI Agent initialized successfully")
        self._log_status()

    def _log_status(self):
        logger.info(f"🔧 System Status:")
        logger.info(
            f"   Claude API: {'✅ Ready' if self.client else '❌ Not available'}")
        logger.info(
            f"   Telegram Bot: {'✅ Ready' if self.bot else '❌ Not available'}")
        logger.info(
            f"   Admin IDs: {self.admin_ids if self.admin_ids else 'None'}")

    def detect_intent(self, message: str) -> IntentType:
        message_lower = message.lower()
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        return IntentType.GENERAL

    def get_system_prompt(self, intent: IntentType) -> str:
        return self.SYSTEM_PROMPTS.get(
            intent, self.SYSTEM_PROMPTS[IntentType.GENERAL])

    async def process_message(self, user_id: int, message: str) -> str:
        try:
            intent = self.detect_intent(message)
            logger.info(f"👤 User {user_id}: Intent={intent.value}")

            if user_id not in self.users:
                self.users[user_id] = UserProfile(user_id=user_id)
                self.stats["total_users"] += 1
                logger.info(f"✨ New user registered: {user_id}")

            self.users[user_id].update_activity()
            system_prompt = self.get_system_prompt(intent)
            history = self.conversations.get(user_id, [])
            messages = list(history[-10:])
            messages.append({"role": "user", "content": message})

            if not self.client:
                response_text = self._get_fallback_response(intent)
                logger.warning(
                    "⚠️  Using fallback response (Claude API not available)")
            else:
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=messages,
                )
                response_text = response.content[0].text

            if user_id not in self.conversations:
                self.conversations[user_id] = []

            self.conversations[user_id].append(
                {"role": "user", "content": message})
            self.conversations[user_id].append(
                {"role": "assistant", "content": response_text})
            self.conversations[user_id] = self.conversations[user_id][-20:]

            if intent == IntentType.ORDER:
                await self._process_order(user_id, message, response_text)
            elif intent == IntentType.SUPPORT or intent == IntentType.COMPLAINT:
                await self._create_support_ticket(user_id, message, intent)

            self.stats["total_messages"] += 1
            logger.info(f"✅ Message processed successfully for user {user_id}")
            return response_text

        except Exception as e:
            logger.error(f"❌ Error processing message: {e}")
            logger.error(traceback.format_exc())
            return "❌ Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте позже или свяжитесь со специалистом."

    def _get_fallback_response(self, intent: IntentType) -> str:
        responses = {
            IntentType.ORDER: "📦 Спасибо за интерес! Я получил ваш запрос на заказ. Свяжемся с вами в ближайшее время.",
            IntentType.SUPPORT: "🆘 Спасибо за обращение! Создал тикет поддержки. Специалист поможет вам решить проблему.",
            IntentType.PRODUCT: "📋 Спасибо за вопрос! Предоставлю информацию о товаре. Подождите, пожалуйста.",
            IntentType.COMPLAINT: "😔 Спасибо за обратную связь! Приносим извинения за проблему. Разберёмся как можно быстрее.",
            IntentType.GENERAL: "👋 Спасибо за сообщение! Я получил ваш вопрос и помогу вам решить его.",
            IntentType.INFO: "ℹ️  Спасибо за вопрос! Предоставлю вам всю необходимую информацию.",
            IntentType.PAYMENT: "💳 Спасибо за вопрос о платежах! Расскажу о всех способах оплаты.",
            IntentType.DELIVERY: "🚚 Спасибо за вопрос о доставке! Предоставлю информацию о вариантах доставки.",
        }
        return responses.get(intent, responses[IntentType.GENERAL])

    async def _process_order(self, user_id: int, message: str, response: str):
        try:
            order_id = f"ORD-{user_id}-{int(datetime.now().timestamp())}"
            order = Order(
                order_id=order_id,
                user_id=user_id,
                description=message
            )
            self.orders[order_id] = order
            self.stats["total_orders"] += 1
            logger.info(f"✅ Order created: {order_id}")
        except Exception as e:
            logger.error(f"❌ Error creating order: {e}")

    async def _create_support_ticket(
        self, user_id: int, issue: str, intent: IntentType):
        try:
            ticket_id = f"TKT-{user_id}-{int(datetime.now().timestamp())}"
            priority = TicketPriority.HIGH if intent == IntentType.COMPLAINT else TicketPriority.MEDIUM
            ticket = SupportTicket(
                ticket_id=ticket_id,
                user_id=user_id,
                issue=issue,
                priority=priority,
                category="complaint" if intent == IntentType.COMPLAINT else "support"
            )
            ticket.add_message("user", issue)
            self.tickets[ticket_id] = ticket
            self.stats["total_tickets"] += 1
            logger.info(
                f"✅ Support ticket created: {ticket_id} (Priority: {priority.value})")
        except Exception as e:
            logger.error(f"❌ Error creating support ticket: {e}")

    def get_user_stats(self, user_id: int) -> Dict:
        user = self.users.get(user_id)
        if not user:
            return {}
        return {
            "user_id": user_id,
            "total_orders": user.total_orders,
            "total_spent": user.total_spent,
            "created_at": user.created_at,
            "last_active": user.last_active
        }

    def get_system_stats(self) -> Dict:
        return {
            "total_messages": self.stats["total_messages"],
            "total_orders": self.stats["total_orders"],
            "total_tickets": self.stats["total_tickets"],
            "total_users": self.stats["total_users"],
            "orders_data": {k: v.to_dict() for k, v in list(self.orders.items())[-5:]},
            "tickets_data": {k: v.to_dict() for k, v in list(self.tickets.items())[-5:]},
        }


agent = None


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.message.from_user.id
        first_name = update.message.from_user.first_name or "Guest"

        welcome_message = f"""🤖 Добро пожаловать, {first_name}!

Я профессиональный AI ассистент вашей компании.

🎯 Я могу помочь вам с:
✅ Оформлением заказов
✅ Информацией о товарах
✅ Вопросами по доставке и оплате
✅ Решением проблем и жалоб
✅ Ответами на любые вопросы

📞 Просто напиши мне сообщение, и я помогу!

/help - Подробнее о командах
/status - Статус вашего аккаунта"""

        await update.message.reply_text(welcome_message)
        logger.info(f"✅ User {user_id} started bot")
    except Exception as e:
        logger.error(f"❌ Error in start_handler: {e}")


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        help_message = """📖 Доступные команды:

/start - Начать работу
/help - Справка
/status - Мой статус
/stats
