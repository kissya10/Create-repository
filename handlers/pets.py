import random
from sqlalchemy import select
from aiogram import Router, types, F
from aiogram.filters import Command
from database.models import User, Pet

router = Router()

PET_SHOP = {
    "magic_cat": {"name": "Магический Кот", "price": 500, "pet_type": "Кот"},
    "battle_wolf": {"name": "Боевой Волк", "price": 1500, "pet_type": "Волк"},
    "little_dragon": {"name": "Маленький Дракон", "price": 5000, "pet_type": "Дракон"},
}


def build_shop_keyboard() -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    for key, item in PET_SHOP.items():
        kb.add(types.InlineKeyboardButton(text=f"{item['name']} — {item['price']} монет", callback_data=f"buy_pet:{key}"))
    return kb


def build_pet_keyboard(pet_id: int) -> types.InlineKeyboardMarkup:
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(types.InlineKeyboardButton(text="🍎 Покормить", callback_data=f"feed_pet:{pet_id}"))
    return kb


def format_pet(pet: Pet) -> str:
    bar = "🟩" * (pet.satiety // 10) + "⬜" * (10 - pet.satiety // 10)
    return (
        f"✨ <b>Твой питомец</b>\n"
        f"Имя: <b>{pet.name}</b>\n"
        f"Тип: <b>{pet.pet_type}</b>\n"
        f"Уровень: <b>{pet.level}</b>\n"
        f"Сытость: <b>{pet.satiety}/100</b> {bar}\n"
    )


@router.message(Command("pets"))
async def pets_menu(message: types.Message):
    await message.answer("✨ Магазин питомцев Ориона", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("Выбери питомца:", reply_markup=build_shop_keyboard())


@router.message(F.text == "🐾 Магазин питомцев")
async def pet_shop(message: types.Message):
    await message.answer("✨ Магазин питомцев Ориона", reply_markup=build_shop_keyboard())


@router.message(F.text == "🐾 Мой питомец")
async def my_pet(message: types.Message, session):
    user = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar_one_or_none()
    if user is None:
        await message.answer("🌌 Сначала начни беседу со мной, и я сохраню тебя в базе.")
        return
    pet = session.execute(select(Pet).where(Pet.owner_id == user.id)).scalar_one_or_none()
    if not pet:
        await message.answer("🌌 У тебя пока нет питомца. Зайди в «🐾 Магазин питомцев».")
        return
    await message.answer(format_pet(pet), reply_markup=build_pet_keyboard(pet.id))


@router.callback_query(F.data.startswith("buy_pet:"))
async def buy_pet(query: types.CallbackQuery, session):
    key = query.data.split(":", 1)[1]
    item = PET_SHOP.get(key)
    if not item:
        await query.answer("Ошибка магазина.", show_alert=True)
        return
    user = session.execute(select(User).where(User.tg_id == query.from_user.id)).scalar_one_or_none()
    if user is None:
        await query.answer("Сначала начни диалог со мной.", show_alert=True)
        return
    exists = session.execute(select(Pet).where(Pet.owner_id == user.id)).scalar_one_or_none()
    if exists:
        await query.answer("У тебя уже есть питомец. Покорми его или продай в будущем.", show_alert=True)
        return
    if user.balance < item["price"]:
        await query.answer("У тебя недостаточно монет для этой покупки.", show_alert=True)
        return
    user.balance -= item["price"]
    pet = Pet(owner_id=user.id, name=item["name"], pet_type=item["pet_type"], level=1, satiety=100)
    session.add(pet)
    session.add(user)
    session.commit()
    await query.answer(f"Ого! Теперь у тебя есть {item['name']}. Не забывай его кормить, а то он съест твое золото!", show_alert=True)
    await query.message.edit_text(
        f"✨ Ты купил питомца: <b>{item['name']}</b>\nБаланс: <b>{user.balance}</b> монет",
        reply_markup=build_pet_keyboard(pet.id),
    )


@router.callback_query(F.data.startswith("feed_pet:"))
async def feed_pet(query: types.CallbackQuery, session):
    pet_id = int(query.data.split(":", 1)[1])
    pet = session.execute(select(Pet).where(Pet.id == pet_id)).scalar_one_or_none()
    if not pet:
        await query.answer("Питомец не найден.", show_alert=True)
        return
    user = session.execute(select(User).where(User.id == pet.owner_id)).scalar_one_or_none()
    if user is None:
        await query.answer("Не найден владелец питомца.", show_alert=True)
        return
    if user.balance < 50:
        await query.answer("Не хватает 50 монет для корма.", show_alert=True)
        return
    if pet.satiety >= 100:
        await query.answer("Сытость уже максимальна.", show_alert=True)
        return
    user.balance -= 50
    pet.satiety = min(100, pet.satiety + 20)
    session.add_all([pet, user])
    session.commit()
    await query.answer(f"Ням-ням! {pet.name} доволен. Твоя забота делает меня чуточку счастливее.", show_alert=True)
    await query.message.edit_text(format_pet(pet), reply_markup=build_pet_keyboard(pet.id))
