from tg_datastore import TGDataStore
from json import dumps


def write_config():
    global global_config
    datastore.write_field(datastore_field_id, global_config)


def read_config() -> dict:
    global global_config
    global_config = datastore.read_field(datastore_field_id)


tg_api_id = 16346841
tg_api_hash = "41994f821a9a2e16195eea854e18bdbc"
tg_bot_token = "5349837003:AAGz0W9HCaNG3CfMvGZg4oW0MfVuRJgxdq0"
datastore_store_id =-1001478975217
datastore_field_id = 2
global_config = {}

datastore = TGDataStore(tg_bot_token, datastore_store_id)

read_config()
print("Config:\n", dumps(global_config, indent=4))
