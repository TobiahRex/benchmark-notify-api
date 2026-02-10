from fastapi import FastAPI

from notify_api.routes import router

app = FastAPI(title="Notify API", version="0.1.0")
app.include_router(router)
