from random import random
from typing import Callable
import aiohttp
from yarl import URL
from bs4 import BeautifulSoup
import asyncio

import re
import json

from io import BufferedReader, FileIO
from pathlib import Path


class ProgressFile(BufferedReader):
    def __init__(self, filename, read_callback):
        f = FileIO(file=filename, mode="r")
        self.__read_callback = read_callback
        super().__init__(raw=f)

        self.length = Path(filename).stat().st_size

    def read(self, size=None):
        calc_sz = size
        if not calc_sz:
            calc_sz = self.length - self.tell()
        self.__read_callback(self.tell(), self.length)
        return super(ProgressFile, self).read(size)


class MoodleClient:

    ##############################################################################
    def __init__(self, ServerUrl: str, UserName: str, Password: str, RepoID: int | str) -> None:
        # Atributos públicos
        self.ServerUrl: str = ServerUrl
        self.UserName: str = UserName
        self.Password: str = Password
        self.RepoID: int | str = RepoID
        self.MaxTasks: int = 3
        self.TasksInProgress: int = 0

        # Atributos privados
        self.__Session: aiohttp.ClientSession = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))
        self.__Headers: dict = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.72 Safari/537.36"
        }
        self.__LoginLOCK: bool = False

    async def LogOut(self) -> None:
        await self.__Session.close()
        self.__Session = aiohttp.ClientSession(cookie_jar=aiohttp.CookieJar(unsafe=True))

    ##############################################################################
    async def Login(self) -> bool:
        # Esperar si hay un inicio de sesión en progreso
        while self.__LoginLOCK:
            await asyncio.sleep(random() * 4 + 1)
        self.__LoginLOCK = True

        # Comprobar si hay una sesión iniciada
        if await self.CheckLogin():
            ret = True
        else:

            # Intentar iniciar sesión
            try:

                # Extraer el token de inicio de sesión
                timeout = aiohttp.ClientTimeout(total=20)
                async with self.__Session.get(
                    url=self.ServerUrl + "/login/index.php",
                    headers=self.__Headers,
                    timeout=timeout,
                ) as response:
                    html = await response.text()

                # Preparar payload de inicio de sesión
                try:
                    # Caso para veriones modernas de Moodle
                    soup = BeautifulSoup(html, "html.parser")
                    token = soup.find("input", attrs={"name": "logintoken"})["value"]
                    payload = {
                        "anchor": "",
                        "logintoken": token,
                        "username": self.UserName,
                        "password": self.Password,
                        "rememberusername": 1,
                    }
                except:
                    # Caso para la versión obsoleta de Aulavirtual de SLD
                    payload = {
                        "anchor": "",
                        "username": self.UserName,
                        "password": self.Password,
                        "rememberusername": 1,
                    }

                # Iniciar sesión
                async with self.__Session.post(
                    url=self.ServerUrl + "/login/index.php",
                    headers=self.__Headers,
                    data=payload,
                    timeout=timeout,
                ) as response:
                    await response.text()

                # Comprobar si no redireccionó desde /login/index.php
                if str(response.url).lower() == (self.ServerUrl + "/login/index.php").lower():
                    # Error, datos incorrectos
                    ret = False
                else:
                    # Sesión iniciada
                    ret = True
                    # print(self.__Session.cookie_jar.filter_cookies(URL(self.ServerUrl)))

            except:
                # Error desconocido (mayormente conexión)
                ret = False

        self.__LoginLOCK = False
        return ret

    ##############################################################################
    async def CheckLogin(self) -> bool:
        try:
            timeout = aiohttp.ClientTimeout(total=20)
            async with self.__Session.get(
                url=self.ServerUrl + "/user/profile.php",
                headers=self.__Headers,
                allow_redirects=False,
                timeout=timeout,
            ) as response:
                html = await response.text()
            if (response.status == 200) and (html.lower().count("<title>")):
                return True
        except:
            pass
        return False

    ##############################################################################
    async def UploadDraft(self, path: str, progress_callback: Callable = None) -> dict:
        await asyncio.sleep(random())  # Para evitar colisiones en las tareas
        # Evita superar el máximo de tareas permitidas
        while self.TasksInProgress >= self.MaxTasks:
            await asyncio.sleep(random() * 4 + 1)

        self.TasksInProgress += 1

        try:
            # Obtener parámetros
            timeout = aiohttp.ClientTimeout(total=20)
            async with self.__Session.get(
                url=self.ServerUrl + "/user/edit.php",  # Porque algunos bloquean el files.php
                headers=self.__Headers,
                timeout=timeout,
            ) as response:
                resp_1 = await response.text()

            soup = BeautifulSoup(resp_1, "html.parser")
            sesskey = soup.find("input", attrs={"name": "sesskey"})["value"]
            query = URL(soup.find("object", attrs={"type": "text/html"})["data"]).query

            client_id_pattern = '"client_id":"\w{13}"'
            client_id = re.findall(client_id_pattern, resp_1)
            client_id = re.findall("\w{13}", client_id[0])[0]
            itemid = query["itemid"]
            file = ProgressFile(filename=path, read_callback=progress_callback)
            # Crear payloads POST
            data = aiohttp.FormData()
            data.add_field("title", "")
            data.add_field("author", self.UserName)
            data.add_field("license", "allrightsreserved")
            data.add_field("itemid", itemid)
            data.add_field("repo_id", str(self.RepoID))
            data.add_field("p", "")
            data.add_field("page", "")
            data.add_field("env", "filemanager")
            data.add_field("sesskey", sesskey)
            data.add_field("client_id", client_id)
            ##################################################################################################
            data.add_field("maxbytes", query["maxbytes"])
            # data.add_field("areamaxbytes", query["areamaxbytes"])
            # Lo anterior es lo correcto, lo siguiente es un hack para sobrepasar el tamaño de archivo definido
            data.add_field("areamaxbytes", str(1024 * 1024 * 1024 * 4))
            #################################################################################################
            data.add_field("ctx_id", query["ctx_id"])
            data.add_field("savepath", "/")
            data.add_field("repo_upload_file", file)

            timeout = aiohttp.ClientTimeout(connect=30, total=60 * 60)  # 1H de timeout
            async with self.__Session.post(
                url=self.ServerUrl + "/repository/repository_ajax.php?action=upload",
                data=data,
                headers=self.__Headers,
                timeout=timeout,
            ) as response:
                resp = await response.text()
                print(resp)
                # resp = await response.json(content_type=None)
                resp = json.loads(resp)
        except:
            resp = {"error": "Error. Error desconocido."}

        self.TasksInProgress -= 1
        file.close()
        return resp

    # Dudoso: Experimentos hasta ahora demuestran que no elimina el archivo
    # directamente, solo borra el link, lo que podria acelerar o no la eliminación
    # por parte del servidor
    ##############################################################################
    async def DeleteDraft(self, url: str):

        try:
            # Obtener parámetros
            timeout = aiohttp.ClientTimeout(total=20)
            async with self.__Session.get(
                url=self.ServerUrl + "/user/edit.php",  # Porque algunos bloquean el files.php
                headers=self.__Headers,
                timeout=timeout,
            ) as response:
                resp_1 = await response.text()

            soup = BeautifulSoup(resp_1, "html.parser")
            sesskey = soup.find("input", attrs={"name": "sesskey"})["value"]

            client_id_pattern = '"client_id":"\w{13}"'
            client_id = re.findall(client_id_pattern, resp_1)
            client_id = re.findall("\w{13}", client_id[0])[0]

            file = URL(url).path.split("/")

            payload = {
                "sesskey": sesskey,
                "client_id": client_id,
                "filepath": "/",
                "itemid": file[-2],
                "filename": file[-1],
            }

            async with self.__Session.post(
                url=self.ServerUrl + "/repository/draftfiles_ajax.php?action=delete",
                data=payload,
                headers=self.__Headers,
                timeout=timeout,
            ) as response:
                return json.loads(await response.text())
        except:
            return {"error": "Error. Error desconocido."}
