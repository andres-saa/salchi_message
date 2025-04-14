from typing import List, Optional
from pydantic import BaseModel, Field

# ----- Modelos de Webhook entrantes -----

class Context(BaseModel):
    from_: Optional[str] = Field(None, alias="from")
    id: Optional[str] = None

class Text(BaseModel):
    body: str

class Audio(BaseModel):
    id: str
    mime_type: Optional[str] = None
    sha256: Optional[str] = None

class Image(BaseModel):
    id: str
    mime_type: Optional[str] = None
    sha256: Optional[str] = None

class Document(BaseModel):
    id: str
    mime_type: Optional[str] = None
    sha256: Optional[str] = None

# Modelo para ubicación
class Location(BaseModel):
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None

# Modelo para un contacto (WhatsApp puede enviar un arreglo de contactos)
class ContactItem(BaseModel):
    addresses: Optional[List[dict]] = None
    emails: Optional[List[dict]] = None
    name: Optional[dict] = None
    org: Optional[dict] = None
    phones: Optional[List[dict]] = None
    urls: Optional[List[dict]] = None

class ContactsMessage(BaseModel):
    contacts: Optional[List[ContactItem]]

class  Message(BaseModel):
    context: Optional[Context] = None
    from_: str = ''
    id: str
    timestamp: str
    type: str
    text: Optional[Text] = None
    audio: Optional[Audio] = None
    image: Optional[Image] = None
    document: Optional[Document] = None

    # Campos adicionales: ubicación y contactos
    location: Optional[Location] = None
    contacts: Optional[List[ContactItem]] = None

class Profile(BaseModel):
    name: str

class Contact(BaseModel):
    profile: Profile
    wa_id: str

class Metadata(BaseModel):
    display_phone_number: str
    phone_number_id: str

class Origin(BaseModel):
    type: str

class Conversation(BaseModel):
    id: str
    expiration_timestamp: Optional[str] = None
    origin: Optional[Origin] = None

class Pricing(BaseModel):
    billable: bool
    pricing_model: str
    category: str

class Status(BaseModel):
    id: str
    status: str
    timestamp: str
    recipient_id: str
    conversation: Optional[Conversation] = None
    pricing: Optional[Pricing] = None

class Value(BaseModel):
    messaging_product: str
    metadata: Metadata
    contacts: Optional[List[Contact]] = None
    messages: Optional[List[Message]] = None
    statuses: Optional[List[Status]] = None

class Change(BaseModel):
    value: Value
    field: str

class Entry(BaseModel):
    id: str
    changes: List[Change]

class Webhook(BaseModel):
    object: str
    entry: List[Entry]


# ----- Modelos para enviar mensajes (ejemplo) -----

# 1. Estructura de "language" en un template
class TemplateLanguage(BaseModel):
    code: str

# 2. Estructura de un template
class TemplateMessage(BaseModel):
    name: str
    language: TemplateLanguage
    components: Optional[List[dict]] = None

# 3. Mensaje de texto libre
class FreeMessage(BaseModel):
    body: str

# 4. Modelo general para envío de mensajes
class SendMessage(BaseModel):
    to: str
    messaging_product: str = "whatsapp"
    type: str  # "template", "text", "audio", "image", etc.
    template: Optional[TemplateMessage] = None
    text: Optional[FreeMessage] = None
    employer_id:int
    context_message_id: Optional[str] = None  # <-- Campo para incluir el ID de contexto

