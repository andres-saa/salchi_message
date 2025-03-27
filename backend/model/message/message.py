import requests
from fastapi import HTTPException
from schema.message import message
from config.db import Db as dataBase
from datetime import datetime
from . utils.utils import Utils
from .  db_message import DbMessageService
class MessageService:
    """
    Servicio para enviar mensajes de WhatsApp a través de la API de Facebook.
    """

    def __init__(self):
        # Inicializa tu conexión a la DB si la necesitas (ejemplo).
        self.db = dataBase()
        self.utils = Utils()
        # Configura estas variables de entorno o cámbialas según tu caso.
        self.phone_number_id = "504763346063951"
        self.access_token = "EAAafKCUnI2cBOZBLxrZCxVsy9H3aj2ZBZBZCloZBZCzcQhomwtiFDRL5ZCd6lsRsWRZCThKmF8jGvvdOFSZAwgJIOAp2wlCw8bZAmJWwjTCZC4PFRdnNxYVphH3O6LVbGRMhj26AYppn68CCODC5df6CxGAwOlMlCpCWclinUd9YGpIgotHp8j2hC3ULEptQzcf1woCbcze9HbvUvh2ZCx3ZCczRkVE3QAowZDZD"
        
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
        Construye el cuerpo de la solicitud para un mensaje de tipo 'text'.
        """
        if not payload.text:
            raise HTTPException(
                status_code=400,
                detail="Se requiere el contenido de texto para mensajes libres",
            )

        return {
            "messaging_product": payload.messaging_product,
            "to": payload.to,
            "type": "text",
            "text": {"body": payload.text.body},
        }

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
 

        data_message = message.Message(
            id = api_response['messages'][0]["id"],
            from_ =  'str',
            timestamp = 'str',
            type = 'str',
            text = message.Text(
                body = payload.text.body,
            )
            
        )
        user = self.db_message.get_user_by_wa_id(payload.to)
        
        self.db_message.create_message(data=data_message,user_id=user,employer_id=payload.employer_id)

        return  api_response['messages'][0]["id"]
          
        

    # =================================================
    #   Métodos para recibir y procesar mensajes
    # =================================================

    def reseive_message(self, data: message.Webhook):
        
        

        message_type, data_id, status_dict = self.utils.identify_message_type(data=data)
        
        if message_type == 'text':
            user_id = self.db_message.create_user(data=data.entry[0].changes[0].value.contacts[0])
            self.db_message.create_message(data=data.entry[0].changes[0].value.messages[0],user_id=user_id,employer_id=None)

      
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
       