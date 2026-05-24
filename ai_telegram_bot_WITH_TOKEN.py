#!/usr/bin/env python3
"""
🚀 TELEGRAM BOT WITH GROQ API
Free, Fast, No Payment Required
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List

try:
    from groq import Groq
except ImportError:
    print("❌ groq not installed. Run: pip install groq")
    sys.exit(1)

try:
    from telegram import Bot, Update
    from telegram.ext import (
        Application, CommandHandler, ContextTypes, 
        MessageHandler, filters
    )
except ImportError:
    print("❌ python-telegram-bot not installed. Run: pip install python-telegram-bot")
    sys.exit(1)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8914072806:AAH2XGYGbVAZsh0O-vAV4DrlelybQnDMzPo")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class GroqAIAgent:
    """AI Agent using Groq API (Free & Fast)"""
    
    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)
        self.conversations: Dict[int, List[Dict]] = {}
        self.user_data: Dict[int, Dict] = {}
        logger.info("✅ GroqAIAgent initialized")
        self._test_connection()
    
    def _test_connection(self):
        try:
            logger.info("🔍 Testing Groq API connection...")
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=10
            )
            logger.info("✅ Groq API connection successful!")
        except Exception as e:
            logger.error(f"❌ Groq API error: {e}")
    
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
                    "created": datetime.now().isoformat(),
                    "messages": 0
                }
            
            logger.info(f"📨 [{user_id}] {message[:50]}...")
            
            self.conversations[user_id].append({
                "role": "user",
                "content": message
            })
            
            history = self.conversations[user_id][-10:]
            
            response = self.client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "system", "content": self.get_system_prompt()},
                    *history
                ],
                max_tokens=1024,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content
            
            self.conversations[user_id].append({
                "role": "assistant",
                "content": ai_response
            })
            
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
        return f"""📊 **Твоя статистика:**
💬 Сообщений: {data['messages']}
📅 С: {data['created'][:10]}"""

agent: GroqAIAgent = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    first_name = user.first_name or "Friend"
    
    welcome = f"""🚀 **Добро пожаловать, {first_name}!**

Я - AI помощник, работающий на **Groq** (самый быстрый AI)

**Я помогаю с:**
✅ Заказами и покупками
✅ Вопросами и информацией  
✅ Проблемами и жалобами
✅ Консультациями и советами
✅ Работаю 24/7

**Просто пиши мне!** 📝

/help - команды
/status - статистика
/clear - новый разговор"""
    
    await update.message.reply_text(welcome, parse_mode="Markdown")
    logger.info(f"✅ User {user.id} started")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 **СПРАВКА**

**Команды:**
/start - Начать
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

Пиши сообщение! 👇"""
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    stats = agent.get_stats(user_id)
    await update.message.reply_text(stats, parse_mode="Markdown")

async def clear_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id in agent.conversations:
        agent.conversations[user_id] = []
    
    await update.message.reply_text(
        "✅ **История очищена!**\n\nЧто-нибудь новое? 😊",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_message = update.message.text
    
    try:
        await update.message.chat.send_action("typing")
        
        response = await agent.process_message(user_id, user_message)
        
        if len(response) > 4096:
            for i in range(0, len(response), 4096):
                await update.message.reply_text(response[i:i+4096], parse_mode="Markdown")
        else:
            await update.message.reply_text(response, parse_mode="Markdown")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Ошибка. Попробуй еще раз.")

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
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("clear", clear_chat))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("=" * 50)
    logger.info("🚀 TELEGRAM BOT WITH GROQ API")
    logger.info("=" * 50)
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
