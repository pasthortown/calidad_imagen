# Manual de Usuario - Image Enhancer API

## Introduccion

Image Enhancer API es un servicio que permite mejorar la calidad y resolucion de imagenes y videos utilizando inteligencia artificial (Real-ESRGAN). Incluye soporte para procesamiento de video con ffmpeg y mejora de rostros con GFPGAN. Este manual describe como instalar, configurar y usar el API.

## Requisitos del Sistema

### Hardware

**Para uso con GPU (recomendado):**
- GPU NVIDIA con CUDA 12.1+ (4GB+ VRAM)
- 16GB RAM
- NVIDIA Driver 525+

**Para uso con CPU:**
- CPU de 4+ núcleos
- 8GB+ RAM
- Procesamiento más lento pero funcional

### Software
- Docker y Docker Compose (versión 2.0+)
- NVIDIA Container Toolkit (si se usa GPU)
- Git (opcional)

## Instalación

### Opción 1: Docker Compose (Recomendado)

Todo el sistema se ejecuta en contenedores Docker.

#### 1. Configurar Variables de Entorno

Editar el archivo `.env` en la raíz del proyecto:

```bash
# Copiar y editar el archivo .env
```

**Variables principales:**

```env
# GPU Configuration - IMPORTANTE
USE_GPU=TRUE          # TRUE para GPU NVIDIA, FALSE para CPU

# JWT - CAMBIAR EN PRODUCCIÓN
JWT_SECRET_KEY=tu-clave-secreta-muy-larga-y-segura

# Network (opcional, usar defaults)
NETWORK_SUBNET=192.168.86.0/24
MONGODB_IP=192.168.86.10
API_IP=192.168.86.20
```

#### 2. Iniciar los Servicios

```bash
# Construir e iniciar todos los servicios
docker-compose up -d --build

# Verificar que están corriendo
docker-compose ps

# Ver logs del API
docker-compose logs -f api

# Ver logs de MongoDB
docker-compose logs -f mongodb
```

#### 3. Verificar Funcionamiento

```bash
# Health check
curl http://localhost:8888/api/health

# Verificar GPU (si USE_GPU=TRUE)
docker exec image_enhancer_api python -c "import torch; print(f'GPU disponible: {torch.cuda.is_available()}')"
```

### Opción 2: Instalación Manual (Desarrollo)

#### 1. Levantar MongoDB con Docker

```bash
docker-compose up -d mongodb
```

#### 2. Instalar Dependencias de Python

```bash
cd API

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

#### 3. Configurar Variables de Entorno

Crear archivo `API/.env`:

```env
MONGO_HOST=192.168.86.10
MONGO_PORT=27017
MONGO_DB=image_enhancer
USE_GPU=TRUE
JWT_SECRET_KEY=tu-clave-secreta
```

#### 4. Iniciar el Servidor

```bash
python main.py
```

El servidor estará disponible en `http://localhost:8888`

---

## Uso del API

### Autenticación

Todos los endpoints de imágenes requieren autenticación JWT.

#### Registrar Usuario

```bash
curl -X POST http://localhost:8888/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "miusuario",
    "email": "usuario@ejemplo.com",
    "password": "mipassword123"
  }'
```

**Respuesta exitosa (201):**
```json
{
  "message": "Usuario registrado exitosamente",
  "user": {
    "id": "6752a1b2c3d4e5f6a7b8c9d0",
    "username": "miusuario",
    "email": "usuario@ejemplo.com",
    "is_active": true,
    "created_at": "2024-12-03T10:30:00"
  }
}
```

#### Iniciar Sesión

```bash
curl -X POST http://localhost:8888/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "usuario@ejemplo.com",
    "password": "mipassword123"
  }'
```

**Respuesta exitosa (200):**
```json
{
  "message": "Login exitoso",
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "a1b2c3d4e5f6g7h8i9j0...",
    "token_type": "bearer"
  }
}
```

#### Refrescar Tokens

Cuando el access_token expire (30 min por defecto):

```bash
curl -X POST http://localhost:8888/api/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "tu_refresh_token_aqui"
  }'
```

#### Cerrar Sesión

```bash
curl -X POST http://localhost:8888/api/auth/logout \
  -H "Authorization: Bearer tu_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "tu_refresh_token_aqui"
  }'
```

