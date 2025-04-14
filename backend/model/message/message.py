import requests
from fastapi import HTTPException
from schema.message import message
from config.db import Db as dataBase
from datetime import datetime
from . utils.utils import Utils
import time
from .  db_message import DbMessageService
import websocket  # Se importa la librería para manejo de sockets WebSocket


class MessageService:
    """
    Servicio para enviar mensajes de WhatsApp a través de la API de Facebook.
    """

    def __init__(self):
        # Inicializa tu conexión a la DB si la necesitas (ejemplo).
        self.db = dataBase()
        self.utils = Utils()
        # Configura estas variables de entorno o cámbialas según tu caso.
        self.phone_number_id = "422125357649864"
        self.access_token = "EAAafKCUnI2cBOwRrVRGF8OtdPcubRrO8ZAZCMZAvApcyTpzub1QqwOvbN5XZA6IV2eLxmZCZCBC5FSZCkTzio0cp5dKDIN9VVTcoO1CLieFPZCQlXYEZCK9jPblGfZAXKRelDnIkOKqDnFYluIaFZAU3u9i7WmcKviY5bbNWewlKJLa46plXMdU9fGwZATMu8vqvLhuZA8Kf8QAG84yhKg7j48zMsdJqZBiAZDZD"
        
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
            raise HTTPException(
                status_code=400,
                detail="Se requiere la data del template para mensajes de plantilla",
            )

        return {
            "messaging_product": payload.messaging_product,
            "to": payload.to,
            "type": "template",
            "template": {
                "name": payload.template.name,
                # Aquí se usa 'payload.template.language.code'
                "language": {"code": payload.template.language.code},
                "components": payload.template.components or []
            },
        }


    def _build_text_message_data(self, payload: message.SendMessage) -> dict:
        """
        Construye el cuerpo de la solicitud para un mensaje de tipo 'text' (WhatsApp).
        """
        if not payload.text:
            raise HTTPException(
                status_code=400,
                detail="Se requiere el contenido de texto para mensajes libres",
            )

        # Estructura básica del mensaje de texto
        data = {
            "messaging_product": payload.messaging_product,
            "to": payload.to,
            "type": "text",
            "text": {
                "body": payload.text.body
            },
        }

        # Si existe un mensaje de contexto, lo añadimos
        if payload.context_message_id:
            data["context"] = {
                "message_id": payload.context_message_id
            }

        return data

    def _send_request(self, endpoint: str, data: dict) -> dict:
        """
        Envía la solicitud POST a la API de Facebook. 
        Lanza HTTPException si la respuesta no es 200.
        """
        # Unificamos la URL de envío de mensajes usando la versión y el phone_number_id
        url = f"{self.graph_api_base}/{self.api_version}/{self.phone_number_id}/{endpoint}"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json=data)

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return response.json()
    

    async def send_message(self, payload: message.SendMessage) -> dict:
        """
        Envía un mensaje a través de la API de Facebook.
        Soporta los tipos de mensaje 'template' y 'text'.
        """
        if payload.type == "template":
            message_data = self._build_template_message_data(payload)
        elif payload.type == "text":
            message_data = self._build_text_message_data(payload)
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de mensaje no soportado. Utiliza 'template' o 'text'",
            )

        api_response = self._send_request(endpoint="messages", data=message_data)

        # Generamos el timestamp actual en segundos
        current_timestamp = int(time.time())

        data_message = message.Message(
            id=api_response['messages'][0]["id"],
            from_='str',
            timestamp=str(current_timestamp),  # Convertimos a string para almacenarlo
            type='str',
            context=message.Context(
                id = payload.context_message_id ) ,
            text=message.Text(
                body=payload.text.body,
            )
        )

        print('api', api_response)
        user = self.db_message.get_user_by_wa_id(payload.to)
        
        self.db_message.create_message(data=data_message, user_id=user, employer_id=payload.employer_id, wa_user_id=payload.to)

        return api_response['messages'][0]["id"]  

    # =================================================
    #   Métodos para recibir y procesar mensajes
    # =================================================

    def reseive_message(self, data: message.Webhook):
        
        

        message_type, data_id, status_dict = self.utils.identify_message_type(data=data)
        
        if message_type == 'text':
            user_id, wa_user_id = self.db_message.create_user(data=data.entry[0].changes[0].value.contacts[0])
            # print(data)
            self.db_message.create_message(data=data.entry[0].changes[0].value.messages[0],user_id=user_id,employer_id=None,wa_user_id = wa_user_id)

      
        if (message_type in ["audio", "image", "document"]):
            result = self.utils.download_media_file(data_id)
            
        print(message_type)

        statuses = {
            "sent":1,
            "delivered":2,
            "read":3
        }
        
        if message_type in ["sent","delivered","read"] and status_dict:
            print(statuses[message_type])
            self.db_message.update_message_status(status_dict['id'],statuses[message_type])
            return statuses[message_type]
        
        return  message_type
    
    
    def get_last_message_contact(self):
        query = 'SELECT * FROM messaging.vista_usuarios_ultimo_mensaje'
        result = self.db.fetch_all(query= query)
        return result
    
        
    def get_user_conversation(self, user_id: int, offset: int = 0, limit: int = 10):
        query = """
        WITH computed_messages AS (
            SELECT m_1.id,
                m_1.user_id,
                m_1.content,
                m_1.created_at,
                m_1.current_status_id,
                m_1.employer_id,
                m_1.wa_id,
                m_1.wa_timestamp,
                m_1.context_message_id,
                (to_timestamp(m_1.wa_timestamp::double precision) AT TIME ZONE 'America/Bogota'::text) AS local_dt,
                to_char((to_timestamp(m_1.wa_timestamp::double precision) AT TIME ZONE 'America/Bogota'::text), 'HH12:MI AM'::text) AS "time",
                to_char((to_timestamp(m_1.wa_timestamp::double precision) AT TIME ZONE 'America/Bogota'::text), 'DD/MM/YYYY'::text) AS date,
                CASE
                    WHEN (to_timestamp(m_1.wa_timestamp::double precision) AT TIME ZONE 'America/Bogota'::text)::date = (now() AT TIME ZONE 'America/Bogota'::text)::date THEN 'hoy'::text
                    WHEN (to_timestamp(m_1.wa_timestamp::double precision) AT TIME ZONE 'America/Bogota'::text)::date = ((now() AT TIME ZONE 'America/Bogota'::text) - '1 day'::interval)::date THEN 'ayer'::text
                    WHEN (to_timestamp(m_1.wa_timestamp::double precision) AT TIME ZONE 'America/Bogota'::text)::date = ((now() AT TIME ZONE 'America/Bogota'::text) - '2 days'::interval)::date THEN 'anteayer'::text
                    ELSE NULL::text
                END AS day_label
            FROM messaging.message m_1
        )
        SELECT u.id AS user_id,
            row_to_json(u.*) AS "user",
            (
                SELECT json_agg(msg)
                FROM (
                -- Reordeno los mensajes para que queden en orden ascendente
                SELECT msg
                FROM (
                    -- Selecciono los últimos mensajes (orden descendente)
                    SELECT 
                    json_build_object(
                        'message_data', row_to_json(m.*),
                        'time', m."time",
                        'date', m.date,
                        'day_label', m.day_label,
                        'contest',
                        CASE
                        WHEN m.context_message_id IS NOT NULL THEN (
                            SELECT json_build_object(
                                    'message_data', row_to_json(c.*),
                                    'time', c."time",
                                    'date', c.date,
                                    'day_label', c.day_label
                                    )
                            FROM computed_messages c
                            WHERE c.wa_id::text = m.context_message_id::text
                            LIMIT 1
                        )
                        ELSE NULL::json
                        END
                    ) AS msg,
                    m.wa_timestamp
                    FROM computed_messages m
                    WHERE m.user_id = u.id
                    ORDER BY m.wa_timestamp::bigint DESC
                    LIMIT %s OFFSET %s
                ) sub
                ORDER BY sub.wa_timestamp ASC
                ) final_sub
            ) AS messages,
            u.wa_user_id AS wa_id
        FROM messaging.user_message_contact u
        WHERE u.wa_user_id = %s;
        """
        # Orden de parámetros: (limit, offset, user_id)
        result = self.db.execute_query(query=query, params=(limit, offset, user_id), fetch=True)
        return result



        # get_user_conversation