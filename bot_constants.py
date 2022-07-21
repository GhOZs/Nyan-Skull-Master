# Constantes del Bot

# Mensajes de información
STR_INFO_WELCOME = "Bienvenido {}. Envia un archivo o un link para descargar."
STR_INFO_PROCESSING = "⏳ Procesando..."
STR_INFO_DOWNLOADING = "⏬ Descargando... {}%"
STR_INFO_COMPRESSING = "🗄 Comprimiendo..."
STR_INFO_UPLOADING = "⏫ Subiendo: {}/{}\n📄 Nombre: {}\n💾 Tamaño: {} MiB\n⏱ Velocidad: {} KiB/s\n⚙️ Progreso: {} {}%"
STR_INFO_COMPLETED = "✅ Completado: {} subidos, {} fallidos."
STR_INFO_CONFIG = "Configuración\n\n💠 URL: {}\n👩‍🎤 Usuario: {}\n🔐 Contraseña: {}\n⚙️ RepoID: {}\n📐 Tamaño de partes: {} MiB\n\nPara editar la configuración use los comandos /auth y /split"
STR_INFO_CONFIG_CHANGED = "✅ Configuracion modificada"
STR_INFO_FILE_LIST = "✅ Listado de archivos en el servidor:"

# Mensajes de error
STR_ERR_UNAUTHORIZED = "❌ Error. No eres un usuario autorizado.\n🔎 ID: {}"
STR_ERR_CANCELLED = "❌ Cancelado por el usuario."
STR_ERR_DOWNLOAD = "❌ Error. No se ha podido descargar."
STR_ERR_COMPRESS = "❌ Error. No se ha podido comprimir."
STR_ERR_UPLOAD = "❌ Error. No se ha podido subir."
STR_ERR_SPLIT = "❌ Error. El uso correcto del comando es:\n\n/split «tamaño en MiB»\nEjemplo: /split 100"
STR_ERR_AUTH = "❌ Error. El uso correcto del comando es:\n\n/auth «url» «usuario» «contraseña» «repoID»\nEjemplo: /auth http://ejemplo.com mi_usuario mi_contraseña 2"

# Botones
STR_BTN_CANCEL = "Cancelar"
STR_BTN_REUPLOAD = "♻️ Resubir"
