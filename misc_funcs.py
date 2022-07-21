from os import unlink
from pathlib import Path
import asyncio
import py7zr
from random import randint
import yt_dlp


def async_decorator(func):
    def run(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, func, *args, **kwargs)

    return run


@async_decorator
def compress(fpath: str, part_size: int):
    fpath: Path = Path(fpath)
    filters = [{"id": py7zr.FILTER_COPY}]
    file_list = []
    # Comprimir
    with py7zr.SevenZipFile(
        f"{fpath}.7z",
        "w",
        filters=filters,
    ) as f:
        f.write(fpath, fpath.name)
    unlink(fpath)

    # Dividir
    with open(f"{fpath}.7z", "rb") as zip_file:
        file_count = 1
        eof = False
        while True:
            with open(f"{fpath}.7z.{file_count:03d}", "wb") as file_part:
                wrote_data = 0
                while wrote_data < (part_size * 1024 * 1024):
                    data = zip_file.read(1024 * 1024)
                    if not data:
                        eof = True
                        break
                    else:
                        file_part.write(data)
                        wrote_data += len(data)

            file_list.append(f"{fpath}.7z.{file_count:03d}")

            if eof:
                break
            file_count += 1

    unlink(f"{fpath}.7z")
    return file_list


@async_decorator
def list_files_recursive(basepath) -> list:
    basepath = Path(basepath)
    result = []
    for i in basepath.rglob("*"):
        if i.is_file():
            result.append(str(i))
    return result


# Descargar url con yt-dlp
async def url_download(url: str, callback: callable = None):
    # Logger para yt-dlp (Nulo)
    class YT_DLP_Logger(object):
        def debug(self, msg):
            pass

        def warning(self, msg):
            pass

        def error(self, msg):
            print(msg)

    dl_cfg = {
        "logger": YT_DLP_Logger(),
        "progress_hooks": [callback],
        "outtmpl": f"./downloads/{randint(1000000000,9999999999)}/%(title)s.%(ext)s",
    }
    downloader = yt_dlp.YoutubeDL(dl_cfg)
    loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
    fdata = await loop.run_in_executor(None, downloader.extract_info, url)
    fpath = downloader.prepare_filename(fdata)
    return fpath
