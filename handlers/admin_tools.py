import re
from datetime import datetime, timedelta
from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import select
from database.models import User
from services.weather import get_weather
from config import SUPERADMIN_ID

router = Router()
USERNAME_RE = re.compile(r"@([A-Za-z0-9_]+)")


def get_mention_user(message: types.Message) -> int | None:
    if message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    match = USERNAME_RE.search(message.text or "")
    if match:
        return match.group(1)
    return None


@router.message(F.text.startswith("варн"))
async def warn(message: types.Message, session):
    if message.chat.type == "private":
        await message.answer("Варн можно выдать только в группе.")
        return
    target = message.reply_to_message and message.reply_to_message.from_user
    if target is None:
        await message.answer("Ответь на сообщение игрока, чтобы выдать варн.")
        return
    user = session.execute(select(User).where(User.tg_id == target.id)).scalar_one_or_none()
    if user is None:
        await message.answer("Игрок не найден в базе.")
        return
    if user.warns_count >= 3:
        await message.answer("Этот игрок уже на пределе.")
        return
    user.warns_count += 1
    session.add(user)
    session.commit()
    if user.warns_count < 3:
        await message.answer(
            f"✨ Внимание, {target.full_name or target.username}! Твоя карма пошатнулась. "
            f"У тебя <b>{user.warns_count}/3</b> предупреждений. Веди себя прилично!"
        )
    else:
        until = datetime.utcnow() + timedelta(hours=24)
        await message.bot.ban_chat_member(message.chat.id, target.id, until_date=until)
        await message.answer(
            f"✨ Терпение лопнуло! {target.full_name or target.username} отправляется в изгнание на 24 часа. "
            "Надеюсь, в черной дыре кормят лучше, чем здесь."
        )
    await message.bot.send_message(SUPERADMIN_ID, f"[WARN] {target.id} получил варн. Сейчас {user.warns_count}/3.")


@router.message(F.text.startswith("разварн"))
async def unwarn(message: types.Message, session):
    target = message.reply_to_message and message.reply_to_message.from_user
    if target is None:
        await message.answer("Ответь на сообщение нарушителя, чтобы снять варн.")
        return
    user = session.execute(select(User).where(User.tg_id == target.id)).scalar_one_or_none()
    if user is None:
        await message.answer("Игрок не найден в базе.")
        return
    user.warns_count = max(0, user.warns_count - 1)
    session.add(user)
    session.commit()
    await message.answer(f"✨ Варн снят. У {target.full_name or target.username} теперь {user.warns_count}/3.")
    await message.bot.send_message(SUPERADMIN_ID, f"[UNWARN] {target.id} варн снят. Сейчас {user.warns_count}/3.")


@router.message(Command("settitle"))
async def admin_set_title(message: types.Message, session):
    if message.from_user is None or message.from_user.id != SUPERADMIN_ID:
        await message.answer("✨ Только супер-админ может использовать эту команду.")
        return
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        await message.answer("✨ Использование: /settitle [ID] [текст]")
        return
    try:
        target_id = int(parts[1])
    except ValueError:
        await message.answer("✨ Неверный ID.")
        return
    new_title = parts[2].strip()
    user = session.execute(select(User).where(User.tg_id == target_id)).scalar_one_or_none()
    if user is None:
        await message.answer("✨ Пользователь не найден в базе.")
        return
    user.title = new_title
    session.add(user)
    session.commit()
    await message.answer(f"✨ Титул пользователя {target_id} изменен на <b>{new_title}</b>.")


@router.message(F.text.startswith("бан") | F.text.startswith("кик"))
async def moderate_kick(message: types.Message):
    target = message.reply_to_message and message.reply_to_message.from_user
    if target is None:
        await message.answer("Ответь на сообщение, чтобы выполнить действие.")
        return
    if message.text.startswith("бан"):
        await message.bot.ban_chat_member(message.chat.id, target.id)
        await message.answer(f"✨ {target.full_name or target.username} изгнан из группы в черную дыру.")
        await message.bot.send_message(SUPERADMIN_ID, f"[BAN] {target.id} был забанен.")
    else:
        await message.bot.ban_chat_member(message.chat.id, target.id)
        await message.bot.unban_chat_member(message.chat.id, target.id)
        await message.answer(f"✨ {target.full_name or target.username} был кикнут и вернулся к звездам.")
        await message.bot.send_message(SUPERADMIN_ID, f"[KICK] {target.id} был кикнут.")


@router.message(F.text.startswith("мут"))
async def mute(message: types.Message):
    target = message.reply_to_message and message.reply_to_message.from_user
    if target is None:
        await message.answer("Ответь на сообщение, чтобы замутить пользователя.")
        return
    until = datetime.utcnow() + timedelta(hours=24)
    await message.bot.restrict_chat_member(
        message.chat.id,
        target.id,
        permissions=types.ChatPermissions(can_send_messages=False),
        until_date=until,
    )
    await message.answer(f"✨ {target.full_name or target.username} погружен в тишину кинематографа на 24 часа.")
    await message.bot.send_message(SUPERADMIN_ID, f"[MUTE] {target.id} замучен.")


@router.message(Command("id") | (F.text == "id"))
async def show_id(message: types.Message):
    if message.from_user:
        await message.answer(f"✨ Твой Telegram ID: <b>{message.from_user.id}</b>")


@router.message(Command("time") | (F.text == "time"))
async def show_time(message: types.Message):
    from datetime import timezone
    now = datetime.now(timezone.utc)
    moscow = now.astimezone(timezone(timedelta(hours=3)))
    berlin = now.astimezone(timezone(timedelta(hours=2)))
    await message.answer(
        f"✨ Времена на картах Ориона:\n"
        f"🇷🇺 РФ: <b>{moscow.strftime('%H:%M')}</b>\n"
        f"🇩🇪 Германия: <b>{berlin.strftime('%H:%M')}</b>\n"
        f"🌍 UTC: <b>{now.strftime('%H:%M')}</b>"
    )


@router.message(F.text.startswith("погода"))
async def weather(message: types.Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("✨ Напиши: погода <город>")
        return
    city = parts[1].strip()
    result = await get_weather(city)
    if not result:
        await message.answer("✨ Не удалось получить погоду. Проверь название города или ключ API.")
        return
    await message.answer(
        f"🌌 В {result['city']} сейчас <b>{result['temp']}°C</b>. {result['description']}\n"
        f"✨ Совет: {result['advice']}"
    )
