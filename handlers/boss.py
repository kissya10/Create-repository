import random
from datetime import datetime, timedelta
from aiogram import Router, types, F
from sqlalchemy import select
from database.models import User

router = Router()

boss_state = {
    "hp": 2000,
    "max_hp": 2000,
    "phase": 1,
    "last_reset": datetime.utcnow(),
    "participants": set(),
    "phase_hp": [2000, 1500, 1000, 500],  # HP для каждой фазы
}


def boss_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(text="⚔️ Атаковать", callback_data="boss_attack"))
    return kb


async def reset_boss():
    boss_state["hp"] = 2000
    boss_state["max_hp"] = 2000
    boss_state["phase"] = 1
    boss_state["last_reset"] = datetime.utcnow()
    boss_state["participants"].clear()


def get_phase_description(phase: int) -> str:
    descriptions = {
        1: "🌌 Босс в первой фазе: обычные атаки.",
        2: "🔥 Босс в огне! Урон увеличен.",
        3: "⚡ Босс электризует! Быстрые атаки.",
        4: "💀 Финальная фаза! Максимальная мощь!",
    }
    return descriptions.get(phase, "Неизвестная фаза")


@router.message((F.text == "босс") | (F.text == "враг"))
async def boss_status(message: types.Message):
    if datetime.utcnow() - boss_state["last_reset"] >= timedelta(hours=24):
        await reset_boss()
    phase_desc = get_phase_description(boss_state["phase"])
    await message.answer(
        f"✨ <b>Мировой босс — Фаза {boss_state['phase']}</b>\n"
        f"{phase_desc}\n"
        f"HP: <b>{boss_state['hp']}/{boss_state['max_hp']}</b>\n"
        f"Нажми «⚔️ Атаковать», чтобы помочь чату.",
        reply_markup=boss_keyboard(),
    )


@router.callback_query(F.data == "boss_attack")
async def boss_attack(query: types.CallbackQuery, session):
    if datetime.utcnow() - boss_state["last_reset"] >= timedelta(hours=24):
        await reset_boss()
    damage = random.randint(10, 50)
    if boss_state["phase"] == 2:
        damage = int(damage * 1.2)
    elif boss_state["phase"] == 3:
        damage = int(damage * 1.5)
    elif boss_state["phase"] == 4:
        damage = int(damage * 2.0)
    boss_state["hp"] = max(0, boss_state["hp"] - damage)
    boss_state["participants"].add(query.from_user.id)

    # Проверка перехода фазы
    if boss_state["hp"] <= boss_state["phase_hp"][boss_state["phase"] - 1] and boss_state["phase"] < 4:
        boss_state["phase"] += 1
        await query.message.edit_text(
            f"✨ Босс переходит в фазу {boss_state['phase']}!\n"
            f"{get_phase_description(boss_state['phase'])}\n"
            f"HP: <b>{boss_state['hp']}/{boss_state['max_hp']}</b>",
            reply_markup=boss_keyboard(),
        )
        await query.answer(f"Фаза {boss_state['phase']} началась!", show_alert=True)
        return

    if boss_state["hp"] <= 0:
        members = list(boss_state["participants"])
        reward = 100 * boss_state["phase"]  # Больше награда за более высокие фазы
        for tg_id in members:
            user = session.execute(select(User).where(User.tg_id == tg_id)).scalar_one_or_none()
            if user:
                user.balance += reward
                session.add(user)
        session.commit()
        text = (
            f"✨ Босс повержен в фазе {boss_state['phase']}! Все участники получили по <b>{reward}</b> монет.\n"
            f"Готов новый бой через 24 часа!"
        )
        await reset_boss()
        await query.message.edit_text(text)
        await query.answer("Босс повержен!", show_alert=True)
        return
    await query.message.edit_text(
        f"✨ Фаза {boss_state['phase']}: {get_phase_description(boss_state['phase'])}\n"
        f"HP: <b>{boss_state['hp']}/{boss_state['max_hp']}</b>",
        reply_markup=boss_keyboard(),
    )
    await query.answer(f"Ты нанес {damage} урона.", show_alert=True)
