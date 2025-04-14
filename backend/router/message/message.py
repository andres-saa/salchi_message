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

# 1. Definir esquema de seguridad
security = HTTPBearer()

# 2. Función para validar el token
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Esta función valida si el token Bearer es correcto.
    Puedes añadir aquí la lógica de validación que necesites,
    como consultar una base de datos, revisar un valor de configuración, etc.
    """
    # Ejemplo simple: comparar con un token fijo (NO usar en producción)
    # Reemplaza esto con tu propio token/lógica
    if credentials.credentials != "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJteS1hcGkiLCJpYXQiOjE2ODAxMjM0NTYsImV4cCI6MTY4MDEyNzE1NiwiYXR0ciI6InZhbG9yIn0.RHXJVLoqk7Z2NwClBLvZ3X2ryDgPQVtCq2l5hwwuMKG53tiNi2e66CUP1F3WpzNmY389_cWl7vsaEyj22ExAQA":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o faltante.",
        )
    return credentials.credentials

@router.get("/webhook/messages")
def verify_webhook(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    # Aquí no exigimos token; Facebook/WhatsApp no envía credenciales en la verificación
):
    # Retornar el hub_challenge para que Facebook/WhatsApp confirme el webhook
    return int(hub_challenge)


@router.post("/webhook/messages")
async def receive_message(
    payload: message.Webhook,
    # token: str = Depends(verify_token)  # Exigimos token para POST
):
    
    
    # Convertir el modelo Pydantic a diccionario
    data = payload.dict()
    
    # Instanciar el servicio y procesar el mensaje
    message_instance = MessageService()
    message_instance.reseive_message(payload)
    
    # Guardar el payload en un archivo JSON con timestamp
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S%f')
    filename = f"payload_{timestamp}.json"
    
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
    
    return {"message": "Payload guardada exitosamente"}



@router.post("/webhook/send")
async def send_message(
    payload: message.SendMessage,
    token: str = Depends(verify_token)  # Exigimos token para POST
):
    # Instanciar el servicio para enviar el mensaje
    message_instance = MessageService()
    result = await message_instance.send_message(payload)
    return result





@router.get("/last-contact-messages")
def  last_contact_message():
    message_instance = MessageService()
    result = message_instance.get_last_message_contact()
    return result


@router.get("/conversation/{user_id}/{offset}/{limit}")
def  last_contact_message( user_id:str,offset:int,limit:int):
    message_instance = MessageService()
    result = message_instance.get_user_conversation(user_id,offset,limit)
    return result



@router.get("/conversation-last-message/{user_id}")
def  last_contact_message( user_id:str):
    message_instance = MessageService()
    result = message_instance.get_user_conversation(user_id,0,1)
    return result