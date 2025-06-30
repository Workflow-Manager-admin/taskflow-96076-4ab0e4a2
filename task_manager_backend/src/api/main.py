from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from . import models
# To initialize DB at startup, you may add:
# from .models import init_db
# @app.on_event("startup")
# def on_startup(): init_db()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def health_check():
    return {"message": "Healthy"}
