# Clase vacía para demostración (de momento)


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

    async def LogOut(self) -> None:
        print("Not implemented")
        return

    ##############################################################################
    async def Login(self) -> bool:
        print("Not implemented")
        return True

    ##############################################################################
    async def CheckLogin(self) -> bool:
        print("Not implemented")
        return True

    ##############################################################################
    async def UploadDraft(self, path: str, progress_callback=None) -> dict:
        print("Not implemented")
        return {"error": "Error. Not Implemented."}

    # Dudoso: Experimentos hasta ahora demuestran que no elimina el archivo
    # directamente, solo borra el link, lo que podria acelerar o no la eliminación
    # por parte del servidor
    ##############################################################################
    async def DeleteDraft(self, url: str):
        print("Not implemented")
        return {"error": "Error. Not Implemented."}
