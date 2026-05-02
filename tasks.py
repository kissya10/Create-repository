import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from sqlalchemy import select
from database.session import SessionLocal
from database.models import User
from config import BOT_TOKEN, MAIN_CHAT_ID

bot = Bot(token=BOT_TOKEN)


async def daily_boss_event():
    while True:
        now = datetime.utcnow()
        if now.hour == 12 and now.minute == 0:  # Каждый день в 12:00
            if MAIN_CHAT_ID:
                await bot.send_message(MAIN_CHAT_ID, "🌌 Время рейда! Босс проснулся. Используй 'босс' для атаки!")
        await asyncio.sleep(60)  # Проверять каждую минуту


async def weekly_leaderboard():
    while True:
        now = datetime.utcnow()
        if now.weekday() == 6 and now.hour == 18 and now.minute == 0:  # Воскресенье 18:00
            with SessionLocal() as session:
                top_users = session.execute(select(User).order_by(User.balance.desc()).limit(3)).scalars().all()
                if MAIN_CHAT_ID:
                    text = "🌌 Еженедельный топ!\n" + "\n".join(f"🥇 {u.username or u.full_name}: {u.balance} монет" for u in top_users)
                    await bot.send_message(MAIN_CHAT_ID, text)
        await asyncio.sleep(3600)  # Проверять каждый час


async def start_tasks():
    await asyncio.gather(daily_boss_event(), weekly_leaderboard())
