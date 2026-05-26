#!/usr/bin/env python3
"""
🚀 TELEGRAM BOT WITH GROQ API + PAID STARS
Monthly subscription with Telegram Stars
"""

import asyncio
import logging
import os
import sys
import json
from datetime import datetime, timedelta
from typing import Dict, List

try:
    from groq import Groq
except ImportError:
    print("❌ groq not installed. Run: pip install groq")
    sys.exit(1)

try:
    from telegram import Bot, Update, LabeledPrice, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (Application, CommandHandler, ContextTypes,
                              MessageHandler, filters, PreCheckoutQueryHandler, SuccessfulPaymentHandler)
    from telegram.constants import ParseMode
except ImportError:
    print("❌ python-telegram-bot not installed. Run: pip install python-telegram-bot")
    sys.exit(1)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN",
                           "8914072806:AAH2XGYGbVAZsh0O-vAV4DrlelybQnDMzPo")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# 💰 PAYMENT SETTINGS
SUBSCRIPTION_PRICE_STARS = 75  # 75 stars per month
SUBSCRIPTION_DAYS = 30  # Days of subscription

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class GroqAIAgent:
    """AI Agent using Groq API (Free & Fast)"""

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.conversations: Dict[int, List[Dict]] = {}
        self.user_data: Dict[int, Dict] = {}
        self.subscriptions: Dict[int, Dict] = {}  # User subscriptions
        self._load_subscriptions()
        logger.info("✅ GroqAIAgent initialized")
        self._test_connection()

    def _load_subscriptions(self):
        """Load subscriptions from file"""
        try:
            if os.path.exists("subscriptions.json"):
                with open("subscriptions.json", "r") as f:
                    self.subscriptions = json.load(f)
                    # Convert string keys to int
                    self.subscriptions = {int(k): v for k, v in self.subscriptions.items()}
        except Exception as e:
            logger.error(f"Error loading subscriptions: {e}")

    def _save_subscriptions(self):
        """Save subscriptions to file"""
        try:
            with open("subscriptions.json", "w") as f:
                json.dump(self.subscriptions, f)
        except Exception as e:
            logger.error(f"Error saving subscriptions: {e}")

    def _test_connection(self):
        try:
            logger.info("🔍 Testing Groq API connection...")
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10,
            )
            logger.info("✅ Groq API connection successful!")
        except Exception as e:
            logger.error(f"❌ Groq API error: {e}")

    def is_subscribed(self, user_id: int) -> bool:
        """Check if user has active subscription"""
        if user_id not in self.subscriptions:
            return False
        
        sub_data = self.subscriptions[user_id]
        expires_at = datetime.fromisoformat(sub_data["expires_at"])
        
        if datetime.now() > expires_at:
            del self.subscriptions[user_id]
            self._save_subscriptions()
            return False
        
        return True

    def add_subscription(self, user_id: int, days: int = SUBSCRIPTION_DAYS):
        """Add subscription for user"""
        expires_at = (datetime.now() + timedelta(days=days)).isoformat()
        self.subscriptions[user_id] = {
            "purchased_at": datetime.now().isoformat(),
            "expires_at": expires_at,
            "price_stars": SUBSCRIPTION_PRICE_STARS
        }
        self._save_subscriptions()
        logger.info(f"✅ User {user_id} subscribed until {expires_at}")

    def get_subscription_info(self, user_id: int) -> str:
        """Get subscription info for user"""
        if user_id not in self.subscriptions:
            return "❌ Нет активной подписки"
        
        sub_data = self.subscriptions[user_id]
        expires_at = datetime.fromisoformat(sub_data["expires_at"])
        days_left = (expires_at - datetime.now()).days
        
        return f"""✅ **Активная подписка:**
⭐ Цена: {sub_data['price_stars']} звезд/месяц
📅 Осталось дней: {days_left}
🔚 Истекает: {expires_at.strftime('%d.%m.%Y')}"""

    def get_system_prompt(self) -> str:
        return """Ты - профессиональный AI помощник компании.

ХАРАКТЕРИСТИКИ:
- Говоришь на русском четко и понятно
- Помогаешь с заказами, вопросами, проблемами
- Даешь конкретные ответы, не шаблоны
- Запоминаешь контекст разговора
- Вежлив, внимателен, проактивен

ФУНКЦИИ:
📦 ЗАКАЗЫ - помогу оформить, уточню детали
🆘 ПОДДЕРЖКА - решу проблемы, дам инструкции
📋 ИНФОРМАЦИЯ - расскажу о товарах и услугах
💡 КОНСУЛЬТАЦИЯ - дам советы и рекомендации
😤 ЖАЛОБЫ - слушаю, сочувствую, решаю

СТИЛЬ:
✓ Краткие но полные ответы
✓ Используй эмодзи для наглядности
✓ Всегда предложи помощь в конце
✓ Будь как настоящий человек, не робот

Помогай с любовью! 🤝"""

    async def process_message(self, user_id: int, message: str) -> str:
        try:
            if user_id not in self.conversations:
                self.conversations[user_id] = []
                self.user_data[user_id] = {
                    "created": datetime.now().isoformat(), "messages": 0}

            logger.info(f"📨 [{user_id}] {message[:50]}...")

            self.conversations[user_id].append(
                {"role": "user", "content": message})

            history = self.conversations[user_id][-10:]

            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": self.get_system_prompt()}, *history],
                max_tokens=1024,
                temperature=0.7,
            )

            ai_response = response.choices[0].message.content

            self.conversations[user_id].append(
                {"role": "assistant", "content": ai_response})

            self.user_data[user_id]["messages"] += 1

            logger.info(f"✅ [{user_id}] Responded")

            return ai_response

        except Exception as e:
            logger.error(f"❌ Error: {e}")
            return f"❌ Ошибка: {str(e)[:100]}. Попробуй еще раз."

    def get_stats(self, user_id: int) -> str:
        if user_id not in self.user_data:
            return "📊 Ты только что присоединился!"

        data = self.user_data[user_id]
        sub_info = self.get_subscription_info(user_id)
        return f"""📊 **Твоя статистика:**
💬 Сообщений: {data['messages']}
📅 С: {data['created'][:10]}

{sub_info}"""


