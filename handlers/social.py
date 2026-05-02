import re
import random
from datetime import datetime
from aiogram import Router, types, F
from sqlalchemy import select, or_
from database.models import User, Marriage
from config import MAIN_CHAT_ID

router = Router()
pending_marriage = {}

USERNAME_RE = re.compile(r"@([A-Za-z0-9_]+)")
PREDICTIONS = [
    "✨ Звезды говорят: шанса много, но будь осторожен.",
    "🌌 Пойди за мечтой, но помни — карта меняется.",
    "🚀 Сейчас лучше подготовиться, а потом действовать.",
    "🛸 Слушай свою интуицию, она тебя не подведет.",
    "🌠 Вероятность успеха велика, если ты не бросишь начатое.",
]


@router.message(F.text.startswith("брак"))
async def propose_marriage(message: types.Message, bot, session):
    if message.from_user is None:
        return
    user = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar_one_or_none()
    if user is None:
        await message.answer("✨ Сначала начни со мной беседу, и я внесу тебя в базу.")
        return
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target_id = message.reply_to_message.from_user.id
        target = session.execute(select(User).where(User.tg_id == target_id)).scalar_one_or_none()
    else:
        match = USERNAME_RE.search(message.text or "")
        if match:
            username = match.group(1)
            try:
                member = await bot.get_chat_member(message.chat.id, username)
                target_id = member.user.id
                target = session.execute(select(User).where(User.tg_id == target_id)).scalar_one_or_none()
            except Exception:
                target = None

    if not target:
        await message.answer("✨ Не могу найти партнера. Укажи упоминание или ответь на сообщение.")
        return
    if target.tg_id == message.from_user.id:
        await message.answer("✨ Сам с собой не вступишь в брак, хоть Орион и креативен.")
        return
    already = session.execute(
        select(Marriage).where(
            or_(
                (Marriage.user1_id == user.id) & (Marriage.user2_id == target.id),
                (Marriage.user1_id == target.id) & (Marriage.user2_id == user.id),
            )
        )
    ).scalar_one_or_none()
    if already:
        await message.answer("✨ Вы уже связаны узами брака.")
        return
    if target.id in pending_marriage:
        await message.answer("✨ У этого игрока уже есть предложение. Подожди ответ.")
        return

    pending_marriage[target.id] = user.id
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Принять", callback_data=f"marriage_accept:{user.id}:{target.id}"),
            types.InlineKeyboardButton(text="❌ Отказать", callback_data=f"marriage_decline:{user.id}:{target.id}"),
        ]
    ])
    await message.answer(
        f"🌌 Слышь, {target.full_name or target.username}, тут {user.full_name or user.username} кольцо достал. Что скажешь? Только не тяни, я жду свадьбу!",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("marriage_accept:"))
async def accept_marriage(query: types.CallbackQuery, session):
    _, proposer_id, target_id = query.data.split(":")
    proposer = session.execute(select(User).where(User.id == int(proposer_id))).scalar_one_or_none()
    target = session.execute(select(User).where(User.id == int(target_id))).scalar_one_or_none()
    if not proposer or not target or int(target_id) not in pending_marriage:
        await query.answer("Предложение устарело.", show_alert=True)
        return
    marriage = Marriage(user1_id=proposer.id, user2_id=target.id, wedding_date=datetime.utcnow())
    session.add(marriage)
    session.commit()
    pending_marriage.pop(int(target_id), None)
    await query.message.edit_text("✨ Ура! В Орионе новая семья. Горько! (Хотя я не знаю, что это значит, но звучит празднично).")
    await query.answer("Поздравляю с свадьбой! Орион благословляет вас.", show_alert=True)


@router.callback_query(F.data.startswith("marriage_decline:"))
async def decline_marriage(query: types.CallbackQuery, session):
    _, proposer_id, target_id = query.data.split(":")
    pending_marriage.pop(int(target_id), None)
    await query.message.edit_text("✨ Предложение отклонено. Не переживай, где-то уже ждут другого героя.")
    await query.answer("Отказ принят.", show_alert=True)


@router.message(F.text.lower().contains("орион отправить"))
async def anonymous_send(message: types.Message):
    if message.chat.type != "private":
        await message.answer("✨ Используй эту команду в личке, чтобы отправить послание в основной чат.")
        return
    if MAIN_CHAT_ID is None:
        await message.answer("✨ В конфиге не задан MAIN_CHAT_ID, я не знаю, куда отправлять письмо.")
        return
    text = message.text or ""
    payload = text.lower().replace("орион отправить", "", 1).strip()
    if not payload:
        await message.answer("✨ Напиши: Орион отправить [текст].")
        return
    await message.bot.send_message(MAIN_CHAT_ID, f"🌌 <b>Послание из пустоты:</b> {payload}")
    await message.answer("✨ Твое послание отправлено в основной чат.")


@router.message(F.text.lower().contains("стоит ли") & F.text.lower().contains("орион"))
async def orion_prediction(message: types.Message):
    await message.answer(random.choice(PREDICTIONS))
