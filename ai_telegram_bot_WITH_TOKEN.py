#!/usr/bin/env python3
"""
╔════════════════════════════════════════════════════════════════════════════╗
║ AI TELEGRAM BOT AGENT - ALL IN ONE                                         ║
║                                                                           ║
║ Полнофункциональный AI агент для Telegram                                 ║
║ Бот: @KivoAppAssistantBot (Личный Ассистент)                             ║
║                                                                           ║
║ • Q&A (вопросы и ответы)                                                  ║
║ • Обработка заказов/бронирования                                         ║
║ • Техническая поддержка (тикеты)                                          ║
║ • Управление базой данных пользователя                                   ║
║ • Автоматические уведомления                                              ║
║ • Контекстный диалог с памятью                                            ║
║                                                                           ║
║ Работает через: GitHub Actions, Docker, Render.com, Railway.app           ║
║ Использует: Claude AI (Anthropic), python-telegram-bot                     ║
║                                                                           ║
║ Автор: AI Assistant (Claude)                                             ║
║ Версия: 1.1 (с токеном @KivoAppAssistantBot)                              ║
║ Дата: 2024                                                               ║
╚════════════════════════════════════════════════════════════════════════════╝
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import traceback

try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False
    print("⚠️  anthropic не установлена. Установите: pip install anthropic")


try:
    from telegram import Update, Bot
    from telegram.ext import Application, MessageHandler, filters, ContextTypes, CommandHandler
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️  python-telegram-bot не установлена. Установите: pip install python-telegram-bot")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8914072806:AAH2XGYGbVAZsh0O-vAV4DrlelybQnDMzPo")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
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
    updated_at: str = None
    amount: Optional[float] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.updated_at is None:
            self.updated_at = datetime.now().isoformat()
    
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
    assigned_to: Optional[str] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)

@dataclass
class UserProfile:
    user_id: str
    first_name: str = ""
    phone: str = ""
    email: str = ""
    data: Dict[str, Any] = None
    created_at: str = None
    last_updated: str = None
    
    def __post_init__(self):
        if self.data is None:
            self.data = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.last_updated is None:
            self.last_updated = datetime.now().isoformat()
    
    def to_dict(self):
        return asdict(self)

class AdvancedTelegramAgent:
    KEYWORDS = {
        IntentType.ORDER: ["заказ", "купить", "бронь", "бронировать", "доставка", "цена", "стоимость", "прайс", "заказать", "зарезервировать"],
        IntentType.SUPPORT: ["помощь", "проблема", "ошибка", "не работает", "баг", "support", "помогите", "сбой", "технич", "поддержк"],
        IntentType.NOTIFICATION: ["уведомл", "напомни", "оповести", "отправь", "send notification", "рассылка", "inform"],
        IntentType.DATABASE: ["сохрани", "запомни", "добавь", "удали", "профиль", "данные", "информацию", "account", "save", "delete"]
    }
    
    SYSTEM_PROMPTS = {
        IntentType.GENERAL: "Ты - профессиональный AI ассистент компании Kivo App. Отвечай на русском языке вежливо, информативно и конкретно. Будь дружелюбным и полезным. Если не уверен - честно скажи об этом. Максимум 2-3 предложения.",
        IntentType.ORDER: "Ты - специалист по продажам Kivo App. Помогай оформлять заказы. Всегда уточняй детали. Подтверждай важные детали перед завершением. На русском, 3-4 предложения.",
        IntentType.SUPPORT: "Ты - специалист технической поддержки Kivo App. Помогай решать проблемы. Спрашивай детали. Давай пошаговые инструкции. На русском.",
        IntentType.NOTIFICATION: "Ты - диспетчер уведомлений Kivo App. Создавай четкие уведомления. На русском, 2-3 предложения.",
        IntentType.DATABASE: "Ты - менеджер данных Kivo App. Сохраняй и обновляй информацию. Подтверждай действия. На русском."
    }
    
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.anthropic_key = ANTHROPIC_API_KEY
        self.admin_ids = [aid.strip() for aid in ADMIN_IDS if aid.strip()]
        
        if ANTHROPIC_AVAILABLE and self.anthropic_key:
            self.client = anthropic.Anthropic(api_key=self.anthropic_key)
        else:
            self.client = None
        
        if TELEGRAM_AVAILABLE:
            self.bot = Bot(token=self.bot_token) if self.bot_token else None
        else:
            self.bot = None
        
        self.orders: Dict[str, Order] = {}
        self.tickets: Dict[str, SupportTicket] = {}
        self.users: Dict[str, UserProfile] = {}
        self.notifications_queue: List[Dict] = []
        self.conversation_history: Dict[str, List[Dict]] = {}
        
        logger.info("🚀 AI Telegram Agent инициализирован")
        logger.info(f"   Бот: @KivoAppAssistantBot")
        logger.info(f"   Anthropic API: {'✅' if self.client else '❌'}")
        logger.info(f"   Telegram Bot: {'✅' if self.bot else '❌'}")
    
    def detect_intent(self, message: str) -> IntentType:
        message_lower = message.lower()
        for intent, keywords in self.KEYWORDS.items():
            if any(keyword in message_lower for keyword in keywords):
                return intent
        return IntentType.GENERAL
    
    def get_system_prompt(self, intent: IntentType) -> str:
        return self.SYSTEM_PROMPTS.get(intent, self.SYSTEM_PROMPTS[IntentType.GENERAL])
    
    def get_conversation_history(self, user_id: str) -> List[Dict]:
        if user_id not in self.conversation_history:
            self.conversation_history[user_id] = []
        return self.conversation_history[user_id].copy()
    
    async def process_message(self, user_id: str, message: str) -> str:
        try:
            intent = self.detect_intent(message)
            logger.info(f"👤 {user_id}: '{message}' -> {intent.value}")
            
            history = self.get_conversation_history(user_id)
            system_prompt = self.get_system_prompt(intent)
            
            history.append({"role": "user", "content": message})
            
            if not self.client:
                answer = self._get_fallback_response(intent, message)
            else:
                response = self.client.messages.create(
                    model="claude-opus-4-6",
                    max_tokens=1024,
                    system=system_prompt,
                    messages=history
                )
                answer = response.content[0].text
            
            history.append({"role": "assistant", "content": answer})
            self.conversation_history[user_id] = history[-20:]
            
            if intent == IntentType.ORDER:
                await self._process_order(user_id, message, answer)
            elif intent == IntentType.SUPPORT:
                await self._create_ticket(user_id, message)
            elif intent == IntentType.DATABASE:
                await self._update_profile(user_id, message)
            elif intent == IntentType.NOTIFICATION:
                await self._queue_notification(user_id, answer)
            
            return answer
            
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            logger.error(traceback.format_exc())
            return "❌ Произошла ошибка. Попробуйте позже."
    
    def _get_fallback_response(self, intent: IntentType, message: str) -> str:
        responses = {
            IntentType.GENERAL: "Спасибо за вопрос! Обработать не могу.",
            IntentType.ORDER: "Заказ принят! Свяжемся с вами.",
            IntentType.SUPPORT: "Тикет создан. Разберёмся.",
            IntentType.DATABASE: "Информация сохранена.",
            IntentType.NOTIFICATION: "Уведомление отправлено."
        }
        return responses.get(intent, responses[IntentType.GENERAL])
    
    async def _process_order(self, user_id: str, message: str, response: str):
        order_id = f"ORD-{user_id}-{int(datetime.now().timestamp())}"
        order = Order(order_id=order_id, user_id=user_id, description=message)
        self.orders[order_id] = order
        logger.info(f"✅ Заказ создан: {order_id}")
        await self._notify_admins(f"📦 Новый заказ! ID: {order_id}, Пользователь: {user_id}")
    
    async def _create_ticket(self, user_id: str, issue: str):
        ticket_id = f"TKT-{user_id}-{int(datetime.now().timestamp())}"
        ticket = SupportTicket(ticket_id=ticket_id, user_id=user_id, issue=issue)
        self.tickets[ticket_id] = ticket
        logger.info(f"✅ Тикет создан: {ticket_id}")
        await self._notify_admins(f"🎫 Новый тикет! ID: {ticket_id}, Пользователь: {user_id}")
    
    async def _update_profile(self, user_id: str, data: str):
        if user_id not in self.users:
            self.users[user_id] = UserProfile(user_id=user_id)
        self.users[user_id].data["last_input"] = data
        self.users[user_id].last_updated = datetime.now().isoformat()
        logger.info(f"✅ Профиль {user_id} обновлен")
    
    async def _queue_notification(self, user_id: str, message: str):
        self.notifications_queue.append({"user_id": user_id, "message": message, "timestamp": datetime.now().isoformat(), "sent": False})
    
    async def _notify_admins(self, message: str):
        if not self.bot:
            return
        for admin_id in self.admin_ids:
            if admin_id.strip():
                try:
                    await self.bot.send_message(chat_id=int(admin_id.strip()), text=message)
                except Exception as e:
                    logger.error(f"❌ Ошибка: {e}")
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    
    async def handle_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text("🤖 Добро пожаловать в Kivo App! Напишите мне сообщение.")
    
    async def handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            await update.message.reply_text("📖 Команды: /start /help /status")
    
    async def handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.message:
            stats = self.get_stats()
            await update.message.reply_text(f"📊 Статистика: Заказов: {stats['total_orders']}, Тикетов: {stats['open_tickets']}")
    
    def get_stats(self) -> Dict[str, Any]:
        return {"total_orders": len(self.orders), "open_tickets": len([t for t in self.tickets.values() if t.status == "open"]), "registered_users": len(self.users), "pending_notifications": len([n for n in self.notifications_queue if not n["sent"]]), "timestamp": datetime.now().isoformat()}
    
    async def send_notifications(self):
        if not self.bot:
            return
        for notif in self.notifications_queue:
            if not notif["sent"]:
                try:
                    await self.bot.send_message(chat_id=int(notif["user_id"]), text=notif["message"])
                    notif["sent"] = True
                except Exception as e:
                    logger.error(f"❌ Ошибка: {e}")
    
    async def run(self):
        if not TELEGRAM_AVAILABLE or not self.bot_token:
            logger.error("❌ Telegram Bot Token не установлен")
            return
        app = Application.builder().token(self.bot_token).build()
        app.add_handler(CommandHandler("start", self.handle_start))
        app.add_handler(CommandHandler("help", self.handle_help))
        app.add_handler(CommandHandler("status", self.handle_status))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        app.job_queue.run_repeating(lambda context: asyncio.create_task(self.send_notifications()), interval=30, first=10)
        logger.info("✅ AI Telegram Bot запущен!")
        await app.run_polling()

async def run_standalone():
    agent = AdvancedTelegramAgent()
    print("\n" + "═" * 80 + "\n🤖 STANDALONE MODE\n" + "═" * 80 + "\nВведите 'exit' для выхода\n")
    test_user = "test_user_123"
    while True:
        try:
            user_input = input("👤 Вы: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("\n👋 До свидания!")
                break
            if not user_input:
                continue
            print("\n🤖 Бот печатает...", end="", flush=True)
            response = await agent.process_message(test_user, user_input)
            print(f"\r🤖 Бот: {response}\n")
        except KeyboardInterrupt:
            print("\n👋 До свидания!")
            break
        except Exception as e:
            print(f"\n❌ Ошибка: {e}\n")

async def main():
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "standalone":
        await run_standalone()
    else:
        agent = AdvancedTelegramAgent()
        await agent.run()

if __name__ == "__main__":
    print("\n🤖 AI TELEGRAM BOT v1.1 @KivoAppAssistantBot\n")
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")