#### Ver Mi Perfil

```bash
curl -X GET http://localhost:8888/api/auth/me \
  -H "Authorization: Bearer tu_access_token"
```

---

### Procesamiento de Imágenes

#### Modelos Disponibles

El API soporta múltiples modelos de Real-ESRGAN, cada uno optimizado para diferentes casos de uso:

| model_type | Nombre | Uso recomendado | Escala default |
|------------|--------|-----------------|----------------|
| `general_x4` | RealESRGAN_x4plus | Fotos reales, retratos, paisajes (default) | 4x |
| `general_x2` | RealESRGAN_x2plus | Fotos reales, escala 2x | 2x |
| `anime` | RealESRGAN_x4plus_anime_6B | Anime, manga, ilustraciones | 4x |
| `anime_video` | realesr-animevideov3 | Frames de video anime | 4x |
| `general_v3` | realesr-general-x4v3 | Uso general, más rápido | 4x |

#### Listar Modelos Disponibles

```bash
curl http://localhost:8888/api/models
```

**Respuesta:**
```json
{
  "total": 5,
  "models": [
    {
      "id": "general_x4",
      "name": "RealESRGAN_x4plus",
      "description": "Modelo general para fotos reales - Alta calidad, escala 4x",
      "default_scale": 4,
      "supported_scales": [4],
      "use_case": "Fotos reales, retratos, paisajes - Alta calidad",
      "recommended_for": ["fotografías", "retratos", "paisajes", "arquitectura"]
    },
    {
      "id": "anime",
      "name": "RealESRGAN_x4plus_anime_6B",
      "description": "Optimizado para anime e ilustraciones - Más rápido",
      "default_scale": 4,
      "supported_scales": [4],
      "use_case": "Anime, manga, ilustraciones, arte digital",
      "recommended_for": ["anime", "manga", "ilustraciones", "arte digital", "comics"]
    }
  ]
}
```

#### Mejorar una Imagen

Este es el endpoint principal. Recibe una imagen en base64 y devuelve la imagen mejorada.

```bash
curl -X POST http://localhost:8888/api/images/enhance \
  -H "Authorization: Bearer tu_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "image_base64": "contenido_base64_aqui",
    "filename": "mi_imagen.jpg",
    "model_type": "general_x4",
    "scale": 4,
    "output_width": 1920,
    "output_height": 1080,
    "face_enhance": false
  }'
```

**Parámetros:**

| Parámetro | Tipo | Requerido | Descripción |
|-----------|------|-----------|-------------|
| image_base64 | string | Sí | Imagen codificada en base64 |
| filename | string | No | Nombre original del archivo |
| **model_type** | string | No | **Tipo de modelo: general_x4, general_x2, anime, anime_video, general_v3. Default: general_x4** |
| scale | integer | No | Factor de escala (1-4). Si no se especifica, usa el default del modelo |
| output_width | integer | No | Ancho de salida deseado (redimensiona después de mejorar) |
| output_height | integer | No | Alto de salida deseado (redimensiona después de mejorar) |
| face_enhance | boolean | No | Mejorar rostros con GFPGAN. Default: false |

**Ejemplos de uso según tipo de contenido:**

```bash
# Para fotos reales (retratos, paisajes)
curl -X POST http://localhost:8888/api/images/enhance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "...", "model_type": "general_x4"}'

# Para anime o ilustraciones
curl -X POST http://localhost:8888/api/images/enhance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "...", "model_type": "anime"}'

# Para procesamiento rápido
curl -X POST http://localhost:8888/api/images/enhance \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "...", "model_type": "general_v3"}'
```

**Respuesta exitosa (201):**
```json
{
  "message": "Imagen procesada exitosamente",
  "image": {
    "id": "6752a1b2c3d4e5f6a7b8c9d1",
    "original_filename": "mi_imagen.jpg",
    "original_width": 256,
    "original_height": 256,
    "enhanced_width": 1920,
    "enhanced_height": 1080,
    "model_type": "general_x4",
    "scale": 4,
    "output_width": 1920,
    "output_height": 1080,
    "face_enhance": false,
    "status": "completed",
    "processing_time_ms": 5432,
    "gpu_used": true,
    "created_at": "2024-12-03T10:35:00",
    "completed_at": "2024-12-03T10:35:05",
    "original_base64": "...",
    "enhanced_base64": "...",
    "error_message": null
  }
}
```

