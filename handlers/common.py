from datetime import datetime, timedelta
import random
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from sqlalchemy import select
from database.models import User, Pet

router = Router()

RANK_TITLES = [
    (1, "Новичок"),
    (2, "Странник"),
    (5, "Исследователь"),
    (10, "Мастер"),
    (15, "Легенда"),
    (20, "Космический Страж"),
]

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🐾 Магазин питомцев"), KeyboardButton(text="🐾 Мой питомец")],
        [KeyboardButton(text="бонус"), KeyboardButton(text="топ")],
        [KeyboardButton(text="профиль"), KeyboardButton(text="📔 Обучение")],
        [KeyboardButton(text="🌐 Наш сайт"), KeyboardButton(text="❌ Скрыть панель")],
    ],
    resize_keyboard=True,
)


def choose_title(level: int) -> str:
    title = "Новичок"
    for threshold, name in RANK_TITLES:
        if level >= threshold:
            title = name
    return title


def progress_bar(current: int, maximum: int = 100) -> str:
    filled = int((current / maximum) * 10)
    return "🟩" * filled + "⬜" * (10 - filled)

ORION_PREDICTIONS = [
    "✨ Звезды говорят: шанса много, но будь осторожен.",
    "🌌 Пойди за мечтой, но помни — карта меняется.",
    "🚀 Сейчас лучше подготовиться, а потом действовать.",
    "🛸 Слушай свою интуицию, она тебя не подведет.",
    "🌠 Вероятность успеха велика, если ты не бросишь начатое.",
]


async def get_or_create_user(session, tg_user) -> User:
    stmt = select(User).where(User.tg_id == tg_user.id)
    result = session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        user = User(
            tg_id=tg_user.id,
            username=tg_user.username or "",
            full_name=" ".join(filter(None, [tg_user.first_name, tg_user.last_name])),
            balance=1000,
            xp=0,
            level=1,
            title="Новичок",
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.message(F.text.lower().contains("орион") & ~F.text.startswith("/") & ~F.text.startswith("Орион титул") & ~F.text.startswith("орион отправить") & ~F.text.startswith("орион титул") & ~F.text.startswith("титул"))
async def orion_answer(message: Message):
    text = message.text or ""
    lowered = text.lower()
    if "стоит ли" in lowered:
        import random
        await message.answer(random.choice(ORION_PREDICTIONS))
        return
    await message.answer("✨ Я здесь, Орион слушает. Спрашивай или нажимай кнопки в меню.")


@router.message(F.text & ~F.text.startswith("/"))
async def ensure_user(message: Message, session):
    if message.from_user is None or message.from_user.is_bot:
        return

    user = await get_or_create_user(session, message.from_user)
    if not user.last_message_at:
        user.last_message_at = datetime.utcnow() - timedelta(seconds=61)

    if (datetime.utcnow() - user.last_message_at) >= timedelta(seconds=30):
        user.xp += 1
        if user.xp >= user.level * 100:
            user.xp = 0
            user.level += 1
            user.title = choose_title(user.level)
            await message.answer(
                f"✨ <b>Уровень повышен!</b> {user.full_name or message.from_user.first_name}, теперь ты <b>{user.title}</b> уровня {user.level}.")
        user.last_message_at = datetime.utcnow()
        session.add(user)
        session.commit()
    elif user.last_message_at is None:
        user.last_message_at = datetime.utcnow()
        session.add(user)
        session.commit()


@router.message(Command("menu"))
async def show_menu(message: Message):
    await message.answer("✨ Главное меню Ориона", reply_markup=MAIN_MENU)


@router.message(F.text == "🌐 Наш сайт")
async def website(message: Message):
    await message.answer("🌐 Админ-панель Ориона: http://localhost:8000/admin\n(Доступ только для владельца)")


@router.message((F.text == "📔 Обучение") | Command("help"))
async def help_message(message: Message):
    await message.answer(
        "🌌 <b>Обучение Ориона</b>\n"
        "• Напиши `бонус` — получить ежедневные монеты.\n"
        "• `🐾 Магазин питомцев` — купить питомца.\n"
        "• `🐾 Мой питомец` — посмотреть и покормить питомца.\n"
        "• `топ` — открыть рейтинг.\n"
        "• `брак @username` или ответом — предложение.\n"
        "• `варн`, `бан`, `мут` — модерация.\n"
        "• `Орион отправить [текст]` — анонимное сообщение в основной чат.\n"
        "• `Орион титул [текст]` — смена титула за 5000 монет.\n"
        "• `погода <город>` — погода RPG-стилем.")


@router.message(F.text.startswith("титул") | F.text.startswith("Орион титул") | F.text.startswith("орион титул"))
async def change_title(message: Message, session):
    user = await get_or_create_user(session, message.from_user)
    text = message.text or ""
    for prefix in ["Орион титул", "орион титул", "титул"]:
        if text.lower().startswith(prefix):
            new_title = text[len(prefix):].strip()
            break
    else:
        new_title = ""
    if not new_title:
        await message.answer("✨ Напиши: Орион титул [текст]. Стоимость — 5000 монет.")
        return
    if user.balance < 5000:
        await message.answer("✨ Тебе нужно 5000 монет, чтобы сменить титул.")
        return
    user.balance -= 5000
    user.title = new_title
    session.add(user)
    session.commit()
    await message.answer(f"✨ Твой титул обновлен. Теперь ты — <b>{user.title}</b>.")


@router.message((F.text == "профиль") | Command("profile"))
async def profile(message: Message, session):
    user = await get_or_create_user(session, message.from_user)
    pet = session.execute(select(Pet).where(Pet.owner_id == user.id)).scalar_one_or_none()
    status = "Активен" if user.last_message_at and (datetime.utcnow() - user.last_message_at) < timedelta(hours=1) else "Спит"
    pet_line = f"🐾 Питомец: {pet.name} ({pet.pet_type})\n" if pet else "🐾 Питомец: нет\n"
    xp_bar = progress_bar(user.xp, user.level * 100)
    text = (
        f"🌌 <b>Профиль Ориона</b>\n"
        f"👤 <b>{user.full_name or user.username or 'Игрок'}</b>\n"
        f"🏷️ Титул: <b>{user.title}</b>\n"
        f"⭐ Уровень: <b>{user.level}</b> | XP: <b>{user.xp}/{user.level * 100}</b> {xp_bar}\n"
        f"💰 Баланс: <b>{user.balance}</b> монет\n"
        f"⚠️ Варны: <b>{user.warns_count}/3</b>\n"
        f"📡 Статус: <b>{status}</b>\n"
        f"{pet_line}"
        f"✨ Чтобы купить питомца — нажми «🐾 Магазин питомцев».")
    await message.answer(text)


@router.message(F.text == "бонус")
async def daily_bonus(message: Message, session):
    user = await get_or_create_user(session, message.from_user)
    now = datetime.utcnow()
    if user.last_bonus_date and user.last_bonus_date.date() == now.date():
        await message.answer("🌌 Бонус уже получен сегодня. Приходи завтра за новым даром космоса.")
        return

    base = random.randint(50, 200)
    bonus = base
    has_pet = session.execute(select(Pet).where(Pet.owner_id == user.id)).scalar_one_or_none()
    if has_pet:
        bonus = int(base * 1.2)
    user.balance += bonus
    user.last_bonus_date = now
    session.add(user)
    session.commit()
    await message.answer(
        f"✨ Деньги упали с небес! Ты получил <b>{bonus}</b> монет.")
