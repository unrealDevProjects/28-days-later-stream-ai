from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi import Request

import markdown2

import logging
import uuid
import time
from types import SimpleNamespace
import asyncio
import os
import time
import mimetypes
import torch
import base64
import socket
from datetime import datetime

from config import config, Args
from util import pil_to_frame, bytes_to_pil
from connection_manager import ConnectionManager, ServerFullException
from img2img import Pipeline

# fix mime error on windows
mimetypes.add_type("application/javascript", ".js")

# Carpeta para guardar snapshots
SNAPSHOTS_DIR = "snapshots"
if not os.path.exists(SNAPSHOTS_DIR):
    os.makedirs(SNAPSHOTS_DIR)

def get_local_ip():
    """Obtiene la IP local de la máquina en la red"""
    try:
        # Crear un socket y conectar a una IP externa para obtener nuestra IP local
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"

# Configuración de URL para QR
# Opciones:
#   1. SERVER_BASE_URL: URL completa externa (ej: https://midominio.ngrok.io)
#   2. SERVER_IP: IP específica (ej: 192.168.1.100)
#   3. Auto-detectar IP local
SERVER_BASE_URL = os.environ.get("SERVER_BASE_URL", None)
LOCAL_IP = os.environ.get("SERVER_IP", get_local_ip())

if SERVER_BASE_URL:
    print(f"📱 URL base para QR (externa): {SERVER_BASE_URL}")
else:
    print(f"📱 IP del servidor para QR (local): {LOCAL_IP}")

THROTTLE = 1.0 / 120
# logging.basicConfig(level=logging.DEBUG)