**Notas sobre `model_type`:**
- `general_x4`: Mejor calidad para fotos reales, más lento
- `general_x2`: Para cuando solo necesitas escala 2x
- `anime`: Optimizado para anime/manga, modelo más pequeño y rápido
- `anime_video`: Para frames de video anime
- `general_v3`: Balance entre velocidad y calidad

**Notas sobre `output_width` y `output_height`:**
- Si se especifican ambos, la imagen se redimensiona exactamente a ese tamaño
- Si se especifica solo uno, el otro se calcula manteniendo el aspect ratio
- Si no se especifican, se devuelve el tamaño completo del procesamiento (original × scale)

#### Listar Mis Imágenes

```bash
curl -X GET "http://localhost:8888/api/images?page=1&per_page=10" \
  -H "Authorization: Bearer tu_access_token"
```

**Parámetros de query:**

| Parámetro | Tipo | Descripción |
|-----------|------|-------------|
| page | integer | Página (default: 1) |
| per_page | integer | Imágenes por página (default: 10, max: 100) |
| status | string | Filtrar por estado: pending, processing, completed, failed |

**Respuesta:**
```json
{
  "total": 25,
  "page": 1,
  "per_page": 10,
  "images": [
    {
      "id": "6752a1b2c3d4e5f6a7b8c9d1",
      "original_filename": "mi_imagen.jpg",
      "original_width": 256,
      "original_height": 256,
      "enhanced_width": 1024,
      "enhanced_height": 1024,
      "scale": 4,
      "output_width": null,
      "output_height": null,
      "face_enhance": false,
      "status": "completed",
      "processing_time_ms": 5432,
      "gpu_used": true,
      "created_at": "2024-12-03T10:35:00",
      "completed_at": "2024-12-03T10:35:05"
    }
  ]
}
```

#### Obtener una Imagen

```bash
curl -X GET http://localhost:8888/api/images/6752a1b2c3d4e5f6a7b8c9d1 \
  -H "Authorization: Bearer tu_access_token"
```

#### Eliminar una Imagen

```bash
curl -X DELETE http://localhost:8888/api/images/6752a1b2c3d4e5f6a7b8c9d1 \
  -H "Authorization: Bearer tu_access_token"
```

---

### Procesamiento de Videos

El procesamiento de videos es **asincrono**. Al enviar un video, el API responde inmediatamente con un ID y status `pending`. El procesamiento ocurre en background.

**Importante sobre formatos:**
- El video **original** se guarda conservando su extension original (.mp4, .avi, etc.)
- El video **mejorado** siempre se genera en formato **MKV** con codec H.264

#### Mejorar un Video

```bash
curl -X POST http://localhost:8888/api/videos/enhance \
  -H "Authorization: Bearer tu_access_token" \
  -H "Content-Type: application/json" \
  -d '{
    "video_base64": "contenido_base64_aqui",
    "filename": "mi_video.mp4",
    "model_type": "general_x4",
    "scale": 2,
    "face_enhance": false
  }'
```

**Parametros:**

| Parametro | Tipo | Requerido | Descripcion |
|-----------|------|-----------|-------------|
| video_base64 | string | Si | Video codificado en base64 |
| filename | string | Si | Nombre original del archivo con extension |
| model_type | string | No | Tipo de modelo (default: general_x4) |
| scale | integer | No | Factor de escala (1-4). Default: segun modelo |
| face_enhance | boolean | No | Mejorar rostros con GFPGAN. Default: false |

**Respuesta exitosa (202 Accepted):**
```json
{
  "message": "Video recibido, procesamiento iniciado. Consulte el estado con GET /api/videos/{id}",
  "video": {
    "id": "6752a1b2c3d4e5f6a7b8c9d1",
    "original_filename": "mi_video.mp4",
    "status": "pending",
    "duration_seconds": 30.5,
    "fps": 29.97,
    "frame_count": 914,
    "original_width": 1920,
    "original_height": 1080,
    "frames_processed": 0
  }
}
```

#### Consultar Estado del Video

```bash
curl -X GET http://localhost:8888/api/videos/6752a1b2c3d4e5f6a7b8c9d1 \
  -H "Authorization: Bearer tu_access_token"
```

