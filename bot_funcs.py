from logging import basicConfig, log, INFO, WARN, ERROR, CRITICAL

basicConfig(format="[%(levelname)s]: %(message)s", level=INFO, force=True)

import asyncio
from random import randint
from typing import Coroutine

import bot_constants
import misc_funcs
import bot_cfg

from moodle_client import MoodleClient
import re
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors.exceptions.bad_request_400 import MessageNotModified
from pathlib import Path
from datetime import datetime
import yt_dlp

# Diccionario con tareas en ejecución, formato esperado:
# {
# msg_id: task_obj,
# msg_id: task_obj,
# msg_id: task_obj,
# }
tasks_dict: dict = {}
moodle = MoodleClient(
    bot_cfg.global_config["moodle_url"],
    bot_cfg.global_config["moodle_user"],
    bot_cfg.global_config["moodle_password"],
    bot_cfg.global_config["moodle_repo_id"],
)

# Iniciador de Tareas Cancelables
async def bot_task_start(progress_msg: Message, command_task: Coroutine):
    task_id = str(progress_msg.chat.id) + "-" + str(progress_msg.id)
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    task_obj: asyncio.Task = loop.create_task(command_task)
    tasks_dict[task_id] = task_obj
    await asyncio.wait_for(task_obj, None)
    tasks_dict.pop(task_id)


# Cancelar Tarea
async def bot_task_cancel(progress_msg: Message):
    task_id = str(progress_msg.chat.id) + "-" + str(progress_msg.id)
    task: asyncio.Task = tasks_dict[task_id]
    while not task.done():
        task.cancel()
        await asyncio.sleep(0.001)

    try:
        await progress_msg.edit(bot_constants.STR_ERR_CANCELLED)
    except MessageNotModified:
        pass


# Mensaje de Bienvenida
async def bot_command_start(base_msg: Message):
    await base_msg.reply(bot_constants.STR_INFO_WELCOME.format(base_msg.from_user.first_name))
    log(INFO, f"User {base_msg.from_user.username} ({base_msg.from_user.id}) started the bot.")  # LOG


# Error de Usuario no autorizado
async def bot_command_auth_err(base_msg: Message):
    await base_msg.reply(bot_constants.STR_ERR_UNAUTHORIZED.format(base_msg.from_user.id))
    log(INFO, f"Unauthorized: {base_msg.from_user.username} ({base_msg.from_user.id})")  # LOG


# Ver configuración
async def bot_command_config(base_msg: Message):
    await base_msg.reply(
        bot_constants.STR_INFO_CONFIG.format(
            bot_cfg.global_config["moodle_url"],
            bot_cfg.global_config["moodle_user"],
            bot_cfg.global_config["moodle_password"],
            bot_cfg.global_config["moodle_repo_id"],
            bot_cfg.global_config["moodle_zip"],
        )
    )


# Editar tamaño de partes
async def bot_command_split(base_msg: Message):
    try:
        new_zips = int(base_msg.text.split(maxsplit=1)[-1])
        if new_zips > 0:
            bot_cfg.global_config["moodle_zip"] = new_zips
            bot_cfg.write_config()
            await base_msg.reply(bot_constants.STR_INFO_CONFIG_CHANGED)
        else:
            await base_msg.reply(bot_constants.STR_ERR_SPLIT)
    except:
        await base_msg.reply(bot_constants.STR_ERR_SPLIT)


# Editar autenticación
async def bot_command_auth(base_msg: Message):
    try:
        tokens = base_msg.text.split(maxsplit=4)
        new_url = tokens[1]
        new_user = tokens[2]
        new_password = tokens[3]
        new_repoid = int(tokens[4])

        bot_cfg.global_config["moodle_url"] = new_url
        bot_cfg.global_config["moodle_user"] = new_user
        bot_cfg.global_config["moodle_password"] = new_password
        bot_cfg.global_config["moodle_repo_id"] = new_repoid

        moodle.ServerUrl = new_url
        moodle.UserName = new_user
        moodle.Password = new_password
        moodle.RepoID = new_repoid
        await moodle.LogOut()
        bot_cfg.write_config()

        await base_msg.reply(bot_constants.STR_INFO_CONFIG_CHANGED)
    except:
        await base_msg.reply(bot_constants.STR_ERR_AUTH)


