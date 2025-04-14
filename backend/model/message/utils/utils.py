
import requests
import os
import time
import requests
from schema.message import message
import mimetypes


class Utils:

    def __init__(self):
      
        
        # Base de la URL de Graph y versión de la API
        # Para unificar, separamos la base y la versión.
        self.graph_api_base = "https://graph.facebook.com"
        self.api_version = "v22.0"
        self.access_token = "EAAafKCUnI2cBOwRrVRGF8OtdPcubRrO8ZAZCMZAvApcyTpzub1QqwOvbN5XZA6IV2eLxmZCZCBC5FSZCkTzio0cp5dKDIN9VVTcoO1CLieFPZCQlXYEZCK9jPblGfZAXKRelDnIkOKqDnFYluIaFZAU3u9i7WmcKviY5bbNWewlKJLa46plXMdU9fGwZATMu8vqvLhuZA8Kf8QAG84yhKg7j48zMsdJqZBiAZDZD"
        

    def identify_message_type(self, data: message.Webhook) -> tuple:
        """
        Recorre el webhook y, según se trate de un mensaje o una actualización de estado,
        imprime un diccionario con la información extra y luego retorna la tupla original:
        - Para mensajes: (msg_type, data_extra) y se imprime un diccionario con:
            { id, user_id, content, context_message_id, created_at }
        - Para estados: (status_type, None) y se imprime un diccionario con:
            { id, timestamp, current_status }
        """
        for entry in data.entry:
            for change in entry.changes:
                value = change.value

                # Si existen mensajes:
                if value.messages and len(value.messages) > 0:
                    first_message = value.messages[0]
                    msg_type = first_message.type

                    # Construimos el diccionario de información para mensajes
                    message_dict = {
                        "id": getattr(first_message, "id", None),
                        "user_id": getattr(first_message, "from", None),
                        "content": None,
                        "context_message_id": None,
                        "created_at": getattr(first_message, "timestamp", None)
                    }
                    # Determinamos el contenido según el tipo de mensaje
                    if msg_type == "text":
                        if hasattr(first_message, "text") and first_message.text:
                            message_dict["content"] = first_message.text.body
                    elif msg_type in ["audio", "image", "document"]:
                        media_obj = getattr(first_message, msg_type, None)
                        message_dict["content"] = getattr(media_obj, "id", None)
                    elif msg_type == "location":
                        if hasattr(first_message, "location") and first_message.location:
                            loc = first_message.location
                            message_dict["content"] = f"lat:{loc.latitude}, lon:{loc.longitude}"
                    else:
                        # Para otros tipos se podría agregar lógica adicional si es necesario
                        message_dict["content"] = None

                    # Extraemos el context_message_id si existe
                    if hasattr(first_message, "context") and first_message.context:
                        message_dict["context_message_id"] = getattr(first_message.context, "id", None)

                    # Imprimimos el diccionario para mensajes
                    print(message_dict)

                    # Mantenemos los returns originales según el tipo de mensaje:
                    if msg_type in ["audio", "image", "document"]:
                        media_obj = getattr(first_message, msg_type, None)
                        media_id = media_obj.id if media_obj else None
                        return msg_type, media_id, None

                    if msg_type == "location" and first_message.location:
                        loc = first_message.location
                        return msg_type, (loc.latitude, loc.longitude, loc.name, loc.address), None

                    if msg_type == "contacts" and first_message.contacts:
                        return msg_type, first_message.contacts, None

                    return msg_type, None, None

                # Si no hay mensajes pero sí actualizaciones de estado:
                elif value.statuses and len(value.statuses) > 0:
                    first_status = value.statuses[0]
                    status_type = first_status.status
                    status_dict = {
                        "id": getattr(first_status, "id", None),
                        "timestamp": getattr(first_status, "timestamp", None),
                        "current_status": getattr(first_status, "status", None)
                    }
                    # Imprimimos el diccionario para estado
                    print(status_dict)
                    return status_type, None, status_dict

        # Si no se encontró ningún mensaje ni estado, retornamos "desconocido" manteniendo el formato
        return "desconocido", None, None


    def download_media_file(self, media_id: str) -> str:
        """
        Dado un media_id de un mensaje de WhatsApp, obtiene la URL y lo descarga al servidor.

        Retorna la ruta local donde se guardó el archivo.
        """
        # 1) Construir el endpoint para obtener la URL de descarga
        media_url_endpoint = f"{self.graph_api_base}/{self.api_version}/{media_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}"
        }

        # 1.a) Obtener la info del media (que incluye la 'url' real de descarga)
        response = requests.get(media_url_endpoint, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Error al obtener info del media: {response.text}")

        media_info = response.json()
        download_url = media_info.get("url")
        if not download_url:
            raise Exception(f"No se encontró 'url' en la respuesta: {media_info}")

        # 2) Descargar el archivo desde esa 'download_url', usando el mismo token
        download_response = requests.get(download_url, headers=headers, stream=True)
        if download_response.status_code != 200:
            raise Exception(f"Error al descargar el archivo: {download_response.text}")

        # 2.a) Determinar la extensión del archivo según el mime_type
        # Primero revisamos 'mime_type' en la respuesta JSON, si existe.
        mime_type = media_info.get('mime_type')

        # Si no está en media_info, revisamos headers de la descarga
        if not mime_type:
            mime_type = download_response.headers.get('Content-Type', '')

        # Usamos mimetypes para adivinar la extensión a partir del mime type
        extension = ''
        if mime_type:
            guessed_ext = mimetypes.guess_extension(mime_type)
            if guessed_ext:
                extension = guessed_ext

        # 3) Guardar el archivo en el servidor
        #    Generamos un nombre basado en la hora actual
        filename = f"file_{int(time.time())}{extension}"

        # Directorio donde guardaremos el archivo (ajusta según tu entorno)
        save_dir = "./media"
        os.makedirs(save_dir, exist_ok=True)  # Crea el directorio si no existe

        file_path = os.path.join(save_dir, filename)
        with open(file_path, "wb") as f:
            for chunk in download_response.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return file_path
