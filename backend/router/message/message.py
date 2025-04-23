from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from fastapi import Query
from schema.message import message
import requests
import json
from model.message.message import MessageService
from datetime import datetime
from fastapi.responses import FileResponse
import os

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

    # Verificar el tipo de mensaje y procesarlo en consecuencia
    if payload.type == "text" and payload.text:
        # Mensaje de texto simple
        result = await message_instance.send_message(payload)
    elif payload.type == "image" and payload.image:
        # Imagen con o sin texto
        result = await message_instance.send_image_message(payload)
    elif payload.type == "audio" and payload.audio:
        # Audio con o sin texto
        result = await message_instance.send_audio_message(payload)
    elif payload.type == "document" and payload.document:
        # Documento con o sin texto
        result = await message_instance.send_document_message(payload)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de mensaje no soportado o datos faltantes.",
        )

    return result





@router.get("/last-contact-messages/{restaurant_id}")
def  last_contact_message(restaurant_id:int):
    message_instance = MessageService()
    result = message_instance.get_last_message_contact(restaurant_id)
    return result


@router.get("/conversation/{restaurant_id}/{user_id}/{offset}/{limit}/")
def  last_contact_message( user_id:str,offset:int,limit:int,restaurant_id:int):
    message_instance = MessageService()
    result = message_instance.get_user_conversation(user_id,restaurant_id,offset,limit)
    return result



@router.get("/conversation-last-message/{restaurant_id}/{user_id}")
def  last_contact_message(restaurant_id:int, user_id:str):
    message_instance = MessageService()
    result = message_instance.get_user_conversation(user_id,restaurant_id,0,1)
    return result



@router.post("/read-message/{message_id}/{restaurant_id}")
def  last_contact_message(message_id:int,restaurant_id:int):
    message_instance = MessageService()
    result = message_instance.read_message_status(message_id,restaurant_id)
    return result


@router.get("/files/{file_type}/{file_id}")
def get_file(file_type: str, file_id: str):
    """
    Endpoint para obtener un archivo guardado en el servidor.
    """
    file_path = f"./uploads/{file_type}/{file_id}"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    return FileResponse(file_path)