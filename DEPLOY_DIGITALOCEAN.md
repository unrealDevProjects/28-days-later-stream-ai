# 🚀 Desplegar StreamDiffusion en DigitalOcean GPU Droplet

Esta guía te permite ejecutar tu experiencia StreamDiffusion real-time img2img en un GPU Droplet de DigitalOcean.

## Requisitos Previos

- Cuenta de DigitalOcean con acceso a GPU Droplets
- Tu repositorio subido a GitHub (o usaremos git clone directo)

---

## Paso 1: Crear el GPU Droplet

1. Inicia sesión en [DigitalOcean](https://cloud.digitalocean.com/)
2. Click en **Create** → **Droplets**
3. Selecciona **GPU Droplets**
4. Elige el plan:
   - **gpu-h100x1-80gb** (~$2.50/hora) - Recomendado
5. Selecciona la región más cercana a ti
6. Imagen: **Ubuntu 22.04 LTS**
7. Autenticación: SSH Key (recomendado) o Password
8. Click en **Create Droplet**

---

## Paso 2: Conectarse al Droplet

```bash
ssh root@TU_IP_DEL_DROPLET
```

---

## Paso 3: Crear Usuario (Recomendado)

```bash
# Crear usuario
adduser streamdiff
usermod -aG sudo streamdiff

# Cambiar a ese usuario
su - streamdiff
cd ~
```

---

## Paso 4: Instalar Dependencias del Sistema

```bash
# Actualizar sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias
sudo apt install -y wget git python3 python3-pip python3-venv ffmpeg libsm6 libxext6

# Verificar CUDA (ya viene instalado en GPU Droplets)
nvidia-smi
```

Deberías ver tu GPU H100 listada.

---

## Paso 5: Clonar el Repositorio

```bash
# Clonar tu repositorio
git clone https://github.com/TU_USUARIO/StreamDiffusion.git
cd StreamDiffusion
```

> **Nota:** Si tu repo es privado, usa un token de acceso personal:
> ```bash
> git clone https://TU_TOKEN@github.com/TU_USUARIO/StreamDiffusion.git
> ```

---

## Paso 6: Crear Entorno Virtual e Instalar

```bash
# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar PyTorch con CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Instalar StreamDiffusion
pip install -e .

# Instalar dependencias de la demo
cd demo/realtime-img2img
pip install -r requirements.txt

# Instalar dependencias del frontend
cd frontend
npm install
npm run build
cd ..
```

---

## Paso 7: Instalar TensorRT (Opcional pero Recomendado)

```bash
# Activar entorno si no está activo
source ~/.venv/bin/activate

# Instalar TensorRT
pip install tensorrt

# Instalar cuda-python compatible
pip install cuda-python==12.3.0

# Instalar streamdiffusion con TensorRT
cd ~/StreamDiffusion
python -m streamdiffusion.tools.install-tensorrt
```

---

## Paso 8: Ejecutar el Servidor

### Sin TensorRT (más simple):
```bash
cd ~/StreamDiffusion/demo/realtime-img2img
source ~/.venv/bin/activate
python main.py --host 0.0.0.0 --port 7860
```

### Con TensorRT (más rápido):
```bash
cd ~/StreamDiffusion/demo/realtime-img2img
source ~/.venv/bin/activate
python main.py --host 0.0.0.0 --port 7860 --acceleration tensorrt
```

---

## Paso 9: Acceder desde tu Navegador

### Opción A: Acceso Directo (Si el firewall lo permite)

1. En DigitalOcean, ve a **Networking** → **Firewalls**
2. Crea una regla para permitir el puerto **7860** (TCP)
3. Accede desde tu navegador: `http://TU_IP_DROPLET:7860`

### Opción B: Túnel SSH (Más seguro)

Desde tu ordenador local:
```bash
ssh -L 7860:localhost:7860 streamdiff@TU_IP_DROPLET
```

Luego abre en tu navegador: `http://localhost:7860`

### Opción C: Usar ngrok (Acceso público temporal)

En el droplet:
```bash
# Instalar ngrok
curl -s https://ngrok-agent.s3.amazonaws.com/ngrok.asc | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | sudo tee /etc/apt/sources.list.d/ngrok.list
sudo apt update && sudo apt install ngrok

# Configurar (necesitas cuenta gratuita en ngrok.com)
ngrok config add-authtoken TU_TOKEN_NGROK

# Crear túnel
ngrok http 7860
```

---

## Paso 10: Ejecutar como Servicio (Opcional)

Para que el servidor se ejecute automáticamente:

```bash
sudo nano /etc/systemd/system/streamdiffusion.service
```

Contenido:
```ini
[Unit]
Description=StreamDiffusion Real-time Service
After=network.target

[Service]
Type=simple
User=streamdiff
WorkingDirectory=/home/streamdiff/StreamDiffusion/demo/realtime-img2img
Environment="PATH=/home/streamdiff/StreamDiffusion/.venv/bin"
ExecStart=/home/streamdiff/StreamDiffusion/.venv/bin/python main.py --host 0.0.0.0 --port 7860 --acceleration tensorrt
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Activar el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable streamdiffusion
sudo systemctl start streamdiffusion

# Ver logs
sudo journalctl -u streamdiffusion -f
```

---

## 💡 Tips

### Monitorear GPU
```bash
# Instalar gpustat
pip install gpustat

# Monitorear en tiempo real
gpustat --color -i 1
```

### Apagar el Droplet cuando no lo uses
Los GPU Droplets cobran por hora. **Apágalo** cuando no lo uses para ahorrar dinero.

### Snapshot para restaurar rápido
Una vez configurado todo, crea un **Snapshot** del droplet para poder restaurarlo rápidamente sin reinstalar todo.

---

## 🔧 Solución de Problemas

### Error: Puerto ya en uso
```bash
sudo lsof -i :7860
sudo kill -9 PID_DEL_PROCESO
```

### Error: CUDA out of memory
Reduce la resolución en `img2img.py`:
```python
width: int = Field(512, ...)
height: int = Field(512, ...)
```

### Error: TensorRT engines incompatibles
Elimina los engines y regenera:
```bash
rm -rf engines/
python main.py --acceleration tensorrt  # Se regenerarán automáticamente
```

---

## 📊 Costos Estimados

| Uso | Costo Aproximado |
|-----|------------------|
| 1 hora de pruebas | ~$2.50 |
| 8 horas (día de trabajo) | ~$20 |
| 24 horas | ~$60 |
| 1 mes 24/7 | ~$1,800 |

**Recomendación:** Usa el droplet solo cuando lo necesites y apágalo después.

---

## 🚀 Script de Instalación Automática

Guarda este script como `install.sh` y ejecútalo en el droplet:

```bash
#!/bin/bash
set -e

echo "🚀 Instalando StreamDiffusion..."

# Actualizar sistema
sudo apt update && sudo apt upgrade -y
sudo apt install -y wget git python3 python3-pip python3-venv ffmpeg libsm6 libxext6 nodejs npm

# Clonar repositorio
cd ~
git clone https://github.com/TU_USUARIO/StreamDiffusion.git
cd StreamDiffusion

# Crear entorno virtual
python3 -m venv .venv
source .venv/bin/activate

# Instalar PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Instalar StreamDiffusion
pip install -e .

# Instalar demo
cd demo/realtime-img2img
pip install -r requirements.txt

# Build frontend
cd frontend
npm install
npm run build
cd ..

echo "✅ Instalación completa!"
echo "Ejecuta: source ~/.venv/bin/activate && python main.py --host 0.0.0.0 --port 7860"
```

Ejecución:
```bash
chmod +x install.sh
./install.sh
```
