#!/bin/bash
# Script para configurar StreamDiffusion en GCP con GPU T4

set -e

echo "=== Configurando StreamDiffusion en GCP (T4 GPU) ==="

# Actualizar sistema
echo "Actualizando sistema..."
sudo apt-get update
sudo apt-get upgrade -y

# Instalar Docker
echo "Instalando Docker..."
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Instalar NVIDIA Container Toolkit
echo "Instalando NVIDIA Container Toolkit..."
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verificar GPU
echo "Verificando GPU..."
nvidia-smi

# Instalar git si no está instalado
sudo apt-get install -y git

# Clonar repositorio
echo "Clonando repositorio StreamDiffusion..."
cd ~
git clone https://github.com/cumulo-autumn/StreamDiffusion.git
cd StreamDiffusion/demo/realtime-img2img

# Construir imagen Docker
echo "Construyendo imagen Docker (esto puede tardar 15-30 minutos)..."
docker build -t streamdiffusion-img2img .

# Crear directorio para engines y cache
mkdir -p ~/engines
mkdir -p ~/.cache/huggingface

# Ejecutar contenedor
echo "Iniciando contenedor StreamDiffusion..."
docker run -d \
  --name streamdiffusion \
  -p 7860:7860 \
  --gpus all \
  --restart unless-stopped \
  -v ~/engines:/data \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -e ENGINE_DIR=/data \
  -e HF_HOME=/root/.cache/huggingface \
  streamdiffusion-img2img

echo ""
echo "=== Configuración completada ==="
echo "El servidor está corriendo en el puerto 7860"
echo ""
echo "Para ver los logs:"
echo "  docker logs -f streamdiffusion"
echo ""
echo "Para detener el servidor:"
echo "  docker stop streamdiffusion"
echo ""
echo "Para iniciar el servidor:"
echo "  docker start streamdiffusion"
echo ""
echo "Obtén tu IP pública con:"
echo "  curl ifconfig.me"
echo ""
echo "Accede desde: http://TU_IP_PUBLICA:7860"