**Respuesta (en progreso):**
```json
{
  "video": {
    "id": "6752a1b2c3d4e5f6a7b8c9d1",
    "status": "in_progress",
    "frame_count": 914,
    "frames_processed": 450,
    "original_base64": null,
    "enhanced_base64": null
  }
}
```

**Respuesta (completado):**
```json
{
  "video": {
    "id": "6752a1b2c3d4e5f6a7b8c9d1",
    "status": "completed",
    "frame_count": 914,
    "frames_processed": 914,
    "enhanced_width": 3840,
    "enhanced_height": 2160,
    "processing_time_ms": 125000,
    "gpu_used": true,
    "original_base64": "...",
    "enhanced_base64": "..."
  }
}
```

#### Listar Mis Videos

```bash
curl -X GET "http://localhost:8888/api/videos?page=1&per_page=10&status=completed" \
  -H "Authorization: Bearer tu_access_token"
```

**Parametros de query:**

| Parametro | Tipo | Descripcion |
|-----------|------|-------------|
| page | integer | Pagina (default: 1) |
| per_page | integer | Videos por pagina (default: 10, max: 100) |
| status | string | Filtrar: pending, in_progress, completed, error |

#### Eliminar un Video

```bash
curl -X DELETE http://localhost:8888/api/videos/6752a1b2c3d4e5f6a7b8c9d1 \
  -H "Authorization: Bearer tu_access_token"
```

---

### Endpoints del Sistema

#### Verificar Estado del Servicio

```bash
curl http://localhost:8888/api/health
```

**Respuesta:**
```json
{
  "status": "healthy",
  "services": {
    "api": "ok",
    "mongodb": "ok",
    "gpu": "ok (NVIDIA GeForce RTX 3080)"
  }
}
```

#### Información del API

```bash
curl http://localhost:8888/api/info
```

---

## Ejemplos de Código

### Python

```python
import requests
import base64

API_URL = "http://localhost:8888"

# 1. Login
response = requests.post(f"{API_URL}/api/auth/login", json={
    "email": "usuario@ejemplo.com",
    "password": "mipassword123"
})
tokens = response.json()["tokens"]
access_token = tokens["access_token"]

# 2. Headers de autenticación
headers = {"Authorization": f"Bearer {access_token}"}

# 3. Leer y codificar imagen
with open("mi_imagen.jpg", "rb") as f:
    image_base64 = base64.b64encode(f.read()).decode("utf-8")

# 4. Mejorar imagen con modelo específico
response = requests.post(
    f"{API_URL}/api/images/enhance",
    headers=headers,
    json={
        "image_base64": image_base64,
        "filename": "mi_imagen.jpg",
        "model_type": "anime",     # Usar modelo para anime
        "scale": 4,
        "output_width": 1920,      # Especificar tamaño de salida
        "output_height": 1080
    }
)
result = response.json()

# 5. Verificar modelo usado y si se uso GPU
print(f"Modelo: {result['image']['model_type']}")
print(f"GPU usada: {result['image']['gpu_used']}")
print(f"Tamano final: {result['image']['enhanced_width']}x{result['image']['enhanced_height']}")

# 6. Guardar imagen mejorada
if result["image"]["status"] == "completed":
    enhanced_base64 = result["image"]["enhanced_base64"]
    enhanced_bytes = base64.b64decode(enhanced_base64)
    with open("imagen_mejorada.png", "wb") as f:
        f.write(enhanced_bytes)
    print("Imagen guardada!")
```

### Python - Video

