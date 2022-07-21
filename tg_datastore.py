from json import loads, dumps
from random import randbytes, randint, seed
import requests

#############################################################################################################
#                                                                                                           #
# TGDataStore v0.1                                                                                          #
# Simple JSON object storage in telegram messages.                                                          #
# By Nyan (TG: @el_garro)                                                                                   #
#                                                                                                           #
# Requisites:                                                                                               #
# - A channel to store data on                                                                              #
# - A telegram bot. The bot needs to be admin of the channel and able to edit                               #
# and access all messages (configurable in BotFather).                                                      #
#                                                                                                           #
# Notes:                                                                                                    #
# - Telegram messages are limited to 4KB                                                                    #
# - The encryption provided is NOT secure and you should not rely on it                                     #
#                                                                                                           #
#############################################################################################################
class TGDataStore:
    def __init__(self, bot_token: str, store_id: int, password: str = "") -> None:
        """Simple JSON object storage in telegram messages

        Args:
            bot_token (str): Telegram bot token to access data
            store_id (int): Telegram channel used to store data
            password (str, optional): Password to save and read data. Defaults to "" (unencrypted).
        """
        self.bot_token: str = bot_token
        self.store_id: int = int(store_id)
        self.password: str = password

    #########################################################################################################
    # Publics
    #########################################################################################################
    def read_field(self, field: int) -> dict | str:
        """Reads the data of a field

        Args:
            field (int): field id

        Returns:
            dict | str: Content of the field
        """
        try:
            message = self.__read_raw_message(self.bot_token, self.store_id, field)
            data = message["text"]

            if self.password != "":
                data = self.__cipher(data[1:-1], decrypt=True)

            try:
                return loads(data)
            except:
                return data

        except:
            return False

    def write_field(self, field: int, data: str | dict | list, pretty_json: bool = False) -> bool:
        """Write data to a field

        Args:
            field (int): field id
            data (str | dict | list): Data to write
            pretty_json (bool, optional): Prettify JSON. Defaults to False.

        Returns:
            bool: True if successful
        """
        try:
            if pretty_json and self.password == "":
                data = dumps(data, indent=4)
            else:
                data = dumps(data)
        except:
            pass

        data = str(data)
        if self.password != "":
            data = "=" + self.__cipher(data) + "="

        return self.__write_raw_message(self.bot_token, self.store_id, field, data)

    def create_field(self) -> int:
        """Create a new empty field

        Returns:
            int: field id
        """
        try:
            with requests.session() as session:
                send_message_url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
                send_message_query = {
                    "chat_id": self.store_id,
                    "text": "{}",
                }
                with session.post(send_message_url, data=send_message_query) as response:
                    data = response.json()

                message_id = data["result"]["message_id"]
                self.__read_raw_message(self.bot_token, self.store_id, message_id)
                return message_id
        except:
            return False

    #########################################################################################################
    # Privates
    #########################################################################################################
    def __cipher(self, data: str, decrypt: bool = False):
        seed(self.password)

        data = list(data)
        scrambler = [[randint(0, len(data) - 1), i] for i in range(len(data))]
        if decrypt:
            scrambler.reverse()

        for i, k in scrambler:
            data[i], data[k] = data[k], data[i]

        seed()
        return "".join(data)

    def __read_raw_message(self, bot_token: str, chat_id: int, message_id: int):
        with requests.session() as session:

            edit_reply_markup_url = f"https://api.telegram.org/bot{bot_token}/editMessageReplyMarkup"

            random_button = {
                "inline_keyboard": [[{"text": f"FIELD {message_id}", "callback_data": randbytes(32).hex()}]]
            }

            edit_reply_markup_query = {
                "chat_id": chat_id,
                "message_id": message_id,
                "reply_markup": dumps(random_button),
            }

            with session.post(edit_reply_markup_url, data=edit_reply_markup_query) as response:
                data: dict = response.json()

            if "ok" in data:
                if data["ok"] == True:
                    data = data["result"]

            return data

    def __write_raw_message(self, bot_token: str, chat_id: int, message_id: int, text: str):
        with requests.session() as session:
            edit_message_url = f"https://api.telegram.org/bot{bot_token}/editMessageText"

            random_button = {
                "inline_keyboard": [
                    [
                        {
                            "text": f"FIELD {message_id}",
                            "callback_data": randbytes(32).hex(),
                        }
                    ]
                ]
            }

            edit_message_query = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "reply_markup": dumps(random_button),
            }

            with session.post(edit_message_url, data=edit_message_query) as response:
                return response.json()["ok"]
