# Guía de Instalación - Demo Img2Img en Windows

Esta guía te ayudará a configurar y ejecutar el demo img2img de StreamDiffusion en otro ordenador Windows.

## 🎯 Dos Formas de Instalar

### Opción A: Docker (Recomendado - Más Fácil) 🐳
- ✅ Instala **TODO automáticamente** (Python, Node.js, dependencias)
- ✅ No necesitas instalar Python ni Node.js manualmente
- ✅ Entorno aislado, sin conflictos con otras instalaciones
- ✅ Funciona igual en cualquier ordenador
- ⚠️ Requiere Docker Desktop instalado
- **Ver sección:** [🐳 Instalación con Docker](#-instalación-con-docker-recomendado-para-evitar-problemas)

### Opción B: Instalación Manual 💻
- ✅ Más control sobre el entorno
- ✅ No requiere Docker
- ❌ Necesitas instalar Python 3.10, Node.js, y todas las dependencias manualmente
- ❌ Puede haber conflictos con otras versiones instaladas
- **Ver sección:** [🚀 Pasos de Instalación (Sin Docker)](#-pasos-de-instalación-sin-docker)

## 📋 Requisitos del Sistema

### Software Necesario

1. **Python 3.10** (obligatorio)
   - Descarga desde: https://www.python.org/downloads/
   - ⚠️ **IMPORTANTE**: Debe ser Python 3.10 exactamente (no 3.9, no 3.11)

2. **Node.js 18 o superior**
   - Descarga desde: https://nodejs.org/
   - Verifica la instalación: `node --version`

3. **Drivers NVIDIA** (para GPU NVIDIA)
   - ⚠️ **IMPORTANTE:** Solo necesitas los drivers NVIDIA (NO el CUDA Toolkit completo)
   - Si `nvidia-smi` funciona, ya tienes lo necesario
   - Los drivers se instalan automáticamente con la GPU o desde: https://www.nvidia.com/Download/index.aspx
   - **Cómo verificar:** Ver sección [🔍 Verificar Instalación de CUDA](#-verificar-instalación-de-cuda) más abajo
   - **Nota:** PyTorch trae sus propias librerías CUDA, no necesitas instalar el CUDA Toolkit completo

4. **Docker Desktop** (solo si usas Docker)
   - Descarga desde: https://www.docker.com/products/docker-desktop/
   - Incluye WSL2 automáticamente
   - Necesitas NVIDIA Container Toolkit para GPU (ver sección Docker)

5. **Git** (opcional, pero recomendado)
   - Descarga desde: https://git-scm.com/download/win

### Hardware Necesario

- **GPU NVIDIA** con soporte CUDA (RTX serie recomendada)
- Mínimo 8GB VRAM (16GB recomendado para mejor rendimiento)
- Al menos 20GB de espacio libre en disco (para modelos y dependencias)

## 📦 Qué Copiar al Otro Ordenador

### Opción 1: Copiar Carpeta Completa (Recomendado)

Copia toda la carpeta `StreamDiffusion` completa, incluyendo:
- ✅ Todo el código fuente (`src/`, `demo/`, `examples/`, etc.)
- ✅ Archivos de configuración (`.gitignore`, `setup.py`, `pyproject.toml`)
- ✅ `requirements.txt` y `package.json` (definen las dependencias)
- ✅ Si ya compilaste el frontend: carpeta `frontend/build/` o `frontend/dist/` (si existe)

**⚠️ NO copies aunque existan:**
- ❌ **`node_modules/`** - Aunque esté instalado, contiene binarios específicos del sistema operativo y puede causar problemas. Es mejor reinstalar con `npm install`.
- ❌ **`.venv/` o entornos virtuales** - Contiene rutas absolutas específicas de tu sistema actual. NO funcionará en otro ordenador.
- ❌ **`__pycache__/`** - Archivos compilados de Python específicos del sistema.
- ❌ **`engines/` de TensorRT** - Son específicos de la GPU y modelo exacto. Si cambias de GPU, no funcionarán.
- ❌ **`.cache/` de Hugging Face** - Los modelos se pueden copiar, pero ocupan mucho espacio. Mejor dejarlos descargar automáticamente.

**💡 Nota:** Si ya tienes el frontend compilado (`frontend/build/` o `frontend/dist/`), SÍ puedes copiarlo y ahorrarás tiempo de compilación.

### Opción 2: Solo el Demo (Más Ligero)

Si solo quieres el demo img2img, copia:
```
demo/realtime-img2img/
```
Pero necesitarás instalar StreamDiffusion como paquete.

### ⚠️ ¿Por qué NO copiar node_modules o .venv?

Aunque técnicamente podrías copiar estas carpetas, **NO es recomendable** porque:

1. **`node_modules/`**: 
   - Contiene binarios nativos compilados para tu sistema específico
   - Puede tener problemas de compatibilidad entre diferentes versiones de Windows
   - Ocupa mucho espacio (cientos de MB)
   - Es más rápido y seguro reinstalar con `npm install`

2. **`.venv/` (entorno virtual Python)**:
   - Contiene rutas absolutas como `C:\Users\ktilouni\...` que no existirán en el otro ordenador
   - Los scripts de activación apuntan a rutas específicas
   - **Definitivamente NO funcionará** si cambias de usuario o ruta

3. **`engines/` de TensorRT**:
   - Son específicos de la GPU exacta (modelo, VRAM, drivers)
   - Si cambias de GPU o actualizas drivers, necesitarás reconstruirlos
   - Ocupan varios GB de espacio

**✅ Lo que SÍ puedes copiar:**
- Si ya compilaste el frontend (`frontend/build/` o `frontend/dist/`), cópialo y ahorrarás tiempo
- Los modelos de Hugging Face (si quieres ahorrar ancho de banda), pero ocupan mucho espacio

## 🔍 Verificar Instalación de CUDA

**⚠️ IMPORTANTE:** Para usar PyTorch con CUDA, NO necesitas instalar el CUDA Toolkit completo. Solo necesitas los **drivers NVIDIA** (que ya tienes si `nvidia-smi` funciona).

### ¿Cuál es la diferencia?

1. **Drivers NVIDIA** (lo que tienes):
   - Instalados con los drivers de tu GPU
   - Permiten que PyTorch use la GPU
   - Se verifican con `nvidia-smi`
   - ✅ **ESTO ES SUFICIENTE para PyTorch**

2. **CUDA Toolkit completo** (opcional):
   - Incluye compilador `nvcc` y librerías de desarrollo
   - Solo necesario si vas a compilar código CUDA desde cero
   - PyTorch trae sus propias librerías CUDA incluidas
   - ❌ **NO es necesario para este proyecto**

### Método 1: Verificar drivers NVIDIA (Lo más importante)

```powershell
# Ver información de la GPU y drivers NVIDIA
nvidia-smi
```

Si funciona, verás:
- Modelo de tu GPU NVIDIA
- Versión del driver NVIDIA
- Versión de CUDA soportada por el driver (ej: CUDA 13.x)

**✅ Si `nvidia-smi` funciona, ya tienes lo necesario para PyTorch.**

### Método 2: Verificar CUDA Toolkit (Opcional)

```powershell
# Verificar si el CUDA Toolkit está instalado
nvcc --version
```

**Si NO funciona** (comando no reconocido):
- ✅ **Esto es NORMAL y está bien**
- PyTorch funcionará igual porque trae sus propias librerías CUDA
- Solo necesitarías el Toolkit si vas a compilar código CUDA personalizado

**Si SÍ funciona**, verás algo como:
```
nvcc: NVIDIA (R) Cuda compiler driver
Copyright (c) 2005-2023 NVIDIA Corporation
Cuda compilation tools, release 12.1, V12.1.105
```

### Método 3: Verificar desde Python (después de instalar PyTorch)

```powershell
python -c "import torch; print(f'CUDA disponible: {torch.cuda.is_available()}'); print(f'Versión CUDA: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}')"
```

Este es el método más confiable para verificar que PyTorch puede usar tu GPU.

### Método 4: Verificar ruta de instalación (Opcional)

```powershell
# Verificar si existe la carpeta de CUDA Toolkit
dir "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA"
```

Si existe, listará las versiones instaladas (ej: `v11.8`, `v12.1`).

### ¿Qué versión de PyTorch instalar?

**Basado en lo que muestra `nvidia-smi`:**

- Si muestra **CUDA 11.x** → Usa PyTorch con `cu118` (compatible hacia atrás)
- Si muestra **CUDA 12.x o 13.x** → Usa PyTorch con `cu121` (compatible hacia atrás)

**Ejemplo:** Si `nvidia-smi` muestra "CUDA Version: 13.0", instala PyTorch con `cu121`:
```powershell
pip3 install torch==2.1.0 torchvision==0.16.0 xformers --index-url https://download.pytorch.org/whl/cu121
```

### Resumen

- ✅ **Tienes drivers NVIDIA** (`nvidia-smi` funciona) → Ya puedes usar PyTorch con GPU
- ❌ **No tienes CUDA Toolkit** (`nvcc` no funciona) → **NO es problema**, PyTorch trae sus librerías
- 📦 **Instala PyTorch** con la versión CUDA apropiada según lo que muestre `nvidia-smi`

## 🐳 Instalación con Docker (Recomendado para evitar problemas)

**✅ Ventajas de Docker:**
- Instala **TODO automáticamente** (Python 3.10, Node.js, dependencias, frontend compilado)
- Entorno aislado y reproducible
- No necesitas instalar Python, Node.js ni CUDA Toolkit manualmente
- Funciona igual en cualquier ordenador con Docker
- No contamina tu sistema con dependencias

**❌ Requisitos para Docker:**
- Docker Desktop instalado (con soporte WSL2 en Windows)
- GPU NVIDIA con drivers instalados (`nvidia-smi` debe funcionar)
- Docker con soporte GPU (NVIDIA Container Toolkit)

### Paso 1: Instalar Docker Desktop en Windows

1. **Descarga Docker Desktop:**
   - https://www.docker.com/products/docker-desktop/
   - Instala Docker Desktop para Windows
   - Durante la instalación, habilita WSL2 (se hace automáticamente)

2. **Verifica la instalación:**
   ```powershell
   docker --version
   docker-compose --version
   ```

3. **Instala NVIDIA Container Toolkit (para GPU):**
   
   **Opción A: Instalador automático (Windows)**
   - Descarga desde: https://github.com/NVIDIA/nvidia-container-toolkit/releases
   - O usa: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html#docker-desktop
   
   **Opción B: Manual (más complejo)**
   - Sigue: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html

4. **Verifica que Docker puede usar la GPU:**
   ```powershell
   docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
   ```
   
   Si funciona, verás la salida de `nvidia-smi` desde dentro del contenedor.

### Paso 2: Construir y Ejecutar el Demo con Docker

**Opción 1: Docker Build + Run (Recomendado)**

```powershell
# Navegar a la carpeta del demo
cd demo\realtime-img2img

# Construir la imagen Docker (esto puede tardar 20-30 minutos la primera vez)
# Descarga Ubuntu, Python, Node.js, compila frontend, instala dependencias
docker build -t streamdiffusion-img2img .

# Ejecutar el contenedor con GPU
docker run --gpus all -p 7860:7860 streamdiffusion-img2img
```

**Opción 2: Docker Compose (Más fácil para configurar)**

Crea un archivo `docker-compose.yml` en la carpeta `demo/realtime-img2img/`:

```yaml
version: '3.8'

services:
  streamdiffusion:
    build: .
    ports:
      - "7860:7860"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      # Persistir modelos de Hugging Face (opcional, ahorra espacio)
      - huggingface_cache:/home/user/.cache/huggingface
      # Persistir engines de TensorRT (opcional)
      - tensorrt_engines:/home/user/app/demo/realtime-img2img/engines
    environment:
      - ACCELERATION=tensorrt
      - ENGINE_DIR=/home/user/app/demo/realtime-img2img/engines
      - PORT=7860
      - HOST=0.0.0.0

volumes:
  huggingface_cache:
  tensorrt_engines:
```

Luego ejecuta:
```powershell
# Construir y ejecutar
docker-compose up --build

# O en segundo plano
docker-compose up -d --build
```

**Para detener:**
```powershell
# Si está en primer plano: Ctrl+C
# Si está en segundo plano:
docker-compose down
```

### Paso 3: Acceder al Demo

Una vez que el contenedor esté corriendo, abre en tu navegador:
- `http://localhost:7860`

### Notas Importantes sobre Docker

- ⏱️ **Primera construcción:** Puede tardar 20-30 minutos (descarga Ubuntu, Python, Node.js, compila todo)
- 💾 **Modelos:** Se descargan automáticamente dentro del contenedor la primera vez
- 🔄 **Reconstruir:** Si cambias código, necesitas reconstruir: `docker-compose build` o `docker build`
- 📦 **Volúmenes:** Los modelos y engines se pueden persistir con volúmenes (ver docker-compose.yml arriba)
- 🐛 **Debug:** Para ver logs: `docker-compose logs -f` o `docker logs <container_id>`
- 🔧 **Entrar al contenedor:** `docker exec -it <container_id> bash`

### Solución de Problemas Docker

**Error: "nvidia-container-toolkit not found"**
- Instala NVIDIA Container Toolkit (ver Paso 1.3 arriba)

**Error: "WSL 2 installation is incomplete"**
- Instala WSL2: `wsl --install` en PowerShell como administrador
- Reinicia el ordenador

**Error: "Cannot connect to Docker daemon"**
- Asegúrate de que Docker Desktop está corriendo
- Verifica: `docker ps`

**El contenedor se detiene inmediatamente**
- Ver logs: `docker logs <container_id>`
- Verifica que la GPU está disponible: `docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi`

## 🚀 Pasos de Instalación (Sin Docker)

### Paso 1: Preparar el Entorno Python

```powershell
# Crear entorno virtual
python -m venv .venv

# Activar entorno virtual (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Si tienes problemas con la política de ejecución, ejecuta primero:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Paso 2: Instalar PyTorch

**Para CUDA 11.8:**
```powershell
pip3 install torch==2.1.0 torchvision==0.16.0 xformers --index-url https://download.pytorch.org/whl/cu118
```

**Para CUDA 12.1:**
```powershell
pip3 install torch==2.1.0 torchvision==0.16.0 xformers --index-url https://download.pytorch.org/whl/cu121
```

### Paso 3: Instalar StreamDiffusion

**Si copiaste toda la carpeta del proyecto:**

```powershell
# Desde la raíz del proyecto StreamDiffusion
python setup.py develop
pip install streamdiffusion[tensorrt]
python -m streamdiffusion.tools.install-tensorrt
```

**Si solo copiaste el demo:**

```powershell
# Instalar StreamDiffusion desde GitHub
pip install git+https://github.com/cumulo-autumn/StreamDiffusion.git@main#egg=streamdiffusion[tensorrt]
python -m streamdiffusion.tools.install-tensorrt
```

**Para Windows, también necesitas:**
```powershell
pip install --force-reinstall pywin32
```

### Paso 4: Instalar Dependencias del Demo

```powershell
# Navegar a la carpeta del demo
cd demo\realtime-img2img

# Instalar dependencias de Python
pip install -r requirements.txt
```

### Paso 5: Instalar y Compilar Frontend

**Si ya copiaste el frontend compilado** (carpeta `build/` o `dist/`), puedes saltar este paso.

**Si NO tienes el frontend compilado:**

```powershell
# Navegar a la carpeta frontend
cd frontend

# Instalar dependencias de Node.js
npm install

# Compilar el frontend
npm run build

# Volver a la carpeta del demo
cd ..
```

**💡 Tip:** Si copiaste `node_modules/` de todos modos y quieres intentarlo, primero prueba ejecutar el demo. Si da errores, elimina `node_modules/` y reinstala con `npm install`.

## 🎯 Ejecutar el Demo

### Opción 1: Con TensorRT (Más rápido, requiere construcción de engines)

```powershell
python main.py --acceleration tensorrt
```

### Opción 2: Con xformers (Más rápido de configurar)

```powershell
python main.py --acceleration xformers
```

### Opción 3: Sin aceleración (Más lento, pero funciona siempre)

```powershell
python main.py --acceleration none
```

Luego abre en tu navegador:
- `http://localhost:7860` o
- `http://0.0.0.0:7860`

## 📁 Modelos Necesarios

Los modelos se descargarán automáticamente la primera vez que ejecutes el demo. Se guardarán en:
- `C:\Users\<tu_usuario>\.cache\huggingface\`

**Modelos que se descargarán:**
- Modelo base de Stable Diffusion (ej: `runwayml/stable-diffusion-v1-5`)
- LCM-LoRA (si no está incluido en el modelo)
- Tiny VAE (si usas `--taesd`)

**Tamaño aproximado:** 4-8 GB en total

## ⚙️ Configuración Opcional

### Variables de Entorno (opcional)

Puedes crear un archivo `.env` o configurar variables de entorno:

```powershell
$env:ACCELERATION = "tensorrt"
$env:ENGINE_DIR = "engines"
$env:USE_TAESD = "True"
$env:PORT = "7860"
$env:HOST = "0.0.0.0"
```

## 🔧 Solución de Problemas Comunes

### Error: "Python 3.10 required"
- Asegúrate de tener Python 3.10 exactamente
- Verifica: `python --version`

### Error: "CUDA out of memory"
- Reduce el tamaño de las imágenes en el frontend
- Cierra otras aplicaciones que usen GPU
- Usa `--acceleration none` si TensorRT causa problemas

### Error: "Module not found"
- Asegúrate de tener el entorno virtual activado
- Reinstala las dependencias: `pip install -r requirements.txt`

### Error: "npm install failed"
- Verifica que tienes Node.js 18+
- Limpia caché: `npm cache clean --force`
- Elimina `node_modules` y `package-lock.json`, luego vuelve a instalar

### El frontend no se carga
- Verifica que ejecutaste `npm run build` en la carpeta `frontend`
- Asegúrate de que el servidor Python está corriendo
- Prueba `http://localhost:7860` en lugar de `http://0.0.0.0:7860`

## 📝 Resumen Rápido

```powershell
# 1. Crear y activar entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar PyTorch (CUDA 12.1)
pip3 install torch==2.1.0 torchvision==0.16.0 xformers --index-url https://download.pytorch.org/whl/cu121

# 3. Instalar StreamDiffusion
pip install streamdiffusion[tensorrt]
python -m streamdiffusion.tools.install-tensorrt
pip install --force-reinstall pywin32

# 4. Instalar dependencias del demo
cd demo\realtime-img2img
pip install -r requirements.txt

# 5. Compilar frontend
cd frontend
npm install
npm run build
cd ..

# 6. Ejecutar
python main.py --acceleration tensorrt
```

## 📞 Notas Adicionales

- La primera ejecución puede tardar varios minutos mientras descarga modelos y construye engines de TensorRT
- Los engines de TensorRT se guardan en la carpeta `engines/` y pueden ocupar varios GB
- Si cambias de GPU, necesitarás reconstruir los engines de TensorRT
- El demo funciona mejor con GPU NVIDIA moderna (RTX 3060 o superior recomendado)

## 🆚 Comparación: Docker vs Instalación Manual

| Aspecto | Docker 🐳 | Instalación Manual 💻 |
|---------|-----------|----------------------|
| **Facilidad** | ⭐⭐⭐⭐⭐ Muy fácil | ⭐⭐⭐ Requiere más pasos |
| **Tiempo inicial** | 20-30 min (primera vez) | 30-60 min (instalando todo) |
| **Dependencias** | Instaladas automáticamente | Debes instalar manualmente |
| **Conflictos** | Ninguno (aislado) | Posibles con otras instalaciones |
| **Portabilidad** | ✅ Igual en cualquier PC | ⚠️ Depende del sistema |
| **Requisitos** | Docker Desktop + GPU drivers | Python 3.10 + Node.js + GPU drivers |
| **Debugging** | Más difícil (dentro contenedor) | Más fácil (acceso directo) |
| **Recomendado para** | Usuarios que quieren empezar rápido | Desarrolladores que necesitan control |

### ¿Cuál elegir?

- **Elige Docker si:**
  - Quieres empezar rápido sin complicaciones
  - No quieres instalar Python/Node.js en tu sistema
  - Vas a usar el demo tal cual, sin modificar código
  - Tienes Docker Desktop instalado o puedes instalarlo

- **Elige Instalación Manual si:**
  - Quieres modificar el código del demo
  - Ya tienes Python/Node.js instalados
  - Prefieres tener control total sobre el entorno
  - No puedes o no quieres usar Docker

