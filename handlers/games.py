import random
from aiogram import Router, types, F
from sqlalchemy import select
from database.models import User

router = Router()
active_games = {}
pending_games = {}


def build_board(board, game_key: str):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    for index, cell in enumerate(board):
        text = cell or "⬜"
        keyboard.add(types.InlineKeyboardButton(text=text, callback_data=f"xo_move:{game_key}:{index}"))
    return keyboard


def check_winner(board, mark):
    wins = [
        (0, 1, 2), (3, 4, 5), (6, 7, 8),
        (0, 3, 6), (1, 4, 7), (2, 5, 8),
        (0, 4, 8), (2, 4, 6),
    ]
    return any(all(board[i] == mark for i in combo) for combo in wins)


def render_game_text(state):
    current = state["player_symbols"][state["current"]]
    return (
        f"✨ Крестики-нолики на монеты!\n"
        f"Игрок X: <b>{state['player_names'][0]}</b> vs Игрок O: <b>{state['player_names'][1]}</b>\n"
        f"Ходит: <b>{state['player_names'][state['current']]}</b> ({current})\n"
    )


def format_board(board):
    lines = []
    for i in range(0, 9, 3):
        lines.append(" ".join(cell or "⬜" for cell in board[i:i+3]))
    return "\n".join(lines)


@router.message(F.text.startswith("крестики"))
async def challenge(message: types.Message, session):
    if not message.from_user:
        return
    args = message.text.split()
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    elif len(args) > 1 and args[1].startswith("@"):
        username = args[1][1:]
        try:
            member = await message.bot.get_chat_member(message.chat.id, username)
            target = member.user
        except Exception:
            target = None
    else:
        target = None

    if not target or target.id == message.from_user.id:
        await message.answer("✨ Укажи оппонента через ответ на сообщение или @username.")
        return

    challenger = session.execute(select(User).where(User.tg_id == message.from_user.id)).scalar_one_or_none()
    defender = session.execute(select(User).where(User.tg_id == target.id)).scalar_one_or_none()
    if not challenger or not defender:
        await message.answer("✨ Оба игрока должны быть в базе.")
        return

    if challenger.balance < 100 or defender.balance < 100:
        await message.answer("✨ Оба игрока должны иметь минимум 100 монет для ставки.")
        return

    game_key = f"{message.chat.id}:{challenger.id}:{defender.id}"
    if game_key in active_games or game_key in pending_games:
        await message.answer("✨ Уже есть активная игра между этими игроками.")
        return

    pending_games[game_key] = {
        "chat_id": message.chat.id,
        "challenger_id": challenger.id,
        "defender_id": defender.id,
        "challenger_name": challenger.full_name or challenger.username or "Игрок",
        "defender_name": defender.full_name or defender.username or "Игрок",
        "stake": 100,
    }
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="✅ Принять дуэль", callback_data=f"xo_accept:{game_key}"),
            types.InlineKeyboardButton(text="❌ Отказать", callback_data=f"xo_decline:{game_key}"),
        ]
    ])
    await message.answer(
        f"✨ {pending_games[game_key]['defender_name']}, {pending_games[game_key]['challenger_name']} вызывает тебя в крестики-нолики на 100 монет!",
        reply_markup=keyboard,
    )


@router.callback_query(F.data.startswith("xo_accept:"))
async def accept_game(query: types.CallbackQuery, session):
    _, game_key = query.data.split(":", 1)
    pending = pending_games.pop(game_key, None)
    if not pending:
        await query.answer("Предложение устарело.", show_alert=True)
        return
    if query.from_user.id != session.execute(select(User).where(User.id == pending["defender_id"])).scalar_one_or_none().tg_id:
        await query.answer("Только приглашенный может принять дуэль.", show_alert=True)
        return
    board = [None] * 9
    active_games[game_key] = {
        "board": board,
        "current": 0,
        "player_ids": [pending["challenger_id"], pending["defender_id"]],
        "player_names": [pending["challenger_name"], pending["defender_name"]],
        "player_symbols": ["X", "O"],
        "stake": pending["stake"],
    }
    await query.message.edit_text(render_game_text(active_games[game_key]) + "\n" + format_board(board), reply_markup=build_board(board, game_key))
    await query.answer("Дуэль началась!", show_alert=True)


@router.callback_query(F.data.startswith("xo_decline:"))
async def decline_game(query: types.CallbackQuery):
    _, game_key = query.data.split(":", 1)
    pending_games.pop(game_key, None)
    await query.message.edit_text("✨ Дуэль отклонена. Может в другой раз?")
    await query.answer("Отказано.", show_alert=True)


@router.callback_query(F.data.startswith("xo_move:"))
async def move(query: types.CallbackQuery, session):
    _, game_key, cell = query.data.split(":")
    cell_index = int(cell)
    game = active_games.get(game_key)
    if not game:
        await query.answer("Игра не найдена.", show_alert=True)
        return
    player_ids = game["player_ids"]
    if query.from_user.id != session.execute(select(User).where(User.id == player_ids[game["current"]])).scalar_one_or_none().tg_id:
        await query.answer("Сейчас не твой ход.", show_alert=True)
        return
    if game["board"][cell_index] is not None:
        await query.answer("Клетка занята.", show_alert=True)
        return
    symbol = game["player_symbols"][game["current"]]
    game["board"][cell_index] = symbol

    if check_winner(game["board"], symbol):
        winner_id = player_ids[game["current"]]
        loser_id = player_ids[1 - game["current"]]
        winner = session.execute(select(User).where(User.id == winner_id)).scalar_one_or_none()
        loser = session.execute(select(User).where(User.id == loser_id)).scalar_one_or_none()
        stake = game["stake"]
        winner.balance += stake
        loser.balance -= stake
        session.add_all([winner, loser])
        session.commit()
        active_games.pop(game_key, None)
        await query.message.edit_text(
            f"✨ Дуэль завершена! Победитель: <b>{winner.full_name or winner.username}</b>\n"
            f"Он получает <b>{stake}</b> монет."
        )
        await query.answer("Победа!", show_alert=True)
        return
    if all(cell is not None for cell in game["board"]):
        active_games.pop(game_key, None)
        await query.message.edit_text("✨ Ничья! Монеты возвращены. Наступит следующая дуэль.")
        await query.answer("Ничья.", show_alert=True)
        return
    game["current"] = 1 - game["current"]
    await query.message.edit_text(render_game_text(game) + "\n" + format_board(game["board"]), reply_markup=build_board(game["board"], game_key))
    await query.answer("Ход принят.", show_alert=True)
