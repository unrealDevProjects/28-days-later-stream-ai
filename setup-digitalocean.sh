#!/bin/bash
# =============================================================================
# StreamDiffusion - Script de Instalación para DigitalOcean GPU Droplet
# =============================================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     🚀 StreamDiffusion - Instalación DigitalOcean GPU        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar que estamos en un sistema con GPU NVIDIA
echo -e "${YELLOW}[1/8] Verificando GPU NVIDIA...${NC}"
if ! command -v nvidia-smi &> /dev/null; then
    echo -e "${RED}❌ No se detectó GPU NVIDIA. Este script es para GPU Droplets.${NC}"
    exit 1
fi
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo -e "${GREEN}✓ GPU detectada${NC}"

# Actualizar sistema
echo -e "${YELLOW}[2/8] Actualizando sistema...${NC}"
sudo apt update && sudo apt upgrade -y
echo -e "${GREEN}✓ Sistema actualizado${NC}"

# Instalar dependencias
echo -e "${YELLOW}[3/8] Instalando dependencias del sistema...${NC}"
sudo apt install -y \
    wget \
    git \
    python3 \
    python3-pip \
    python3-venv \
    ffmpeg \
    libsm6 \
    libxext6 \
    curl

# Instalar Node.js 18+ para el frontend
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
echo -e "${GREEN}✓ Dependencias instaladas${NC}"

# Crear directorio de trabajo
echo -e "${YELLOW}[4/8] Configurando directorio de trabajo...${NC}"
INSTALL_DIR="$HOME/StreamDiffusion"

if [ -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}⚠ El directorio $INSTALL_DIR ya existe.${NC}"
    read -p "¿Deseas eliminarlo y reinstalar? (s/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Ss]$ ]]; then
        rm -rf "$INSTALL_DIR"
    else
        echo "Usando directorio existente..."
    fi
fi

if [ ! -d "$INSTALL_DIR" ]; then
    echo "Clonando repositorio..."
    # Cambiar esta URL a tu repositorio
    git clone https://github.com/cumulo-autumn/StreamDiffusion.git "$INSTALL_DIR"
fi
cd "$INSTALL_DIR"
echo -e "${GREEN}✓ Repositorio listo${NC}"

# Crear entorno virtual
echo -e "${YELLOW}[5/8] Creando entorno virtual Python...${NC}"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
echo -e "${GREEN}✓ Entorno virtual creado${NC}"

# Instalar PyTorch con CUDA
echo -e "${YELLOW}[6/8] Instalando PyTorch con CUDA...${NC}"
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
echo -e "${GREEN}✓ PyTorch instalado${NC}"

# Instalar StreamDiffusion
echo -e "${YELLOW}[7/8] Instalando StreamDiffusion...${NC}"
pip install -e .

# Instalar dependencias de la demo
cd demo/realtime-img2img
pip install -r requirements.txt

# Build del frontend
echo "Compilando frontend..."
cd frontend
npm install
npm run build
cd ..
echo -e "${GREEN}✓ StreamDiffusion instalado${NC}"

# Instalar herramientas adicionales
echo -e "${YELLOW}[8/8] Instalando herramientas adicionales...${NC}"
pip install gpustat
echo -e "${GREEN}✓ Herramientas instaladas${NC}"

# Crear script de inicio rápido
cat > "$INSTALL_DIR/start.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/demo/realtime-img2img"
source ../../.venv/bin/activate
echo "🚀 Iniciando StreamDiffusion..."
echo "📍 Accede en: http://$(hostname -I | awk '{print $1}'):7860"
python main.py --host 0.0.0.0 --port 7860 "$@"
EOF
chmod +x "$INSTALL_DIR/start.sh"

# Crear script de inicio con TensorRT
cat > "$INSTALL_DIR/start-tensorrt.sh" << 'EOF'
#!/bin/bash
cd "$(dirname "$0")/demo/realtime-img2img"
source ../../.venv/bin/activate
echo "🚀 Iniciando StreamDiffusion con TensorRT..."
echo "📍 Accede en: http://$(hostname -I | awk '{print $1}'):7860"
echo "⏳ La primera ejecución compilará los engines (puede tardar 5-10 min)..."
python main.py --host 0.0.0.0 --port 7860 --acceleration tensorrt "$@"
EOF
chmod +x "$INSTALL_DIR/start-tensorrt.sh"

# Resumen final
echo ""
echo -e "${GREEN}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           ✅ INSTALACIÓN COMPLETADA CON ÉXITO                ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "${BLUE}Para iniciar StreamDiffusion:${NC}"
echo ""
echo "  Sin TensorRT (más simple):"
echo -e "    ${YELLOW}cd $INSTALL_DIR && ./start.sh${NC}"
echo ""
echo "  Con TensorRT (más rápido):"
echo -e "    ${YELLOW}cd $INSTALL_DIR && ./start-tensorrt.sh${NC}"
echo ""
echo -e "${BLUE}Accede desde tu navegador:${NC}"
IP_ADDRESS=$(hostname -I | awk '{print $1}')
echo -e "    ${GREEN}http://$IP_ADDRESS:7860${NC}"
echo ""
echo -e "${YELLOW}💡 Tip: Usa 'gpustat -i 1' en otra terminal para monitorear la GPU${NC}"
echo ""
