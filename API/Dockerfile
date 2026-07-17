# =============================================================================
# Dockerfile para API de Mejora de Imágenes con Real-ESRGAN
# =============================================================================

# Usar imagen base CUDA con PyTorch 2.7+ para soporte Blackwell (sm_120)
# RTX 5060 requiere PyTorch 2.7+ que incluye kernels para sm_120
FROM nvidia/cuda:12.8.1-cudnn-runtime-ubuntu22.04

# Metadatos
LABEL maintainer="Image Enhancer API"
LABEL description="API REST para mejora de imágenes usando Real-ESRGAN"
LABEL version="1.0"

# Variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

# Directorio de trabajo
WORKDIR /app

# Instalar Python, dependencias del sistema y ffmpeg
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    wget \
    curl \
    ffmpeg \
    libavcodec-extra \
    && ln -sf /usr/bin/python3 /usr/bin/python \
    && rm -rf /var/lib/apt/lists/*

# Instalar PyTorch 2.7 con soporte CUDA 12.8 (incluye Blackwell sm_120)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
    torch==2.7.0 torchvision==0.22.0 --index-url https://download.pytorch.org/whl/cu128

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Crear directorio para modelos (weights/ es donde el código los busca)
RUN mkdir -p /app/weights

# Descargar todos los modelos de Real-ESRGAN
# Modelos generales para fotos reales
RUN wget -q https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth \
    -O /app/weights/RealESRGAN_x4plus.pth && \
    wget -q https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth \
    -O /app/weights/RealESRGAN_x2plus.pth && \
    # Modelo optimizado para anime/ilustraciones
    wget -q https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth \
    -O /app/weights/RealESRGAN_x4plus_anime_6B.pth && \
    # Modelo para video anime
    wget -q https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth \
    -O /app/weights/realesr-animevideov3.pth && \
    # Modelo general compacto v3
    wget -q https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth \
    -O /app/weights/realesr-general-x4v3.pth

# Descargar modelo GFPGAN para face enhancement (restauración de rostros)
RUN wget -q https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth \
    -O /app/weights/GFPGANv1.4.pth && \
    # Modelo de detección de rostros
    wget -q https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth \
    -O /app/weights/detection_Resnet50_Final.pth && \
    # Modelo de parsing facial
    wget -q https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth \
    -O /app/weights/parsing_parsenet.pth

# Copiar código de la aplicación
COPY app/ /app/app/
COPY main.py /app/

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Puerto de la aplicación
EXPOSE 8888

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8888/api/health || exit 1

# Comando de inicio
CMD ["python", "main.py"]
