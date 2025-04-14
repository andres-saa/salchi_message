from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from router.message import message

app = FastAPI()

# Agrega CORS para permitir todas las solicitudes
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # Permitir cualquier origen
    allow_credentials=True,
    allow_methods=["*"],        # Permitir todos los métodos (GET, POST, PUT, etc.)
    allow_headers=["*"],        # Permitir todos los encabezados
)

app.include_router(message.router)
