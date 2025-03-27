import requests
from fastapi import HTTPException
from schema.message import message
from config.db import Db as dataBase
from datetime import datetime
from . utils.utils import Utils

class DbMessageService:
    """
    Servicio para enviar mensajes de WhatsApp a través de la API de Facebook.
    """

    def __init__(self):
        # Inicializa tu conexión a la DB si la necesitas (ejemplo).
        self.db = dataBase()
        
        
        #INSERT INTO messaging.message(
	#id, user_id, content, context_message_id, created_at, current_status_id, employer_id)
	#VALUES (%s, %s, %s, %s, %s, %s, %s);
 
#  entry[0].changes[0].value.messages[0]
    def create_user (self, data:message.Contact):
        
        user_id = None
        query = self.db.cargar_archivo_sql('./sql/exist_user.sql')
        result = self.db.execute_query(query=query,params=[data.wa_id],fetch=True)
        
        if result:
            user_id=result[0]["id"] 

        if not result:
            #name, email, address, status_id
            query2 = self.db.cargar_archivo_sql('./sql/create_or_update_user.sql')
            params = [data.profile.name,data.wa_id]
            result2 = self.db.execute_query(query=query2, params=params,fetch=True)
            user_id=result2[0]["id"] 
        return user_id
 
    def create_message (self,data:message.Message, user_id:int,employer_id:int):
        query = self.db.cargar_archivo_sql('./sql/create_message.sql')
        params = [data.id, user_id, data.text.body, None, 1, employer_id]
        return self.db.execute_query(query=query,params=params)

    def update_message_status(self, message_id:str, status_id:int):
        query_status = self.db.cargar_archivo_sql('./sql/get_message_status.sql')
        params_status = [message_id]
        status = self.db.execute_query(query_status,params_status,fetch=True)
        if status[0]["current_status_id"] < status_id: 
            query = self.db.cargar_archivo_sql('./sql/update_message_status.sql')
            params = [status_id,message_id]
            result  = self.db.execute_query(query=query,params=params)
            return result

    def get_user_by_wa_id (self, wa_id = str):
        
        user_id = None
        query = self.db.cargar_archivo_sql('./sql/exist_user.sql')
        result = self.db.execute_query(query=query,params=[wa_id],fetch=True)
        
        if result:
            user_id=result[0]["id"] 
        return user_id