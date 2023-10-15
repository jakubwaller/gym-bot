import hashlib
import logging
import os
from datetime import datetime

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.ext import (
    CallbackContext,
    CommandHandler,
    ConversationHandler,
)
from telegram.ext import CallbackQueryHandler, ApplicationBuilder

from gymbot.tools import read_config, read_csv, plot_exercises

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

outdir = "logs"

config = read_config(outdir)

df_columns = ["group", "timestamp", "exercise", "kg", "reps"]

developer_chat_id = config["developer_chat_id"]
bot_token = config["bot_token"]
exercises = config["exercises"]

(START, KG, REPS, FERTIG) = range(4)

exercise_tmp = dict()
kg_tmp = dict()
reps_tmp = dict()


async def start(update: Update, context: CallbackContext) -> int:
    await context.bot.send_message(
        update.message.chat.id,
        "Hi there! I’m Gym Bot.\n"
        "I can help you track your gym progress.\n"
        "Send me what exercise with how many kg and reps you did and I'll save it to my database.\n"
        "I can then send you your exercise history with some cool statistics and graphs.\n"
        "And don't worry, your user id is anonymised so I won't know who you are.\n"
        "If you find issues or have any questions, please contact gymbot@jakubwaller.eu\n"
        "Feel free to also check out the code at: https://github.com/jakubwaller/gym-bot",
    )

    return START


async def report(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    logger.info(f"user_id: {user_id}")
    hashed_id = hashlib.md5(bytes(user_id)).hexdigest()
    logger.info(f"hashed: {hashed_id}")

    df = read_csv(outdir, hashed_id, df_columns)

    exercises_list = plot_exercises(df, hashed_id)

    for e in exercises_list:
        await context.bot.send_photo(chat_id, f"{hashed_id}_{e}.png")

    if len(exercises_list) == 0:
        await context.bot.send_message(chat_id, "Nothing to report yet, you lazy laser!")

    return START


async def exercise(update: Update, context: CallbackContext) -> int:
    chat_id = update.message.chat.id

    keyboard = [InlineKeyboardButton(d, callback_data=d) for d in exercises]

    chunk_size = 2
    chunks = [keyboard[x : x + chunk_size] for x in range(0, len(keyboard), chunk_size)]

    reply_markup = InlineKeyboardMarkup(chunks)

    await context.bot.send_message(
        chat_id, "Good job! What exercise did you just do?", reply_markup=reply_markup
    )

    return KG


async def kg(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    logger.info(f"user_id: {user_id}")

    await query.answer()

    exercise_tmp[user_id] = query.data

    await query.edit_message_text(text=f"Selected exercise: {query.data}")

    keyboard = [
        InlineKeyboardButton(str(d), callback_data=str(d)) for d in range(20, 205, 5)
    ]

    chunk_size = 5
    chunks = [keyboard[x : x + chunk_size] for x in range(0, len(keyboard), chunk_size)]

    reply_markup = InlineKeyboardMarkup(chunks)

    await context.bot.send_message(chat_id, "How many kg?", reply_markup=reply_markup)

    return REPS


async def reps(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    logger.info(f"user_id: {user_id}")

    await query.answer()

    kg_tmp[user_id] = query.data

    await query.edit_message_text(text=f"Selected kg: {query.data}")

    keyboard = [
        InlineKeyboardButton(str(d), callback_data=str(d)) for d in range(1, 51)
    ]

    chunk_size = 5
    chunks = [keyboard[x : x + chunk_size] for x in range(0, len(keyboard), chunk_size)]

    reply_markup = InlineKeyboardMarkup(chunks)

    await context.bot.send_message(chat_id, "How many reps?", reply_markup=reply_markup)

    return FERTIG


async def fertig(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    chat_id = query.message.chat.id
    user_id = query.from_user.id
    logger.info(f"user_id: {user_id}")
    logger.info(f"hashed: {hashlib.md5(bytes(user_id)).hexdigest()}")

    try:
        if "group" in query.message.chat.type:
            is_group = True
        else:
            is_group = False
    except Exception as e:
        logger.error(e)
        is_group = False

    await query.answer()

    reps_tmp[user_id] = query.data

    await query.edit_message_text(text=f"Selected reps: {query.data}")

    data_row = ",".join(
        [
            str(is_group),
            str(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            exercise_tmp[user_id],
            kg_tmp[user_id],
            reps_tmp[user_id],
        ]
    )

    with open(
        os.path.join(outdir, hashlib.md5(bytes(user_id)).hexdigest()) + ".csv", "a"
    ) as file:
        file.write(data_row + "\n")

    await context.bot.send_message(
        chat_id,
        f"Exercise saved: {', '.join([exercise_tmp[user_id], kg_tmp[user_id] + ' kg', reps_tmp[user_id] + ' reps'])}",
    )

    return START


async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancels the current operation."""

    await context.bot.send_message(
        update.message.chat.id, "Current operation cancelled."
    )

    return START


async def error_handler(update: object, context: CallbackContext) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    await context.bot.send_message(chat_id=developer_chat_id, text=str(context.error))


def main() -> None:
    """Setup and run the bot."""
    # Create the Updater and pass it your bot's token.
    application = ApplicationBuilder().token(bot_token).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("exercise", exercise),
            CommandHandler("report", report),
        ],
        states={
            START: [
                CommandHandler("start", start),
                CommandHandler("exercise", exercise),
                CommandHandler("report", report),
            ],
            KG: [CallbackQueryHandler(kg)],
            REPS: [CallbackQueryHandler(reps)],
            FERTIG: [CallbackQueryHandler(fertig)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)

    application.add_error_handler(error_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