async def bot_command_ls(progress_msg: Message):
    try:
        buttons = []
        files_list = await misc_funcs.list_files_recursive("./downloads/")
        for i in files_list:
            buttons.append([InlineKeyboardButton(Path(i).name, switch_inline_query_current_chat=i)])

        if buttons == []:
            buttons = None
        else:
            buttons = InlineKeyboardMarkup(buttons)

        await progress_msg.edit(bot_constants.STR_INFO_FILE_LIST, reply_markup=buttons)
    except:
        pass


# Recibido un link o un archivo
async def bot_download(base_msg: Message, progress_msg: Message):
    buttons: InlineKeyboardMarkup = progress_msg.reply_markup
    msg_text: str = str(base_msg.text)

    # Paso 1: Descargar el archivo
    try:
        await progress_msg.edit(bot_constants.STR_INFO_DOWNLOADING.format(0), reply_markup=buttons)
    except MessageNotModified:
        pass

    try:
        if base_msg.document or base_msg.audio or base_msg.video or base_msg.sticker or base_msg.photo:
            log(INFO, f"STATUS=Downloading, User={base_msg.from_user.username}, Data=FILE")  # LOG
            fpath = await base_msg.download(
                file_name=f"./downloads/{randint(1000000000,9999999999)}/",
                progress=tg_progress_bar,
                progress_args=[progress_msg],
            )
        else:
            msg_url = re.findall(r"https*://[^\s\t\n]+", msg_text, flags=re.IGNORECASE)[0]
            log(INFO, f"STATUS=Downloading, User={base_msg.from_user.username}, Data={msg_url}")  # LOG
            fpath = await misc_funcs.url_download(msg_url, lambda data: yt_dlp_progress_bar(data, progress_msg))

        log(INFO, f"STATUS=Downloaded, User={base_msg.from_user.username}, Data={fpath}")  # LOG
    except Exception as e:

        log(ERROR, f"STATUS=DownloadERROR, User={base_msg.from_user.username}, Data={e}")  # LOG
        try:
            await progress_msg.edit(bot_constants.STR_ERR_DOWNLOAD)
        except MessageNotModified:
            pass

        return

    # Paso 2: Comprimir y Dividir si sobrepasa MOODLE_ZIP
    fsize = Path(fpath).stat().st_size
    if fsize > bot_cfg.global_config["moodle_zip"] * 1024 * 1024:
        try:
            log(INFO, f"STATUS=Compressing, User={base_msg.from_user.username}, Data={fpath}")  # LOG

            try:
                await progress_msg.edit(bot_constants.STR_INFO_COMPRESSING, reply_markup=buttons)
            except MessageNotModified:
                pass

            file_list = await misc_funcs.compress(fpath, bot_cfg.global_config["moodle_zip"])
            log(INFO, f"STATUS=Compressed, User={base_msg.from_user.username}, Data=files({len(file_list)})")  # LOG
        except Exception as e:
            log(ERROR, f"STATUS=CompressERROR, User={base_msg.from_user.username}, Data={e}")  # LOG

            try:
                await progress_msg.edit(bot_constants.STR_ERR_COMPRESS)
            except MessageNotModified:
                pass

            return
    else:
        file_list = [fpath]

    # Paso 3: Subir al Moodle
    failed_list = []
    completed_list = []

    for i, file in enumerate(file_list):
        for attemp in range(3):  # Cantidad de reintentos
            try:
                log(INFO, f"STATUS=Uploading, User={base_msg.from_user.username}, Data={file}")  # LOG
                upload_data = {}
                await moodle.Login()

                upload_data = await moodle.UploadDraft(
                    file,
                    progress_callback=lambda current, total: moodle_upload_progress_bar(
                        current, total, file, i + 1, len(file_list), progress_msg
                    ),
                )
                if upload_data.get("event") == "fileexists":
                    upload_data = upload_data.get("newfile")
                file_url = upload_data["url"]
                completed_list.append(file_url)
                buttons.inline_keyboard.insert(
                    -1,
                    [
                        InlineKeyboardButton(f"✅ {Path(file).name}", url=file_url),
                        InlineKeyboardButton(bot_constants.STR_BTN_REUPLOAD, switch_inline_query_current_chat=file),
                    ],
                )

                try:
                    await progress_msg.edit_reply_markup(buttons)
                except MessageNotModified:
                    pass

                log(INFO, f"STATUS=Uploaded, User={base_msg.from_user.username}, Data={file}")  # LOG
                break
            except asyncio.CancelledError as e:
                return
            except Exception as e:
                log(
                    ERROR,
                    f"STATUS=UploadERROR, User={base_msg.from_user.username}, Data=try({attemp+1}/3, {upload_data})",
                )  # LOG
        else:
            buttons.inline_keyboard.insert(
                -1,
                [
                    InlineKeyboardButton(f"❌ {Path(file).name}", switch_inline_query_current_chat=file),
                    InlineKeyboardButton(bot_constants.STR_BTN_REUPLOAD, switch_inline_query_current_chat=file),
                ],
            )

            try:
                await progress_msg.edit_reply_markup(buttons)
            except MessageNotModified:
                pass

            failed_list.append(file)

    buttons.inline_keyboard.pop()
    if buttons.inline_keyboard == []:
        buttons = None

    try:
        await progress_msg.edit(
            bot_constants.STR_INFO_COMPLETED.format(len(file_list) - len(failed_list), len(failed_list)),
            reply_markup=buttons,
        )
    except MessageNotModified:
        pass

    try:
        with open(fpath + ".txt", "w") as f:
            f.write("\n".join(completed_list))
        await progress_msg.reply_document(fpath + ".txt", reply_to_message_id=progress_msg.id)
    except:
        pass


