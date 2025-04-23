import requests
from fastapi import HTTPException, UploadFile
from schema.message import message
from config.db import Db as dataBase
from datetime import datetime
from . utils.utils import Utils
import time
from .  db_message import DbMessageService
import websocket  # Se importa la librería para manejo de sockets WebSocket
import os


class MessageService:
    """
    Servicio para enviar mensajes de WhatsApp a través de la API de Facebook.
    """

    def __init__(self):
        # Inicializa tu conexión a la DB si la necesitas (ejemplo).
        self.db = dataBase()
        self.utils = Utils()
        # Configura estas variables de entorno o cámbialas según tu caso.
        self.phone_number_id = {
            # mapea cada restaurant_id (entry_id) a su phone_number_id
            "1": "422125357649864",
            "7": "633892163131388"   # ejemplo
        }
        self.access_token = "EAAafKCUnI2cBO8L4LleLBjE1xNUu4mdkquRKnRAcZC660hMUBLfDcuZCpkTTnmUPLqnAiWfnEejIOWMmZB8dVd2Y16MyZCDqGlrUDuZBsQNYoRau6LDYK6z20Odlp89zun2Hzj2o7PmiCd8X606jE9gekqUMLIxAsGqfEZAFnhNgwCZA8PxPjmQHkhDEhorZCF7gZBxZAKqN9a5fAkWO8rtZBX3PJgM6hJ5jXZA6Jay0SlFF"
        
        # Base de la URL de Graph y versión de la API
        # Para unificar, separamos la base y la versión.
        self.graph_api_base = "https://graph.facebook.com"
        self.api_version = "v22.0"
        self.db_message = DbMessageService()
    
    # =================================================
    #   Métodos para enviar mensajes
    # =================================================

    def _build_template_message_data(self, payload: message.SendMessage) -> dict:
        if not payload.template:
            raise HTTPException(400, "Se requiere la data del template")
        return {
            "messaging_product": payload.messaging_product,
            "to": payload.to,
            "type": "template",
            "template": {
                "name": payload.template.name,
                "language": {"code": payload.template.language.code},
                "components": payload.template.components or []
            },
        }
                                        
    def _build_text_message_data(self, payload: message.SendMessage) -> dict:
        if not payload.text:
            raise HTTPException(400, "Se requiere el texto")
        data = {
            "messaging_product": payload.messaging_product,
            "to": payload.to,
            "type": "text",
            "text": {"body": payload.text.body},
        }
        if payload.context_message_id:
            data["context"] = {"message_id": payload.context_message_id}
        return data

    # ---------- llamada HTTP a la Graph API ----------
    def _send_request(self, endpoint: str, data: dict, restaurant_id: str) -> dict:
        """
        Envía la solicitud POST a la Graph API de WhatsApp.

        restaurant_id → entry_id de la página/sede
        """
        phone_id = self.phone_number_id.get(restaurant_id)
        if not phone_id:
            raise HTTPException(400, f"No encuentro phone_number_id para {restaurant_id}")
        
        print(phone_id)

        url = f"{self.graph_api_base}/{self.api_version}/{phone_id}/{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=data)
        if response.status_code != 200:
            raise HTTPException(response.status_code, response.text)
        return response.json()
    

    async def send_message(self, payload: message.SendMessage) -> dict:
            # 1. Construye el cuerpo
            if payload.type == "template":
                message_data = self._build_template_message_data(payload)
            elif payload.type == "text":
                message_data = self._build_text_message_data(payload)
            else:
                raise HTTPException(400, "Tipo de mensaje no soportado")

            # 2. Llama a la API, pasando restaurant_id
            api_response = self._send_request("messages", message_data, payload.restaurant_id)

            # 3. Registra en la BD (opcional)
            current_ts = int(time.time())
            data_message = message.Message(
                id=api_response["messages"][0]["id"],
                from_="str",
                timestamp=str(current_ts),
                type="str",
                context=message.Context(id=payload.context_message_id),
                text=message.Text(body=payload.text.body if payload.text else ""),
            )

            user_id = self.db_message.get_user_by_wa_id(payload.to)
            phone_id = self.phone_number_id.get(payload.restaurant_id)
            if not phone_id:
                raise HTTPException(400, f"No encuentro phone_number_id para {phone_id}")
            
            self.db_message.create_message(
                data=data_message,
                user_id=user_id,
                employer_id=payload.employer_id,
                wa_user_id=payload.to,
                entry_id=phone_id         # ← aquí va el entry_id
            )

            return api_response["messages"][0]["id"]

    async def send_text_message(self, payload: message.SendMessage) -> dict:
        """
        Envía un mensaje de texto a través de la API de WhatsApp.
        """
        # 1. Construye el cuerpo del mensaje de texto
        if payload.type != "text":
            raise HTTPException(400, "Este método solo soporta mensajes de tipo texto")
        
        message_data = self._build_text_message_data(payload)

        # 2. Llama a la API, pasando restaurant_id
        api_response = self._send_request("messages", message_data, payload.restaurant_id)

        # 3. Registra en la BD (opcional)
        current_ts = int(time.time())
        data_message = message.Message(
            id=api_response["messages"][0]["id"],
            from_="str",
            timestamp=str(current_ts),
            type="text",
            context=message.Context(id=payload.context_message_id),
            text=message.Text(body=payload.text.body if payload.text else ""),
        )

        user_id = self.db_message.get_user_by_wa_id(payload.to)
        phone_id = self.phone_number_id.get(payload.restaurant_id)
        if not phone_id:
            raise HTTPException(400, f"No encuentro phone_number_id para {phone_id}")
        self.db_message.create_message(
            data=data_message,
            user_id=user_id,
            employer_id=payload.employer_id,
            wa_user_id=payload.to,
            entry_id=phone_id  # ← aquí va el entry_id
        )

        return api_response["messages"][0]["id"]

    async def send_image_message(self, payload: message.SendMessage):
        """
        Envía un mensaje con una imagen (con o sin texto).
        """
        # 1. Guardar la imagen en el servidor
        file_path = self._save_file(payload.image.id, "images")

        # 2. Subir la imagen a Meta y obtener el file_id
        file_id = self._upload_file_to_meta(file_path, payload.restaurant_id)

        # 3. Construir el cuerpo del mensaje
        message_data = {
            "messaging_product": payload.messaging_product,
            "to": payload.to,
            "type": "image",
            "image": {"id": file_id},
        }
        if payload.text:
            message_data["text"] = {"body": payload.text.body}

        # 4. Enviar el mensaje a través de la API de Meta
        api_response = self._send_request("messages", message_data, payload.restaurant_id)

        # 5. Guardar el mensaje en la base de datos
        self.db_message.create_message(
            data=message.Message(
                id=api_response["messages"][0]["id"],
                from_="str",
                timestamp=str(int(time.time())),
                type="image",
                text=payload.text,
                image=message.Image(id=file_id),
            ),
            user_id=self.db_message.get_user_by_wa_id(payload.to),
            employer_id=payload.employer_id,
            wa_user_id=payload.to,
            entry_id=self.phone_number_id.get(payload.restaurant_id),
        )

        return api_response

    async def send_audio_message(self, payload: message.SendMessage):
        # Lógica para enviar mensajes con audios (con o sin texto)
        if payload.text:
            # Procesar texto junto con el audio
            pass
        else:
            # Procesar solo el audio
            pass

    async def send_document_message(self, payload: message.SendMessage):
        # Lógica para enviar mensajes con documentos (con o sin texto)
        if payload.text:
            # Procesar texto junto con el documento
            pass
        else:
            # Procesar solo el documento
            pass

    def _save_file(self, file_id: str, folder: str) -> str:
        """
        Guarda un archivo en el servidor.
        """
        directory = f"./uploads/{folder}"
        os.makedirs(directory, exist_ok=True)
        file_path = f"{directory}/{file_id}"
        # Aquí deberías implementar la lógica para guardar el archivo
        # Por ejemplo, descargarlo desde Meta o recibirlo desde el cliente
        return file_path

    def _upload_file_to_meta(self, file_path: str, restaurant_id: str) -> str:
        """
        Sube un archivo a Meta y devuelve el file_id.
        """
        phone_id = self.phone_number_id.get(restaurant_id)
        if not phone_id:
            raise HTTPException(400, f"No encuentro phone_number_id para {restaurant_id}")

        url = f"{self.graph_api_base}/{self.api_version}/{phone_id}/media"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        with open(file_path, "rb") as file:
            response = requests.post(url, headers=headers, files={"file": file})
        if response.status_code != 200:
            raise HTTPException(response.status_code, response.text)
        return response.json()["id"]

    # =================================================
    #   Métodos para recibir y procesar mensajes
    # =================================================

    def reseive_message(self, data: message.Webhook):
        
        print(data)

        message_type, data_id, status_dict = self.utils.identify_message_type(data=data)
        
        restaurants = {
        "448043808382821":"422125357649864",
        "642503312010167":'633892163131388'
        }
        
        
        if message_type == 'text':
            user_id, wa_user_id = self.db_message.create_user(data=data.entry[0].changes[0].value.contacts[0])
           
            # print(data)
            self.db_message.create_message(data=data.entry[0].changes[0].value.messages[0],user_id=user_id,employer_id=None,wa_user_id = wa_user_id,entry_id=restaurants[data.entry[0].id] )

      
        if (message_type in ["audio", "image", "document"]):
            result = self.utils.download_media_file(data_id)
            
        print(status_dict)

        statuses = {
            "sent":1,
            "delivered":2,
            "read":3,
            "failed":4
        }
        
        if message_type in ["sent","delivered","read","failed"] and status_dict:
            print(statuses[message_type])
            self.db_message.update_message_status(status_dict['id'],statuses[message_type],data.entry[0].changes[0].value.statuses[0],restaurants[data.entry[0].id])
            return statuses[message_type]

        return  message_type
    
    
    def get_last_message_contact(self, restaurant_id:int):
        query = 'SELECT * FROM messaging.vista_usuarios_ultimo_mensaje where restaurant_id = %s'
        result = self.db.fetch_all(query= query, params=[restaurant_id])
        return result
    
    def get_user_conversation(
        self,
        user_id: int,
        restaurant_id: int,
        offset: int = 0,
        limit: int = 10
    ):
        query = """
        WITH computed_messages AS (
            SELECT
                m_1.id,
                m_1.user_id,
                m_1.restaurant_id,
                m_1.content,
                m_1.created_at,
                m_1.current_status_id,
                m_1.employer_id,
                e.name       AS employer_name,
                m_1.wa_id,
                m_1.wa_timestamp,
                m_1.context_message_id,
                (to_timestamp(m_1.wa_timestamp::double precision)
                AT TIME ZONE 'America/Bogota') AS local_dt,
                to_char(
                (to_timestamp(m_1.wa_timestamp::double precision)
                AT TIME ZONE 'America/Bogota'),
                'HH12:MI AM'
                ) AS "time",
                to_char(
                (to_timestamp(m_1.wa_timestamp::double precision)
                AT TIME ZONE 'America/Bogota'),
                'DD/MM/YYYY'
                ) AS date,
                CASE
                WHEN (to_timestamp(m_1.wa_timestamp::double precision)
                        AT TIME ZONE 'America/Bogota')::date
                    = (now() AT TIME ZONE 'America/Bogota')::date THEN 'hoy'
                WHEN (to_timestamp(m_1.wa_timestamp::double precision)
                        AT TIME ZONE 'America/Bogota')::date
                    = ((now() AT TIME ZONE 'America/Bogota') - INTERVAL '1 day')::date THEN 'ayer'
                WHEN (to_timestamp(m_1.wa_timestamp::double precision)
                        AT TIME ZONE 'America/Bogota')::date
                    = ((now() AT TIME ZONE 'America/Bogota') - INTERVAL '2 days')::date THEN 'anteayer'
                ELSE NULL
                END AS day_label
            FROM messaging.message m_1
            LEFT JOIN employers e
            ON e.id = m_1.employer_id
        )
        SELECT
            u.id                AS user_id,
            row_to_json(u.*)    AS "user",

            /* lista de mensajes */
            (
            SELECT json_agg(msg)
            FROM (
                SELECT msg
                FROM (
                SELECT
                    json_build_object(
                    'message_data', json_build_object(
                                        'id',                m.id,
                                        'user_id',           m.user_id,
                                        'restaurant_id',     m.restaurant_id,
                                        'content',           m.content,
                                        'created_at',        m.created_at,
                                        'current_status_id', m.current_status_id,
                                        'employer_id',       m.employer_id,
                                        'employer_name',     m.employer_name,
                                        'wa_id',             m.wa_id,
                                        'wa_timestamp',      m.wa_timestamp,
                                        'context_message_id',m.context_message_id,
                                        'local_dt',          m.local_dt
                                    ),
                    'time',       m."time",
                    'date',       m.date,
                    'day_label',  m.day_label,
                    'contest',
                    CASE
                        WHEN m.context_message_id IS NOT NULL THEN (
                        SELECT json_build_object(
                            'message_data', row_to_json(c.*),
                            'time',         c."time",
                            'date',         c.date,
                            'day_label',    c.day_label
                        )
                        FROM computed_messages c
                        WHERE c.wa_id::text = m.context_message_id::text
                            AND c.restaurant_id = m.restaurant_id
                        LIMIT 1
                        )
                        ELSE NULL
                    END
                    ) AS msg,
                    m.wa_timestamp
                FROM computed_messages m
                WHERE m.user_id       = u.id
                    AND m.restaurant_id = %s
                ORDER BY m.wa_timestamp::bigint DESC
                LIMIT  %s
                OFFSET %s
                ) sub
                ORDER BY sub.wa_timestamp ASC
            ) final_sub
            ) AS messages,

            u.wa_user_id AS wa_id,

            /* hora del último mensaje en 12h Colombia */
            (
            SELECT cm."time"
            FROM computed_messages cm
            WHERE cm.user_id       = u.id
                AND cm.restaurant_id = %s
            ORDER BY cm.wa_timestamp::bigint DESC
            LIMIT 1
            ) AS time

        FROM messaging.user_message_contact u
        WHERE u.wa_user_id = %s;
        """

        result = self.db.execute_query(
            query=query,
            params=(
            restaurant_id,  # para filtrar mensajes
            limit,
            offset,
            restaurant_id,  # para obtener la hora del último mensaje
            user_id
            ),
            fetch=True
        )
        return result

    def read_message_status(
        self,
        message_id: int,
        restaurant_id:int
    ):
        query = """

        UPDATE messaging.message
        SET current_status_id = 3
        WHERE id = %s; 
        
        """
        result = self.db.execute_query(
            query=query,
            params=(message_id,),
            fetch=True
        )
        
        ws_url_all = f"wss://sockets-service.salchimonster.com/ws/salchimonster-{restaurant_id}"
        try:
            ws_all = websocket.create_connection(ws_url_all)
            ws_all.send("nuevo mensaje")
            ws_all.close()
        except Exception as e:
            print(f"Error al conectarse al socket {ws_url_all}: {e}")
        
        
        
        
        return result
