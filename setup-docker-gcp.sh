#!/bin/bash
# Script para instalar Docker y NVIDIA Container Toolkit en GCP VM

set -e

echo "=== Instalando Docker y NVIDIA Container Toolkit ==="

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

echo ""
echo "=== Instalación completada ==="
echo "Docker y NVIDIA Container Toolkit están instalados"
echo ""
echo "Ahora puedes ejecutar:"
echo "  git clone https://github.com/cumulo-autumn/StreamDiffusion.git"
echo "  cd StreamDiffusion/demo/realtime-img2img"
echo "  docker build -t streamdiffusion-img2img ."
echo "  docker run -d --name streamdiffusion -p 7860:7860 --gpus all --restart unless-stopped streamdiffusion-img2img"