async def bot_reupload(base_msg: Message, progress_msg: Message):
    buttons: InlineKeyboardMarkup = progress_msg.reply_markup
    fpath: str = " ".join(str(base_msg.text).split(" ")[1:]).strip()

    file_list = [fpath]

    failed_list = []
    completed_list = []
    for i, file in enumerate(file_list):
        for attemp in range(3):  # Cantidad de reintentos
            try:
                log(INFO, f"STATUS=Uploading, User={base_msg.from_user.username}, Data={file}")  # LOG
                upload_data = {}
                await moodle.Login()
                upload_data = await moodle.UploadDraft(
                    file,
                    progress_callback=lambda current, total: moodle_upload_progress_bar(
                        current, total, file, i + 1, len(file_list), progress_msg
                    ),
                )
                if upload_data.get("event") == "fileexists":
                    upload_data = upload_data.get("newfile")
                file_url = upload_data["url"]
                completed_list.append(file_url)
                buttons.inline_keyboard.insert(
                    -1,
                    [
                        InlineKeyboardButton(f"✅ {Path(file).name}", url=file_url),
                        InlineKeyboardButton(bot_constants.STR_BTN_REUPLOAD, switch_inline_query_current_chat=file),
                    ],
                )

                try:
                    await progress_msg.edit_reply_markup(buttons)
                except MessageNotModified:
                    pass

                log(INFO, f"STATUS=Uploaded, User={base_msg.from_user.username}, Data={file}")  # LOG
                break
            except asyncio.CancelledError as e:
                return
            except Exception as e:
                log(
                    ERROR,
                    f"STATUS=UploadERROR, User={base_msg.from_user.username}, Data=try({attemp+1}/3, {upload_data})",
                )  # LOG
        else:
            buttons.inline_keyboard.insert(
                -1,
                [
                    InlineKeyboardButton(f"❌ {Path(file).name}", switch_inline_query_current_chat=file),
                    InlineKeyboardButton(bot_constants.STR_BTN_REUPLOAD, switch_inline_query_current_chat=file),
                ],
            )

            try:
                await progress_msg.edit_reply_markup(buttons)
            except MessageNotModified:
                pass

            failed_list.append(file)

    buttons.inline_keyboard.pop()
    if buttons.inline_keyboard == []:
        buttons = None

    try:
        await progress_msg.edit(
            bot_constants.STR_INFO_COMPLETED.format(len(file_list) - len(failed_list), len(failed_list)),
            reply_markup=buttons,
        )
    except MessageNotModified:
        pass

    try:
        with open(fpath + ".txt", "w") as f:
            f.write("\n".join(completed_list))
        await progress_msg.reply_document(fpath + ".txt", reply_to_message_id=progress_msg.id)
    except:
        pass


