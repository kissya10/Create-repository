import random
from aiogram import Router, types, F
from sqlalchemy import select
from database.models import User

router = Router()

WORDS = [
    "космос", "звезда", "планета", "ракета", "галактика", "астероид", "комета", "спутник",
    "телескоп", "орбита", "метеорит", "луна", "солнце", "марс", "венера", "юпитер",
    "сатурн", "уран", "нептун", "плутон", "андромеда", "млечный", "путь", "черная",
    "дыра", "квазар", "пульсар", "нейтронная", "звезда", "сверхновая", "красный",
    "гигант", "белый", "карлик", "черный", "карлик", "коричневый", "карлик",
]

active_games = {}


def mask_word(word: str) -> str:
    return " ".join("_" if i % 2 == 0 else letter for i, letter in enumerate(word))


def reveal_letter(word: str, mask: str, letter: str) -> str:
    new_mask = list(mask.replace(" ", ""))
    for i, char in enumerate(word):
        if char.lower() == letter.lower():
            new_mask[i] = char
    return " ".join(new_mask)


@router.message(F.text.startswith("угадай"))
async def start_word_game(message: types.Message, session):
    if message.from_user is None:
        return
    user = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar_one_or_none()
    if user is None:
        await message.answer("✨ Сначала начни со мной беседу.")
        return
    if user.balance < 50:
        await message.answer("✨ Нужно минимум 50 монет для игры.")
        return
    word = random.choice(WORDS)
    mask = mask_word(word)
    game_id = f"word_{message.from_user.id}"
    active_games[game_id] = {
        "word": word,
        "mask": mask,
        "attempts": 5,
        "reveals": 0,
    }
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton(text="🔍 Открыть букву", callback_data=f"reveal_{game_id}"),
        types.InlineKeyboardButton(text="💡 Подсказка", callback_data=f"hint_{game_id}"),
    )
    await message.answer(
        f"✨ Угадай слово! Ставка: 50 монет.\n"
        f"Слово: <b>{mask}</b>\n"
        f"Попыток: <b>{active_games[game_id]['attempts']}</b>",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("reveal_"))
async def reveal_letter_callback(query: types.CallbackQuery):
    game_id = query.data.split("_", 1)[1]
    if game_id not in active_games:
        await query.answer("Игра не найдена.", show_alert=True)
        return
    game = active_games[game_id]
    if game["reveals"] >= 3:
        await query.answer("Максимум 3 открытия.", show_alert=True)
        return
    word = game["word"]
    mask_list = game["mask"].split()
    hidden_indices = [i for i, char in enumerate(mask_list) if char == "_"]
    if not hidden_indices:
        await query.answer("Все буквы открыты.", show_alert=True)
        return
    idx = random.choice(hidden_indices)
    mask_list[idx] = word[idx]
    game["mask"] = " ".join(mask_list)
    game["reveals"] += 1
    await query.message.edit_text(
        f"✨ Угадай слово!\n"
        f"Слово: <b>{game['mask']}</b>\n"
        f"Попыток: <b>{game['attempts']}</b>",
        reply_markup=query.message.reply_markup,
    )
    await query.answer("Буква открыта!", show_alert=True)


@router.callback_query(F.data.startswith("hint_"))
async def hint_callback(query: types.CallbackQuery):
    game_id = query.data.split("_", 1)[1]
    if game_id not in active_games:
        await query.answer("Игра не найдена.", show_alert=True)
        return
    game = active_games[game_id]
    word = game["word"]
    hint = f"Это слово связано с космосом. Длина: {len(word)} букв."
    await query.answer(hint, show_alert=True)


@router.message(F.text.startswith("казино") | F.text.startswith("🎰"))
async def casino_game(message: types.Message, session):
    if message.from_user is None:
        return
    user = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar_one_or_none()
    if user is None:
        await message.answer("✨ Сначала начни со мной беседу.")
        return
    if user.balance < 100:
        await message.answer("✨ Нужно минимум 100 монет для казино.")
        return
    user.balance -= 100
    session.add(user)
    session.commit()
    # Имитация dice
    dice_value = random.randint(1, 6)
    if dice_value in [1, 2, 3]:
        reward = 0
        result = "Проигрыш"
    elif dice_value in [4, 5]:
        reward = 200
        result = "Выигрыш!"
    else:
        reward = 500
        result = "Джекпот!"
    user.balance += reward
    session.add(user)
    session.commit()
    await message.answer(
        f"🎰 Казино Ориона!\n"
        f"Ставка: 100 монет\n"
        f"Результат: <b>{result}</b> (🎲 {dice_value})\n"
        f"Выигрыш: <b>{reward}</b> монет\n"
        f"Баланс: <b>{user.balance}</b> монет"
    )