```python
import requests
import base64
import time

API_URL = "http://localhost:8888"

# 1. Login
response = requests.post(f"{API_URL}/api/auth/login", json={
    "email": "usuario@ejemplo.com",
    "password": "mipassword123"
})
tokens = response.json()["tokens"]
access_token = tokens["access_token"]
headers = {"Authorization": f"Bearer {access_token}"}

# 2. Leer y codificar video
with open("mi_video.mp4", "rb") as f:
    video_base64 = base64.b64encode(f.read()).decode("utf-8")

# 3. Enviar video para procesamiento
response = requests.post(
    f"{API_URL}/api/videos/enhance",
    headers=headers,
    json={
        "video_base64": video_base64,
        "filename": "mi_video.mp4",
        "model_type": "general_x4",
        "scale": 2,
        "face_enhance": True  # Mejorar rostros
    }
)
result = response.json()
video_id = result["video"]["id"]
print(f"Video ID: {video_id}")
print(f"Frames totales: {result['video']['frame_count']}")

# 4. Esperar a que termine (polling)
while True:
    response = requests.get(f"{API_URL}/api/videos/{video_id}", headers=headers)
    video = response.json()["video"]
    status = video["status"]
    frames = video.get("frames_processed", 0)
    total = video.get("frame_count", 0)

    print(f"Status: {status} - Frames: {frames}/{total}")

    if status == "completed":
        print(f"Procesamiento completado en {video['processing_time_ms']}ms")
        break
    elif status == "error":
        print(f"Error: {video.get('error_message')}")
        break

    time.sleep(10)  # Esperar 10 segundos

# 5. Descargar video mejorado (siempre en formato MKV)
if video.get("enhanced_base64"):
    enhanced_bytes = base64.b64decode(video["enhanced_base64"])
    with open("video_mejorado.mkv", "wb") as f:
        f.write(enhanced_bytes)
    print("Video mejorado guardado como MKV!")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');
const fs = require('fs');

const API_URL = 'http://localhost:8888';

async function main() {
    // 1. Login
    const loginResponse = await axios.post(`${API_URL}/api/auth/login`, {
        email: 'usuario@ejemplo.com',
        password: 'mipassword123'
    });
    const accessToken = loginResponse.data.tokens.access_token;

    // 2. Headers
    const headers = { Authorization: `Bearer ${accessToken}` };

    // 3. Leer y codificar imagen
    const imageBuffer = fs.readFileSync('mi_imagen.jpg');
    const imageBase64 = imageBuffer.toString('base64');

    // 4. Mejorar imagen con output_width/height
    const enhanceResponse = await axios.post(
        `${API_URL}/api/images/enhance`,
        {
            image_base64: imageBase64,
            filename: 'mi_imagen.jpg',
            scale: 4,
            output_width: 1920,
            output_height: 1080
        },
        { headers }
    );

    console.log(`GPU usada: ${enhanceResponse.data.image.gpu_used}`);

    // 5. Guardar resultado
    const enhancedBase64 = enhanceResponse.data.image.enhanced_base64;
    const enhancedBuffer = Buffer.from(enhancedBase64, 'base64');
    fs.writeFileSync('imagen_mejorada.png', enhancedBuffer);
    console.log('Imagen guardada!');
}

main().catch(console.error);
```

### cURL Script (Bash)

```bash
#!/bin/bash

API_URL="http://localhost:8888"
EMAIL="usuario@ejemplo.com"
PASSWORD="mipassword123"

# Login y obtener token
TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
    | jq -r '.tokens.access_token')

echo "Token obtenido: ${TOKEN:0:20}..."

# Codificar imagen
IMAGE_BASE64=$(base64 -w 0 mi_imagen.jpg)

# Mejorar imagen con tamaño específico
RESULT=$(curl -s -X POST "$API_URL/api/images/enhance" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"image_base64\":\"$IMAGE_BASE64\",
        \"scale\":4,
        \"output_width\":1920,
        \"output_height\":1080
    }")

# Mostrar info
echo "GPU usada: $(echo $RESULT | jq -r '.image.gpu_used')"
echo "Tamaño: $(echo $RESULT | jq -r '.image.enhanced_width')x$(echo $RESULT | jq -r '.image.enhanced_height')"

# Extraer y guardar imagen mejorada
echo $RESULT | jq -r '.image.enhanced_base64' | base64 -d > imagen_mejorada.png

echo "Imagen mejorada guardada!"
```

---

## Configuración

### Archivo .env

Todas las configuraciones se manejan desde el archivo `.env` en la raíz del proyecto:

