from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from fastapi import Query
from schema.message import message
import requests
import json
from model.message.message import MessageService
from datetime import datetime


router = APIRouter()

@router.get("/webhook/messages")
def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
):
    return int(hub_challenge)

@router.post('/webhook/messages')
async def receive_message(payload: message.Webhook):
    # Convertir el modelo Pydantic a diccionario
    data = payload.dict()
    # print(data)
    
    
    
    message_instance = MessageService()

    
    
    message_instance.reseive_message(payload)
    
    # Generar un nombre de archivo único usando timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    filename = f"payload_{timestamp}.json"
    
    # Guardar el payload en el archivo JSON
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    return {"message": "Payload guardada exitosamente"}




@router.post("/webhook/send")
async def send_message (payload:message.SendMessage):
    message_instance = MessageService()
    result = await message_instance.send_message(payload)
    return result


## el contenido del mensaje debe ser proporcionado por el usuario de las credenciales estas rredenecioales son las 
## si no es sin o es esl ususario el euq el que lo determina 