agent: GroqAIAgent = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    first_name = user.first_name or "Friend"

    welcome = f"""🚀 **Добро пожаловать, {first_name}!**

Я - AI помощник, работающий на **Groq** (самый быстрый AI)

**💰 ТАРИФЫ:**
⭐ **ПРЕМИУМ** - 75 звезд/месяц
   • Неограниченный доступ на 30 дней
   • AI помощник 24/7
   • Полная поддержка

**Я помогаю с:**
✅ Заказами и покупками
✅ Вопросами и информацией
✅ Проблемами и жалобами
✅ Консультациями и советами

**Команды:**
/buy - Купить премиум подписку
/help - Справка
/status - Статистика и подписка
/clear - Новый разговор

**Нажми /buy чтобы начать!** 👇"""

    await update.message.reply_text(welcome, parse_mode=ParseMode.MARKDOWN)
    logger.info(f"✅ User {user.id} started")


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 **СПРАВКА И ТАРИФЫ**

**💰 ПОДПИСКА:**
⭐ ПРЕМИУМ - 75 звезд/месяц
   • Неограниченный доступ
   • Полная поддержка 24/7
   • Сохранение истории диалогов

**Команды:**
/start - Начать
/buy - Купить подписку
/help - Справка
/status - Статистика
/clear - Очистить историю

**Примеры вопросов:**
- Хочу заказать товар
- Как работает доставка?
- У меня проблема
- Какие скидки?

**Советы:**
💡 Будь конкретен
💡 Я помню контекст
💡 Спрашивай всё что угодно!