# Slow wrapper
def slow(secs):
    def dec(f):
        t = [datetime.utcnow().timestamp()]

        async def wrapper(*args, **kwargs):
            now = datetime.utcnow().timestamp()
            if now - t[0] < secs:
                return
            t[0] = now
            return await f(*args, **kwargs)

        return wrapper

    return dec


# File download progress tracking
@slow(2)
async def tg_progress_bar(current: int, total: int, *args):
    progress_msg: Message = args[0]

    try:
        await progress_msg.edit(
            bot_constants.STR_INFO_DOWNLOADING.format(100 * current // total), reply_markup=progress_msg.reply_markup
        )
    except MessageNotModified:
        pass


# URL download progress tracking
def yt_dlp_progress_bar(data: dict, progress_msg: Message, start_time=[datetime.now().timestamp()]):
    now = datetime.now().timestamp()
    if now - start_time[0] < 2:
        return
    start_time[0] = now

    task_id = str(progress_msg.chat.id) + "-" + str(progress_msg.id)

    if task_id in tasks_dict:
        if not tasks_dict[task_id].cancelled():
            if data["status"] == "downloading":
                try:
                    progress_msg.edit(
                        bot_constants.STR_INFO_DOWNLOADING.format(
                            100 * data["downloaded_bytes"] // data["total_bytes"]
                        ),
                        reply_markup=progress_msg.reply_markup,
                    )
                except MessageNotModified:
                    pass

                return
    raise yt_dlp.utils.DownloadCancelled


# Moodle upload progress tracking
def moodle_upload_progress_bar(
    file_pos: int,
    file_size: int,
    file_name: str,
    current_file: int,
    files_count: int,
    progress_msg: Message,
    progress_data={},
):
    if file_pos == file_size:
        progress_data.pop(progress_msg.id)
        return

    if not progress_msg.id in progress_data:
        progress_data[progress_msg.id] = {}
        progress_data[progress_msg.id]["last_update"] = datetime.now().timestamp() - 2.1
        progress_data[progress_msg.id]["last_pos"] = 0

    now = datetime.now().timestamp()
    if now - progress_data[progress_msg.id]["last_update"] < 2:
        return

    speed = int(
        (file_pos - progress_data[progress_msg.id]["last_pos"])
        / (now - progress_data[progress_msg.id]["last_update"])
        / 1024
    )
    percent = 100 * file_pos // file_size
    progress_bar = "■" * (percent // 10) + "□" * (10 - (percent // 10))

    try:
        progress_msg.edit(
            bot_constants.STR_INFO_UPLOADING.format(
                current_file,
                files_count,
                Path(file_name).name,
                round(file_size / 1024 / 1024, 2),
                speed,
                progress_bar,
                percent,
            ),
            reply_markup=progress_msg.reply_markup,
        )
    except MessageNotModified:
        pass

    progress_data[progress_msg.id]["last_update"] = now
    progress_data[progress_msg.id]["last_pos"] = file_pos
