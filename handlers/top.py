from aiogram import Router, types, F
from aiogram.filters import Command
from sqlalchemy import select, func
from database.models import User, Marriage

router = Router()


def medal(rank: int) -> str:
    if rank == 1:
        return "🥇"
    if rank == 2:
        return "🥈"
    if rank == 3:
        return "🥉"
    return "🔹"


async def build_top(category: str, current_user_id: int, session):
    current_user = session.execute(select(User).where(User.tg_id == current_user_id)).scalar_one_or_none()
    if category == "money":
        users = session.execute(select(User).order_by(User.balance.desc()).limit(10)).scalars().all()
        lines = [f"{medal(i+1)} <b>{u.username or u.full_name}</b> — <b>{u.balance}</b> монет" for i, u in enumerate(users)]
        rank = None
        if current_user:
            rank = session.execute(select(func.count()).where(User.balance > current_user.balance)).scalar_one_or_none()
        rank_text = f"Твое место в общем рейтинге: #{rank + 1 if rank is not None else '—'}"
        return "✨ <b>Топ богачей</b>\n" + "\n".join(lines) + "\n" + rank_text
    if category == "level":
        users = session.execute(select(User).order_by(User.level.desc(), User.xp.desc()).limit(10)).scalars().all()
        lines = [f"{medal(i+1)} <b>{u.username or u.full_name}</b> — <b>{u.level}</b> lvl" for i, u in enumerate(users)]
        rank = None
        if current_user:
            rank = session.execute(
                select(func.count()).where(
                    (User.level > current_user.level) |
                    ((User.level == current_user.level) & (User.xp > current_user.xp))
                )
            ).scalar_one_or_none()
        rank_text = f"Твое место в общем рейтинге: #{rank + 1 if rank is not None else '—'}"
        return "✨ <b>Топ легенд</b>\n" + "\n".join(lines) + "\n" + rank_text
    if category == "active":
        users = session.execute(select(User).order_by(User.last_message_at.desc().nullslast()).limit(10)).scalars().all()
        lines = []
        for i, u in enumerate(users):
            status = u.last_message_at.strftime("%H:%M") if u.last_message_at else "нет"
            lines.append(f"{medal(i+1)} <b>{u.username or u.full_name}</b> — <b>{status}</b>")
        rank_text = "Твое место в общем рейтинге: #—"
        return "✨ <b>Топ активности</b>\n" + "\n".join(lines) + "\n" + rank_text
    if category == "marriage":
        marriage_counts = session.execute(
            select(User, func.count(Marriage.id).label("count"))
            .join(Marriage, (User.id == Marriage.user1_id) | (User.id == Marriage.user2_id))
            .group_by(User.id)
            .order_by(func.count(Marriage.id).desc())
            .limit(10)
        ).all()
        lines = [f"{medal(i+1)} <b>{row[0].username or row[0].full_name}</b> — <b>{row[1]}</b> пар" for i, row in enumerate(marriage_counts)]
        rank_text = "Твое место в общем рейтинге: #—"
        return "✨ <b>Топ пар</b>\n" + "\n".join(lines) + "\n" + rank_text
    return ""


def build_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=2)
    kb.add(
        types.InlineKeyboardButton(text="💰 Богачи", callback_data="top_money"),
        types.InlineKeyboardButton(text="⚔️ Уровень", callback_data="top_level"),
    )
    kb.add(
        types.InlineKeyboardButton(text="💍 Пары", callback_data="top_marriage"),
        types.InlineKeyboardButton(text="📊 Актив", callback_data="top_active"),
    )
    return kb


@router.message((F.text == "топ") | Command("top"))
async def top_command(message: types.Message, session):
    text = await build_top("money", message.from_user.id, session)
    await message.answer(text, reply_markup=build_keyboard())


@router.callback_query(F.data.startswith("top_"))
async def top_callback(query: types.CallbackQuery, session):
    category = query.data.split("_", 1)[1]
    text = await build_top(category, query.from_user.id, session)
    await query.message.edit_text(text, reply_markup=build_keyboard())
    await query.answer()
