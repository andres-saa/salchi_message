import requests
from fastapi import HTTPException
from schema.message import message
from config.db import Db as dataBase
from datetime import datetime
from .utils.utils import Utils
import websocket  # Se importa la librería para manejo de sockets WebSocket

class DbMessageService:
    """
    Servicio para enviar mensajes de WhatsApp a través de la API de Facebook.
    """

    def __init__(self):
        # Inicializa tu conexión a la base de datos
        self.db = dataBase()
    
    def create_user(self, data: message.Contact):
        user_id = None
        wa_user_id = None
        query = self.db.cargar_archivo_sql('./sql/exist_user.sql')
        result = self.db.execute_query(query=query, params=[data.wa_id], fetch=True)
        print('result', result)
        if result:
            user_id = result[0]["id"]
            wa_user_id = result[0]["wa_user_id"]
        elif not result:
            # name, email, address, status_id
            query2 = self.db.cargar_archivo_sql('./sql/create_or_update_user.sql')
            params = [data.profile.name, data.wa_id]
            result2 = self.db.execute_query(query=query2, params=params, fetch=True)
            user_id = result2[0]["id"]
            wa_user_id = result2[0]["wa_user_id"]
        return user_id, wa_user_id
 
    def create_message(self, data: message.Message, user_id: int, employer_id: int, wa_user_id: str):
        # Ejecuta la consulta SQL para crear el mensaje en la DB
        query = self.db.cargar_archivo_sql('./sql/create_message.sql')
        context_id = data.context.id if data.context else None
        params = [data.id, user_id, data.text.body, context_id, 1, employer_id, data.timestamp]
        result_db = self.db.execute_query(query=query, params=params)

        # Conecta al socket reemplazando el número por el wa_user_id y envía el mensaje "actualizar"
        ws_url_wa = f"wss://sockets-service.salchimonster.com/ws/{wa_user_id}"
        try:
            ws = websocket.create_connection(ws_url_wa)
            ws.send("actualizar")
            ws.close()
        except Exception as e:
            # Aquí se puede registrar o manejar el error según convenga
            print(f"Error al conectarse al socket {ws_url_wa}: {e}")
        
        # Conecta al socket utilizando el parámetro "salchimonster-all" y envía el mensaje "nuevo mensaje"
        ws_url_all = "wss://sockets-service.salchimonster.com/ws/salchimonster-all"
        try:
            ws_all = websocket.create_connection(ws_url_all)
            ws_all.send("nuevo mensaje")
            ws_all.close()
        except Exception as e:
            print(f"Error al conectarse al socket {ws_url_all}: {e}")
        
        return result_db

    def update_message_status(self, message_id: str, status_id: int):
        # Consulta para obtener el estado actual del mensaje
        query_status = self.db.cargar_archivo_sql('./sql/get_message_status.sql')
        params_status = [message_id]
        status = self.db.execute_query(query=query_status, params=params_status, fetch=True)

        # Verifica si el mensaje existe
        if not status:
            # El mensaje no existe, no hacemos nada
            return None

        # Verifica si el estado actual es menor al nuevo estado
        if status[0]["current_status_id"] < status_id:
            update_query = self.db.cargar_archivo_sql('./sql/update_message_status.sql')
            update_params = [status_id, message_id]
            result = self.db.execute_query(query=update_query, params=update_params)
            return result
        
        # Si el estado no es menor, no se actualiza
        return None

    def get_user_by_wa_id(self, wa_id: str):
        user_id = None
        query = self.db.cargar_archivo_sql('./sql/exist_user.sql')
        result = self.db.execute_query(query=query, params=[wa_id], fetch=True)
        
        if result:
            user_id = result[0]["id"]
        return user_id
