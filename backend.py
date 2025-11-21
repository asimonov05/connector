import socketio
import uvicorn
from fastapi import FastAPI
from loguru import logger

from src import Messenger
from src.config import get_settings
from src.kernelwrapper import KernelWrapper
from src.routes import router

if __name__ == "__main__":
    settings = get_settings()
    logger.info(f"IPython config - {settings.dict()}")
    wrapper = KernelWrapper()
    messenger = Messenger(wrapper)
    app = FastAPI()
    app.include_router(router, tags=["Service"])
    socketio_app = socketio.ASGIApp(messenger.sio, app)
    uvicorn.run(socketio_app, host=settings.SOCKETIO_HOST, port=settings.SOCKETIO_PORT)
