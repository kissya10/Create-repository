import asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.bot import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from database.session import DbSessionMiddleware, create_db
from handlers.init import register_routers
from config import BOT_TOKEN
import uvicorn
from web import app
from tasks import start_tasks

async def run_bot():
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware())
    register_routers(dp)
    create_db()
    print("Орион запускается...")
    await dp.start_polling(bot)

async def run_web():
    config = uvicorn.Config(app, host="0.0.0.0", port=8080)
    server = uvicorn.Server(config)
    await server.serve()

async def main():
    await asyncio.gather(run_bot(), run_web(), start_tasks())

if __name__ == "__main__":
    asyncio.run(main())