```env
# =============================================================================
# Configuración del Sistema de Mejora de Imágenes
# =============================================================================

# MongoDB Configuration
MONGO_HOST=192.168.86.10
MONGO_PORT=27017
MONGO_DB=image_enhancer
MONGO_USER=
MONGO_PASSWORD=

# API Configuration
API_HOST=0.0.0.0
API_PORT=8888
API_DEBUG=false

# JWT Configuration - CAMBIAR EN PRODUCCIÓN
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# GPU Configuration
USE_GPU=TRUE          # TRUE para GPU NVIDIA, FALSE para CPU

# Real-ESRGAN Configuration
DEFAULT_SCALE=4
TILE_SIZE=512         # Reducir si hay problemas de memoria GPU
TILE_PAD=10

# Network Configuration
NETWORK_NAME=ImagesNet
NETWORK_SUBNET=192.168.86.0/24
NETWORK_GATEWAY=192.168.86.1
MONGODB_IP=192.168.86.10
API_IP=192.168.86.20
```

### Tabla de Variables

| Variable | Descripción | Default |
|----------|-------------|---------|
| MONGO_HOST | IP/host de MongoDB | 192.168.86.10 |
| MONGO_PORT | Puerto de MongoDB | 27017 |
| MONGO_DB | Nombre de la base de datos | image_enhancer |
| API_PORT | Puerto del API | 8888 |
| JWT_SECRET_KEY | Clave secreta para JWT | - |
| **USE_GPU** | **Usar GPU NVIDIA (TRUE/FALSE)** | **TRUE** |
| DEFAULT_SCALE | Escala por defecto | 4 |
| TILE_SIZE | Tamaño de tile para procesamiento | 512 |

### Modelos Disponibles

| Modelo | Escala | Uso recomendado |
|--------|--------|-----------------|
| RealESRGAN_x2plus | 2x | Imágenes grandes, menos procesamiento |
| RealESRGAN_x4plus | 4x | Uso general (default) |

---

## Comandos Docker

```bash
# Iniciar todos los servicios
docker-compose up -d

# Reconstruir e iniciar
docker-compose up -d --build

# Ver logs del API
docker-compose logs -f api

# Ver logs de MongoDB
docker-compose logs -f mongodb

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (CUIDADO: borra datos)
docker-compose down -v

# Reiniciar solo el API
docker-compose restart api

# Verificar estado de GPU en contenedor
docker exec image_enhancer_api python -c "import torch; print(torch.cuda.is_available())"

# Ver uso de memoria GPU
docker exec image_enhancer_api nvidia-smi
```

---

## Errores Comunes

### 401 Unauthorized

```json
{"error": "Token de autenticación requerido"}
```
**Solución**: Incluir el header `Authorization: Bearer <token>`

```json
{"error": "Token inválido o expirado"}
```
**Solución**: Usar el refresh_token para obtener un nuevo access_token

### 400 Bad Request

```json
{"error": "Datos de imagen inválidos"}
```
**Solución**: Verificar que el campo `image_base64` contiene una imagen válida

```json
{"error": "Formato no soportado: gif"}
```
**Solución**: Usar formatos soportados: PNG, JPG, JPEG, WEBP

### 500 Internal Server Error

```json
{"error": "Error procesando imagen: CUDA out of memory"}
```
**Solución**:
1. Reducir `TILE_SIZE` en el .env
2. Usar `scale` menor (2 en lugar de 4)
3. Reducir tamaño de imagen de entrada
4. Usar `USE_GPU=FALSE` para procesar con CPU

---

## Solución de Problemas

### MongoDB no conecta

```bash
# Verificar que Docker está corriendo
docker ps

# Ver logs de MongoDB
docker-compose logs mongodb

# Reiniciar MongoDB
docker-compose restart mongodb
```

### Error de GPU/CUDA

```bash
# Verificar driver NVIDIA
nvidia-smi

# Verificar NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.1-base nvidia-smi

# Usar CPU como alternativa
# En .env: USE_GPU=FALSE
```

### Procesamiento lento

1. Verificar que GPU está habilitada: `USE_GPU=TRUE`
2. Reducir `scale` (2 en lugar de 4)
3. Reducir tamaño de imagen de entrada
4. Ajustar `TILE_SIZE` según memoria disponible

### API no responde

```bash
# Ver logs del API
docker-compose logs -f api

# Reiniciar API
docker-compose restart api

# Health check
curl http://localhost:8888/api/health
```

---

## Contacto y Soporte

Para reportar problemas o solicitar ayuda:
- Revisar la documentación de arquitectura en `docs/ARQUITECTURA.md`
- Verificar los logs del servidor: `docker-compose logs -f api`
- Verificar el health check: `curl http://localhost:8888/api/health`