class App:
    def __init__(self, config: Args, pipeline):
        self.args = config
        self.pipeline = pipeline
        self.app = FastAPI()
        self.conn_manager = ConnectionManager()
        self.init_app()

    def init_app(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.websocket("/api/ws/{user_id}")
        async def websocket_endpoint(user_id: uuid.UUID, websocket: WebSocket):
            try:
                await self.conn_manager.connect(
                    user_id, websocket, self.args.max_queue_size
                )
                await handle_websocket_data(user_id)
            except ServerFullException as e:
                logging.error(f"Server Full: {e}")
            finally:
                await self.conn_manager.disconnect(user_id)
                logging.info(f"User disconnected: {user_id}")

        async def handle_websocket_data(user_id: uuid.UUID):
            if not self.conn_manager.check_user(user_id):
                return HTTPException(status_code=404, detail="User not found")
            last_time = time.time()
            try:
                while True:
                    if (
                        self.args.timeout > 0
                        and time.time() - last_time > self.args.timeout
                    ):
                        await self.conn_manager.send_json(
                            user_id,
                            {
                                "status": "timeout",
                                "message": "Your session has ended",
                            },
                        )
                        await self.conn_manager.disconnect(user_id)
                        return
                    data = await self.conn_manager.receive_json(user_id)
                    if data["status"] == "next_frame":
                        info = pipeline.Info()
                        params = await self.conn_manager.receive_json(user_id)
                        params = pipeline.InputParams(**params)
                        params = SimpleNamespace(**params.dict())
                        if info.input_mode == "image":
                            image_data = await self.conn_manager.receive_bytes(user_id)
                            if len(image_data) == 0:
                                await self.conn_manager.send_json(
                                    user_id, {"status": "send_frame"}
                                )
                                continue
                            params.image = bytes_to_pil(image_data)
                        await self.conn_manager.update_data(user_id, params)

            except Exception as e:
                logging.error(f"Websocket Error: {e}, {user_id} ")
                await self.conn_manager.disconnect(user_id)

        @self.app.get("/api/queue")
        async def get_queue_size():
            queue_size = self.conn_manager.get_user_count()
            return JSONResponse({"queue_size": queue_size})

        @self.app.get("/api/stream/{user_id}")
        async def stream(user_id: uuid.UUID, request: Request):
            try:

                async def generate():
                    while True:
                        last_time = time.time()
                        await self.conn_manager.send_json(
                            user_id, {"status": "send_frame"}
                        )
                        params = await self.conn_manager.get_latest_data(user_id)
                        if params is None:
                            # Si no hay parámetros nuevos, esperar un poco antes de continuar
                            await asyncio.sleep(0.01)  # 10ms de delay para evitar bucle infinito
                            continue
                        try:
                            image = pipeline.predict(params)
                            if image is None:
                                await asyncio.sleep(0.01)
                                continue
                            frame = pil_to_frame(image)
                            yield frame
                        except Exception as e:
                            logging.error(f"Error generating frame: {e}")
                            await asyncio.sleep(0.1)  # Esperar más tiempo si hay error
                            continue
                        if self.args.debug:
                            print(f"Time taken: {time.time() - last_time}")

                return StreamingResponse(
                    generate(),
                    media_type="multipart/x-mixed-replace;boundary=frame",
                    headers={"Cache-Control": "no-cache"},
                )
            except Exception as e:
                logging.error(f"Streaming Error: {e}, {user_id} ")
                return HTTPException(status_code=404, detail="User not found")

        # route to setup frontend
        @self.app.get("/api/settings")
        async def settings():
            info_schema = pipeline.Info.schema()
            info = pipeline.Info()
            if info.page_content:
                page_content = markdown2.markdown(info.page_content)

            input_params = pipeline.InputParams.schema()
            return JSONResponse(
                {
                    "info": info_schema,
                    "input_params": input_params,
                    "max_queue_size": self.args.max_queue_size,
                    "page_content": page_content if info.page_content else "",
                }
            )

        # Endpoint para guardar snapshot y devolver URL para QR
        @self.app.post("/api/snapshot")
        async def save_snapshot(request: Request):
            try:
                data = await request.json()
                image_data = data.get("image")  # Base64 encoded image
                
                if not image_data:
                    raise HTTPException(status_code=400, detail="No image data provided")
                
                # Remover el prefijo data:image/jpeg;base64, si existe
                if "," in image_data:
                    image_data = image_data.split(",")[1]
                
                # Generar ID único para la foto
                photo_id = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"
                filename = f"{photo_id}.jpg"
                filepath = os.path.join(SNAPSHOTS_DIR, filename)
                
                # Decodificar y guardar la imagen
                image_bytes = base64.b64decode(image_data)
                with open(filepath, "wb") as f:
                    f.write(image_bytes)
                
                # Construir URL de la foto
                # Si hay una URL base externa configurada, usarla (para ngrok, cloudflare, etc)
                # Si no, usar la IP local detectada
                if SERVER_BASE_URL:
                    # URL externa (ya incluye protocolo y dominio)
                    base_url = SERVER_BASE_URL.rstrip('/')
                    photo_url = f"{base_url}/api/photo/{photo_id}"
                else:
                    # IP local
                    protocol = "https" if self.args.ssl_certfile else "http"
                    photo_url = f"{protocol}://{LOCAL_IP}:{self.args.port}/api/photo/{photo_id}"
                
                logging.info(f"Snapshot saved: {filepath}, URL: {photo_url}")
                
                return JSONResponse({
                    "success": True,
                    "photo_id": photo_id,
                    "photo_url": photo_url
                })
                
            except Exception as e:
                logging.error(f"Error saving snapshot: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Endpoint para servir las fotos guardadas
        @self.app.get("/api/photo/{photo_id}")
        async def get_photo(photo_id: str):
            filepath = os.path.join(SNAPSHOTS_DIR, f"{photo_id}.jpg")
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail="Photo not found")
            return FileResponse(filepath, media_type="image/jpeg")

        if not os.path.exists("public"):
            os.makedirs("public")

        self.app.mount(
            "/", StaticFiles(directory="./frontend/public", html=True), name="public"
        )


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
torch_dtype = torch.float16
pipeline = Pipeline(config, device, torch_dtype)
app = App(config, pipeline).app

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=config.host,
        port=config.port,
        reload=config.reload,
        ssl_certfile=config.ssl_certfile,
        ssl_keyfile=config.ssl_keyfile,
    )
