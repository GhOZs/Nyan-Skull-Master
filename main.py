from logging import basicConfig, getLogger, log, INFO, WARN, ERROR, CRITICAL

basicConfig(format="[%(levelname)s]: %(message)s", level=INFO, force=True)
pyrogram_logger = getLogger("pyrogram")
pyrogram_logger.setLevel(WARN)
log(INFO, "Initializing...")


# Imports generales
import asyncio
import re
from pathlib import Path

from pyrogram import Client
from pyrogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

# Configuración del bot
import bot_cfg
import bot_constants
import bot_funcs

bot: Client = Client(
    "bot",
    api_id=bot_cfg.tg_api_id,
    api_hash=bot_cfg.tg_api_hash,
    bot_token=bot_cfg.tg_bot_token,
)

###################################################################################################
# Message Handler:
###################################################################################################
@bot.on_message()
async def message_handler(client: Client, message: Message):
    msg_text: str = str(message.text)
    if msg_text.lower().startswith(f"@{client.me.username}".lower()):
        msg_text = msg_text[len(f"@{client.me.username}") :].strip()

    # Mensaje de bienvenida
    if msg_text.lower() == "/start":
        await bot_funcs.bot_command_start(message)

    # Usuario no autorizado
    if not (message.from_user.id in bot_cfg.global_config["users_allowed"]):
        await bot_funcs.bot_command_auth_err(message)
        return

    # Ver configuración
    elif msg_text.lower() == "/config":
        await bot_funcs.bot_command_config(message)

    # Editar tamaño de partes
    elif msg_text.lower().startswith("/split"):
        await bot_funcs.bot_command_split(message)

    # Editar credenciales
    elif msg_text.lower().startswith("/auth"):
        await bot_funcs.bot_command_auth(message)

    # Comando /ls (Ni idea de para qué lo quiere)
    elif msg_text.lower() == "/ls":
        progress_msg: Message = await message.reply(bot_constants.STR_INFO_PROCESSING, reply_to_message_id=message.id)
        await bot_funcs.bot_command_ls(progress_msg)

    # Link de descarga o archivo
    elif re.findall(r"https*://[^\s\t\n]+", msg_text, flags=re.IGNORECASE) or (
        message.document or message.audio or message.video or message.sticker or message.photo
    ):
        progress_msg: Message = await message.reply(
            bot_constants.STR_INFO_PROCESSING,
            reply_to_message_id=message.id,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(bot_constants.STR_BTN_CANCEL, "task_cancel")]]),
        )
        await bot_funcs.bot_task_start(progress_msg, bot_funcs.bot_download(message, progress_msg))

    # Resubida
    elif Path(msg_text).parent.parent.name.lower() == "downloads" and Path(msg_text).is_file():
        progress_msg: Message = await message.reply(
            bot_constants.STR_INFO_PROCESSING,
            reply_to_message_id=message.id,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(bot_constants.STR_BTN_CANCEL, "task_cancel")]]),
        )
        await bot_funcs.bot_task_start(progress_msg, bot_funcs.bot_reupload(message, progress_msg))


###################################################################################################
# Callback Handler:
###################################################################################################
@bot.on_callback_query()
async def callback_handler(client: Client, callback_query: CallbackQuery):
    data: str = str(callback_query.data)
    # Cancelar tarea
    if data == "task_cancel":
        progress_msg: Message = callback_query.message
        await bot_funcs.bot_task_cancel(progress_msg)


###################################################################################################
# Main Loop
###################################################################################################
log(INFO, "Starting...")
bot.start()
log(INFO, "Ready.")
bot.loop.run_forever()
