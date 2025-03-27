from fastapi import FastAPI
from router.message import message


app = FastAPI()


app.include_router(message.router)