Готов помочь! 👇"""

    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


async def buy_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription purchase"""
    user_id = update.message.from_user.id
    
    if agent.is_subscribed(user_id):
        sub_info = agent.get_subscription_info(user_id)
        await update.message.reply_text(
            f"✅ **У тебя уже есть активная подписка!**\n\n{sub_info}",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Create invoice
    title = "Премиум подписка на месяц"
    description = "Неограниченный доступ к AI помощнику на 30 дней"
    payload = "subscription_monthly"
    currency = "XTR"  # Telegram Stars
    price = SUBSCRIPTION_PRICE_STARS

    prices = [LabeledPrice("Премиум подписка", price * 100)]

    await context.bot.send_invoice(
        chat_id=user_id,
        title=title,
        description=description,
        payload=payload,
        currency=currency,
        prices=prices,
        provider_token="",  # No token needed for Telegram Stars
    )

    logger.info(f"💰 Invoice sent to user {user_id}")


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Answer pre-checkout query"""
    query = update.pre_checkout_query
    if query.invoice_payload == "subscription_monthly":
        await query.answer(ok=True)
        logger.info(f"✅ Pre-checkout confirmed for user {query.from_user.id}")
    else:
        await query.answer(ok=False, error_message="Something went wrong...")
        logger.error(f"❌ Pre-checkout failed for user {query.from_user.id}")


async def successful_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle successful payment"""
    user_id = update.message.from_user.id
    payment = update.message.successful_payment
    
    logger.info(f"✅ Payment successful! User {user_id}, Amount: {payment.total_amount} (Telegram Stars)")
    
    # Add subscription
    agent.add_subscription(user_id, SUBSCRIPTION_DAYS)
    
    # Send confirmation
    await update.message.reply_text(
        f"""✅ **Спасибо за покупку!**

🎉 Твоя подписка активирована!
⭐ Сумма: {payment.total_amount} звезд
📅 Срок: {SUBSCRIPTION_DAYS} дней

Теперь ты можешь использовать бота без ограничений!

Просто пиши мне! 💬""",
        parse_mode=ParseMode.MARKDOWN
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    stats = agent.get_stats(user_id)
    
    keyboard = []
    if not agent.is_subscribed(user_id):
        keyboard = [[InlineKeyboardButton("⭐ Купить подписку", callback_data="buy")]]
    
    reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    
    await update.message.reply_text(
        stats,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )


async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in agent.conversations:
        agent.conversations[user_id] = []

    await update.message.reply_text(
        "✅ **История очищена!**\n\nЧто-нибудь новое? 😊", 
        parse_mode=ParseMode.MARKDOWN
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text

    # Check subscription
    if not agent.is_subscribed(user_id):
        keyboard = [[InlineKeyboardButton("⭐ Купить подписку", callback_data="buy")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"""❌ **Подписка не активна!**

Чтобы использовать бота, купи премиум подписку за ⭐ {SUBSCRIPTION_PRICE_STARS} звезд/месяц

**Что включено:**
✅ Неограниченный доступ
✅ AI помощник 24/7
✅ Сохранение истории

Нажми кнопку ниже! 👇""",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=reply_markup
        )
        return

    try:
        await update.message.chat.send_action("typing")

        response = await agent.process_message(user_id, user_message)

        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await update.message.reply_text(response[i: i + 4096], parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text(response, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Ошибка. Попробуй еще раз.")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "buy":
        # Trigger buy_subscription by creating a fake message
        update.message = query.message
        await buy_subscription(update, context)


async def main():
    global agent

    if not GROQ_API_KEY:
        logger.error("❌ GROQ_API_KEY not set!")
        logger.error("Run: export GROQ_API_KEY='your-key'")
        return

    try:
        agent = GroqAIAgent(GROQ_API_KEY)
    except Exception as e:
        logger.error(f"❌ Failed to init: {e}")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Payment handlers
    app.add_handler(CommandHandler("buy", buy_subscription))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(SuccessfulPaymentHandler(successful_payment_callback))

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clear", clear_chat))
    
    # Callback handler for buttons
    app.add_handler(update.CallbackQueryHandler(button_callback))
    
    # Message handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message))

    logger.info("=" * 50)
    logger.info("🚀 TELEGRAM BOT WITH GROQ API + STARS PAYMENT")
    logger.info("=" * 50)
    logger.info(f"💰 Subscription: {SUBSCRIPTION_PRICE_STARS} stars per {SUBSCRIPTION_DAYS} days")
    logger.info("✅ Groq API: Ready")
    logger.info("✅ Telegram: Ready")
    logger.info("✅ Polling: Active")
    logger.info("=" * 50)

    await app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Bot stopped")
    except Exception as e:
        logger.error(f"\n❌ Error: {e}")
