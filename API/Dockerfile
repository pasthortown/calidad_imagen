# =============================================================================
# Dockerfile para API de Mejora de Imágenes con Real-ESRGAN
# =============================================================================

# Usar imagen base de PyTorch con soporte CUDA
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

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

# Instalar dependencias del sistema incluyendo ffmpeg para procesamiento de video
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    wget \
    curl \
    ffmpeg \
    libavcodec-extra \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements primero para aprovechar cache de Docker
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

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
