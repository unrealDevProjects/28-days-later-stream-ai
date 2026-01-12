from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect, UploadFile, File, Query
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse, HTMLResponse
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
from external_storage import upload_to_external

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
                    if data is None:
                        # Conexión cerrada
                        break
                    if data.get("status") == "next_frame":
                        info = pipeline.Info()
                        params = await self.conn_manager.receive_json(user_id)
                        if params is None:
                            # Conexión cerrada
                            break
                        params = pipeline.InputParams(**params)
                        params = SimpleNamespace(**params.dict())
                        if info.input_mode == "image":
                            image_data = await self.conn_manager.receive_bytes(user_id)
                            if image_data is None or len(image_data) == 0:
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
                mode = data.get("mode", "url")  # 'url', 'dataurl', o 'external'
                external_service = data.get("service", "tmpfiles")  # Para modo external
                form_url = data.get("form_url")  # URL del formulario opcional
                
                if not image_data:
                    raise HTTPException(status_code=400, detail="No image data provided")
                
                # Para modo External (solo DigitalOcean ahora)
                if mode == "external" and external_service == "digitalocean":
                    cdn_url = upload_to_external(image_data, "digitalocean")
                    if cdn_url:
                        logging.info(f"Snapshot uploaded to DigitalOcean Spaces: {cdn_url}")
                        
                        # Si hay form_url, redirigir al middleware de Render
                        if form_url:
                            from urllib.parse import quote
                            middleware_url = "https://middleware-picture-28days.onrender.com"
                            photo_url = f"{middleware_url}/?image={quote(cdn_url)}"
                            logging.info(f"QR URL con middleware: {photo_url}")
                            
                            return JSONResponse({
                                "success": True,
                                "mode": "external",
                                "service": "digitalocean",
                                "photo_url": photo_url,  # URL del middleware con imagen del CDN
                                "cdn_url": cdn_url  # URL del CDN para referencia
                            })
                        else:
                            # Si no hay form_url, devolver directamente la URL del CDN
                            return JSONResponse({
                                "success": True,
                                "mode": "external",
                                "service": "digitalocean",
                                "photo_url": cdn_url
                            })
                    else:
                        # Fallback a modo local si falla
                        logging.warning(f"DigitalOcean upload failed, falling back to local storage")
                        mode = "url"
                
                # Para modo DataURL, devolver la imagen directamente en el QR
                if mode == "dataurl":
                    # Verificar tamaño (QR tiene límite práctico de ~3KB)
                    if len(image_data) > 4000:  # ~3KB en base64
                        # Comprimir imagen si es muy grande
                        from PIL import Image
                        import io
                        
                        # Decodificar imagen original
                        if "," in image_data:
                            img_b64 = image_data.split(",")[1]
                        else:
                            img_b64 = image_data
                        
                        img_bytes = base64.b64decode(img_b64)
                        img = Image.open(io.BytesIO(img_bytes))
                        
                        # Reducir tamaño
                        max_size = (200, 200)  # Tamaño máximo para QR
                        img.thumbnail(max_size, Image.Resampling.LANCZOS)
                        
                        # Recodificar con alta compresión
                        buffer = io.BytesIO()
                        img.save(buffer, format="JPEG", quality=30, optimize=True)
                        compressed_b64 = base64.b64encode(buffer.getvalue()).decode()
                        
                        # Crear data URL comprimida
                        dataurl = f"data:image/jpeg;base64,{compressed_b64}"
                    else:
                        # Usar imagen original si es pequeña
                        if not image_data.startswith("data:"):
                            dataurl = f"data:image/jpeg;base64,{image_data}"
                        else:
                            dataurl = image_data
                    
                    return JSONResponse({
                        "success": True,
                        "mode": "dataurl",
                        "photo_url": dataurl,
                        "size_kb": len(dataurl) / 1024
                    })
                
                # Modo URL tradicional (guardar en servidor)
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
                # Si hay form_url, redirigir al middleware de Render (que se encargará de mostrar HTML)
                if form_url:
                    from urllib.parse import quote
                    # Para modo local, también necesitamos subir a CDN o usar una URL accesible
                    # Por ahora, si hay form_url y es modo local, intentar usar el servidor
                    # Pero mejor usar el middleware que acepta URLs del CDN
                    middleware_url = "https://middleware-picture-28days.onrender.com"
                    
                    # Si está en modo external, ya tenemos cdn_url, usar esa
                    # Si no, construir URL local accesible
                    if SERVER_BASE_URL:
                        base_url = SERVER_BASE_URL.rstrip('/')
                        image_url_for_middleware = f"{base_url}/api/photo/{photo_id}/image"
                    else:
                        protocol = "https" if self.args.ssl_certfile else "http"
                        image_url_for_middleware = f"{protocol}://{LOCAL_IP}:{self.args.port}/api/photo/{photo_id}/image"
                    
                    photo_url = f"{middleware_url}/?image={quote(image_url_for_middleware)}"
                    logging.info(f"QR URL con middleware (modo local): {photo_url}")
                else:
                    # Si no hay form_url, construir URL normal del servidor
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
                    "mode": "url",
                    "photo_id": photo_id,
                    "photo_url": photo_url
                })
                
            except Exception as e:
                logging.error(f"Error saving snapshot: {e}")
                raise HTTPException(status_code=500, detail=str(e))
        
        # Endpoint para servir solo la imagen (sin HTML)
        @self.app.get("/api/photo/{photo_id}/image")
        async def get_photo_image(photo_id: str):
            filepath = os.path.join(SNAPSHOTS_DIR, f"{photo_id}.jpg")
            if not os.path.exists(filepath):
                raise HTTPException(status_code=404, detail="Photo not found")
            return FileResponse(filepath, media_type="image/jpeg")
        
        # Endpoint para servir las fotos guardadas
        @self.app.get("/api/photo/{photo_id}")
        async def get_photo(photo_id: str, formUrl: str = Query(None), cdnUrl: str = Query(None)):
            filepath = os.path.join(SNAPSHOTS_DIR, f"{photo_id}.jpg")
            
            # Si hay formUrl en los query params, devolver una página HTML que muestre la imagen y abra el formulario
            if formUrl:
                # Si hay cdnUrl, usar esa URL para la imagen (desde DigitalOcean CDN)
                # Si no, usar la imagen local
                if cdnUrl:
                    image_url = cdnUrl  # Usar URL del CDN
                else:
                    # Construir la URL completa de la imagen local (usando el endpoint de solo imagen)
                    if SERVER_BASE_URL:
                        base_url = SERVER_BASE_URL.rstrip('/')
                        image_url = f"{base_url}/api/photo/{photo_id}/image"
                    else:
                        protocol = "https" if self.args.ssl_certfile else "http"
                        image_url = f"{protocol}://{LOCAL_IP}:{self.args.port}/api/photo/{photo_id}/image"
                
                # Verificar que la imagen existe si es local (si es CDN, no podemos verificar aquí)
                if not cdnUrl and not os.path.exists(filepath):
                    raise HTTPException(status_code=404, detail="Photo not found")
                
                html_content = f"""
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Tu Foto Zombie</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            background: #000;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            font-family: Arial, sans-serif;
            padding: 20px;
        }}
        .container {{
            max-width: 100%;
            width: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }}
        img {{
            max-width: 100%;
            height: auto;
            display: block;
            border-radius: 10px;
            box-shadow: 0 4px 20px rgba(255, 0, 0, 0.3);
        }}
        .loading {{
            color: #fff;
            text-align: center;
            padding: 20px;
        }}
        .form-button {{
            background: linear-gradient(135deg, #dc2626 0%, #991b1b 100%);
            color: white;
            border: none;
            padding: 16px 32px;
            font-size: 18px;
            font-weight: bold;
            border-radius: 12px;
            cursor: pointer;
            box-shadow: 0 4px 15px rgba(220, 38, 38, 0.4);
            transition: all 0.3s ease;
            text-decoration: none;
            display: inline-block;
        }}
        .form-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(220, 38, 38, 0.6);
        }}
        .form-button:active {{
            transform: translateY(0);
        }}
        .form-button.hidden {{
            display: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <img src="{image_url}" alt="Tu Foto Zombie" onload="hideLoading()" onerror="showError()">
        <div class="loading" id="loading">Cargando foto...</div>
        <button id="formButton" class="form-button hidden" onclick="openForm()">
            📝 Abrir Formulario
        </button>
    </div>
    <script>
        let formOpened = false;
        let autoOpenAttempted = false;
        const formUrl = "{formUrl}";
        const formButton = document.getElementById('formButton');
        
        function openForm() {{
            if (!formUrl) return;
            
            if (!formOpened) {{
                formOpened = true;
                try {{
                    // Intentar abrir el formulario en una nueva pestaña
                    const formWindow = window.open(formUrl, '_blank');
                    
                    // Si el popup fue bloqueado (retorna null), mostrar el botón
                    if (!formWindow) {{
                        console.warn('Popup bloqueado por el navegador');
                        showButton();
                    }} else {{
                        // Ocultar el botón si se abrió correctamente
                        if (formButton) {{
                            formButton.classList.add('hidden');
                        }}
                    }}
                }} catch (e) {{
                    console.error('Error al abrir formulario:', e);
                    showButton();
                }}
            }}
        }}
        
        function showButton() {{
            if (formButton) {{
                formButton.classList.remove('hidden');
            }}
        }}
        
        function hideLoading() {{
            const loadingEl = document.getElementById('loading');
            if (loadingEl) {{
                loadingEl.style.display = 'none';
            }}
            // Abrir formulario después de que la imagen se carga
            if (!autoOpenAttempted) {{
                openForm();
            }}
        }}
        
        function showError() {{
            const loadingEl = document.getElementById('loading');
            if (loadingEl) {{
                loadingEl.textContent = 'Error al cargar la imagen';
            }}
            showButton();
        }}
        
        // Abrir el formulario automáticamente cuando se carga la página
        // Intentamos múltiples veces porque los navegadores móviles pueden bloquear popups
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', function() {{
                autoOpenAttempted = true;
                // Intentar inmediatamente después de DOM ready
                openForm();
                setTimeout(openForm, 100);
                setTimeout(openForm, 300);
                setTimeout(openForm, 500);
                // Si después de 1 segundo no se abrió, mostrar el botón
                setTimeout(function() {{
                    if (!formOpened) {{
                        showButton();
                    }}
                }}, 1000);
            }});
        }} else {{
            // Si ya está cargado, intentar inmediatamente
            autoOpenAttempted = true;
            openForm();
            setTimeout(openForm, 100);
            setTimeout(openForm, 300);
            setTimeout(openForm, 500);
            // Si después de 1 segundo no se abrió, mostrar el botón
            setTimeout(function() {{
                if (!formOpened) {{
                    showButton();
                }}
            }}, 1000);
        }}
        
        // También intentar cuando la página esté completamente cargada
        window.addEventListener('load', function() {{
            if (!autoOpenAttempted) {{
                autoOpenAttempted = true;
                openForm();
                setTimeout(openForm, 200);
                setTimeout(openForm, 400);
                // Si después de 1 segundo no se abrió, mostrar el botón
                setTimeout(function() {{
                    if (!formOpened) {{
                        showButton();
                    }}
                }}, 1000);
            }}
        }});
    </script>
</body>
</html>
"""
                return HTMLResponse(content=html_content)
            
            # Si no hay formUrl, devolver la imagen directamente
            return FileResponse(filepath, media_type="image/jpeg")

        if not os.path.exists("public"):
            os.makedirs("public")

        # Servir archivos estáticos
        # Usar html=True permite que FastAPI sirva index.html en rutas no encontradas (SPA routing)
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
