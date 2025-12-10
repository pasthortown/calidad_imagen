# Arquitectura del Sistema - Image Enhancer API

## Vision General

Image Enhancer API es un servicio REST que permite mejorar la calidad de imagenes y videos utilizando Real-ESRGAN, una red neuronal de ultima generacion para super-resolucion. El sistema esta construido con Python usando Tornado como framework web asincrono y MongoDB como base de datos. Incluye soporte para procesamiento de video con ffmpeg.

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENTES                                    │
│                    (Web App, Mobile App, Scripts)                        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         DOCKER COMPOSE                                   │
│                        (Red: ImagesNet)                                  │
│                    Subnet: 192.168.86.0/24                               │
│                                                                          │
│  ┌─────────────────────────────────┐  ┌─────────────────────────────┐  │
│  │     API Container               │  │    MongoDB Container        │  │
│  │     192.168.86.20:8888          │  │    192.168.86.10:27017      │  │
│  │                                 │  │                             │  │
│  │  ┌───────────┐ ┌───────────┐   │  │  ┌─────────┐ ┌─────────┐   │  │
│  │  │  Tornado  │ │Real-ESRGAN│   │  │  │ users   │ │ images  │   │  │
│  │  │  Server   │ │  + GPU    │   │  │  └─────────┘ └─────────┘   │  │
│  │  └───────────┘ ├───────────┤   │  │  ┌─────────┐ ┌─────────┐   │  │
│  │                │  ffmpeg   │   │  │  │ videos  │ │ refresh │   │  │
│  │                │ (video)   │   │  │  │         │ │ _tokens │   │  │
│  │                └───────────┘   │  │  └─────────┘ └─────────┘   │  │
│  └─────────────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Arquitectura de Contenedores

### Docker Compose Services

| Servicio | Container Name | IP | Puerto | Descripción |
|----------|---------------|-----|--------|-------------|
| mongodb | image_enhancer_mongodb | 192.168.86.10 | 27017 | Base de datos MongoDB 7.0 |
| api | image_enhancer_api | 192.168.86.20 | 8888 | API REST con Real-ESRGAN |

### Soporte GPU NVIDIA

El sistema está configurado para usar GPU NVIDIA cuando está disponible:

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

**Requisitos para GPU:**
- NVIDIA Driver instalado en el host
- NVIDIA Container Toolkit (nvidia-docker2)
- Variable de entorno `USE_GPU=TRUE`

## Diagrama de Componentes Internos

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY                                    │
│                         (Tornado Server)                                 │
│                                                                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │    Auth     │  │   Images    │  │   Videos    │  │   System    │    │
│  │  Handlers   │  │  Handlers   │  │  Handlers   │  │  Handlers   │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
        ┌───────────────┐  ┌───────────────┐  ┌───────────────┐
        │  Auth Service │  │ Image Service │  │ Video Service │
        │               │  │               │  │               │
        │ - Register    │  │ - Enhance     │  │ - Enhance     │
        │ - Login       │  │ - Resize      │  │ - Extract     │
        │ - Refresh     │  │ - List        │  │   frames      │
        │ - Logout      │  │ - Get/Delete  │  │ - Merge MKV   │
        └───────────────┘  └───────────────┘  └───────────────┘
                │                   │                   │
                │                   ▼                   ▼
                │          ┌───────────────┐   ┌───────────────┐
                │          │  Real-ESRGAN  │   │    ffmpeg     │
                │          │    Engine     │   │               │
                │          │               │   │ - Extract     │
                │          │ - GPU/CPU     │   │   audio/video │
                │          │ - Scale 2x-4x │   │ - Merge MKV   │
                │          │ - Tile-based  │   │ - Codecs      │
                │          │ - GFPGAN face │   └───────────────┘
                │          └───────────────┘
                │
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            MongoDB                                       │
│                                                                          │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌─────────────────┐     │
│  │   users   │  │  images   │  │  videos   │  │ refresh_tokens  │     │
│  │           │  │           │  │           │  │                 │     │
│  │ - email   │  │ - user_id │  │ - user_id │  │ - user_id       │     │
│  │ - pass    │  │ - paths   │  │ - status  │  │ - token         │     │
│  │ - active  │  │ - model   │  │ - frames  │  │ - expires_at    │     │
│  └───────────┘  └───────────┘  └───────────┘  └─────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
```

## Componentes del Sistema

### 1. API Layer (Handlers)

Los handlers de Tornado manejan las peticiones HTTP y las respuestas.

#### Auth Handlers (`app/handlers/auth.py`)
- **RegisterHandler**: Registro de nuevos usuarios
- **LoginHandler**: Autenticación y generación de tokens
- **RefreshTokenHandler**: Renovación de tokens de acceso
- **LogoutHandler**: Cierre de sesión e invalidación de tokens
- **MeHandler**: Obtención del perfil del usuario actual

#### Image Handlers (`app/handlers/images.py`)
- **ImageEnhanceHandler**: Procesamiento y mejora de imagenes
- **ImageListHandler**: Listado paginado de imagenes del usuario
- **ImageDetailHandler**: Detalle y eliminacion de imagenes

#### Video Handlers (`app/handlers/videos.py`)
- **VideoEnhanceHandler**: Inicia procesamiento asincrono de videos
- **VideoListHandler**: Listado paginado de videos con status
- **VideoDetailHandler**: Detalle, descarga y eliminacion de videos

#### System Handlers (`app/handlers/health.py`)
- **HealthHandler**: Verificacion del estado del sistema
- **InfoHandler**: Informacion sobre el API
- **ModelsHandler**: Lista de modelos disponibles

### 2. Service Layer

#### Auth Service (`app/services/auth_service.py`)
Gestiona toda la lógica de autenticación:
- Registro de usuarios con validación
- Autenticación con email/password
- Generación y validación de tokens JWT
- Gestión de refresh tokens
- Logout y revocación de tokens

#### Image Service (`app/services/image_service.py`)
Gestiona el procesamiento de imagenes:
- Decodificacion de imagenes base64
- Inicializacion del modelo Real-ESRGAN
- Procesamiento configurable GPU/CPU
- Redimensionado a tamano de salida especifico
- Almacenamiento de resultados en disco
- Gestion del historial de imagenes
- Face Enhancement con GFPGAN

#### Video Service (`app/services/video_service.py`)
Gestiona el procesamiento de videos:
- Procesamiento asincrono en background
- Extraccion de audio con ffmpeg (usa `/usr/bin/ffmpeg` del sistema)
- Extraccion de frames individuales (PNG)
- Procesamiento de cada frame con Real-ESRGAN
- Face Enhancement opcional con GFPGAN
- Reconstruccion del video en formato MKV (H.264 + AAC)
- Video original conserva su extension original (.mp4, .avi, etc.)
- Tracking de progreso (frames procesados)
- Status: pending, in_progress, completed, error

**Nota tecnica:** Se usa `/usr/bin/ffmpeg` en lugar del ffmpeg de Conda porque el de Conda no incluye el encoder libx264.

### 3. Data Layer

#### Models (`app/models/`)
Definiciones de modelos usando Pydantic:
- **User models**: UserCreate, UserLogin, UserResponse, UserInDB
- **Image models**: ImageEnhanceRequest, ImageResponse, ImageDetailResponse
- **Video models**: VideoEnhanceRequest, VideoResponse, VideoDetailResponse
- **Token models**: TokenPair, TokenData, RefreshTokenRequest

#### Campos en Video models:
| Campo | Tipo | Descripcion |
|-------|------|-------------|
| status | enum | pending, in_progress, completed, error |
| frames_processed | int | Frames procesados hasta el momento |
| frame_count | int | Total de frames del video |
| duration_seconds | float | Duracion del video |
| fps | float | Frames por segundo |
| face_enhance | bool | Mejora de rostros activada |

#### Database (`app/database.py`)
Conexión y gestión de MongoDB usando Motor (driver async).

### 4. Security Layer

#### Utils (`app/utils/security.py`)
- **Password hashing**: bcrypt para almacenamiento seguro
- **JWT tokens**: Generación y validación de access tokens
- **Refresh tokens**: Tokens seguros para renovación

## Flujo de Autenticación

```
┌──────────┐                    ┌──────────┐                    ┌──────────┐
│  Client  │                    │   API    │                    │ MongoDB  │
└────┬─────┘                    └────┬─────┘                    └────┬─────┘
     │                               │                               │
     │  POST /api/auth/login         │                               │
     │  {email, password}            │                               │
     │──────────────────────────────>│                               │
     │                               │  Find user by email           │
     │                               │──────────────────────────────>│
     │                               │                               │
     │                               │  User document                │
     │                               │<──────────────────────────────│
     │                               │                               │
     │                               │  Verify password (bcrypt)     │
     │                               │                               │
     │                               │  Generate JWT access token    │
     │                               │  Generate refresh token       │
     │                               │                               │
     │                               │  Store refresh token          │
     │                               │──────────────────────────────>│
     │                               │                               │
     │  {access_token, refresh_token}│                               │
     │<──────────────────────────────│                               │
     │                               │                               │
     │  GET /api/images              │                               │
     │  Authorization: Bearer {jwt}  │                               │
     │──────────────────────────────>│                               │
     │                               │  Decode & validate JWT        │
     │                               │                               │
     │                               │  Query images                 │
     │                               │──────────────────────────────>│
     │                               │                               │
     │                               │  Images list                  │
     │                               │<──────────────────────────────│
     │                               │                               │
     │  {images: [...]}              │                               │
     │<──────────────────────────────│                               │
```

## Flujo de Procesamiento de Imagenes

```
┌──────────┐                    ┌──────────┐       ┌──────────┐       ┌──────────┐
│  Client  │                    │   API    │       │Real-ESRGAN│      │ MongoDB  │
└────┬─────┘                    └────┬─────┘       └────┬─────┘       └────┬─────┘
     │                               │                  │                  │
     │  POST /api/images/enhance     │                  │                  │
     │  {image_base64, model_type}   │                  │                  │
     │──────────────────────────────>│                  │                  │
     │                               │                  │                  │
     │                               │  Decode base64   │                  │
     │                               │  Validate image  │                  │
     │                               │                  │                  │
     │                               │  Process image   │                  │
     │                               │─────────────────>│                  │
     │                               │                  │  GPU/CPU         │
     │                               │                  │  Enhancement     │
     │                               │  Enhanced image  │                  │
     │                               │<─────────────────│                  │
     │                               │                  │                  │
     │                               │  Save to disk + Create record       │
     │                               │─────────────────────────────────────>│
     │                               │                  │                  │
     │  {enhanced_base64, metadata}  │                  │                  │
     │<──────────────────────────────│                  │                  │
```

## Flujo de Procesamiento de Videos (Asincrono)

```
┌──────────┐              ┌──────────┐       ┌──────────┐       ┌──────────┐
│  Client  │              │   API    │       │ ffmpeg + │       │ MongoDB  │
│          │              │          │       │Real-ESRGAN│      │          │
└────┬─────┘              └────┬─────┘       └────┬─────┘       └────┬─────┘
     │                         │                  │                  │
     │  POST /api/videos/enhance                  │                  │
     │  {video_base64, model_type}                │                  │
     │────────────────────────>│                  │                  │
     │                         │                  │                  │
     │                         │  Create record (status: pending)    │
     │                         │─────────────────────────────────────>│
     │                         │                  │                  │
     │  202 Accepted           │                  │                  │
     │  {video_id, status}     │                  │                  │
     │<────────────────────────│                  │                  │
     │                         │                  │                  │
     │                         │  [BACKGROUND TASK]                  │
     │                         │  Update status: in_progress         │
     │                         │─────────────────────────────────────>│
     │                         │                  │                  │
     │                         │  Extract audio   │                  │
     │                         │─────────────────>│                  │
     │                         │                  │                  │
     │                         │  Extract frames  │                  │
     │                         │─────────────────>│  frame_001.png   │
     │                         │                  │  frame_002.png   │
     │                         │                  │  ...             │
     │                         │                  │                  │
     │                         │  Process each frame with Real-ESRGAN│
     │                         │─────────────────>│                  │
     │                         │                  │  GPU/CPU         │
     │                         │                  │  + GFPGAN (opt)  │
     │                         │                  │                  │
     │                         │  Update frames_processed            │
     │                         │─────────────────────────────────────>│
     │                         │                  │                  │
     │  GET /api/videos/{id}   │                  │                  │
     │────────────────────────>│                  │                  │
     │  {status: in_progress,  │                  │                  │
     │   frames_processed: 50} │                  │                  │
     │<────────────────────────│                  │                  │
     │                         │                  │                  │
     │                         │  Merge frames + audio -> MKV        │
     │                         │─────────────────>│                  │
     │                         │                  │                  │
     │                         │  Update status: completed           │
     │                         │─────────────────────────────────────>│
     │                         │                  │                  │
     │  GET /api/videos/{id}   │                  │                  │
     │────────────────────────>│                  │                  │
     │  {status: completed,    │                  │                  │
     │   enhanced_base64: ...} │                  │                  │
     │<────────────────────────│                  │                  │
```

## Estructura de Carpetas

```
calidad_imagen/
├── .env                    # Variables de entorno
├── docker-compose.yml      # Orquestación de contenedores
├── mongo-init.js           # Script de inicialización MongoDB
│
├── API/
│   ├── Dockerfile          # Imagen Docker del API
│   ├── requirements.txt    # Dependencias Python
│   ├── main.py             # Punto de entrada
│   ├── sonar-project.properties  # Configuracion SonarQube
│   │
│   └── app/
│       ├── __init__.py
│       ├── config.py       # Configuración desde env
│       ├── database.py     # Conexión MongoDB
│       │
│       ├── handlers/       # Controladores HTTP
│       │   ├── __init__.py
│       │   ├── base.py     # Handler base con auth
│       │   ├── auth.py     # Endpoints de auth
│       │   ├── images.py   # Endpoints de imágenes
│       │   ├── videos.py   # Endpoints de videos
│       │   ├── health.py   # Endpoints de sistema
│       │   └── swagger.py  # Swagger UI
│       │
│       ├── models/         # Modelos Pydantic
│       │   ├── __init__.py
│       │   ├── user.py     # Modelos de usuario
│       │   ├── image.py    # Modelos de imagen
│       │   └── video.py    # Modelos de video
│       │
│       ├── services/       # Logica de negocio
│       │   ├── __init__.py
│       │   ├── auth_service.py   # Servicio auth
│       │   ├── image_service.py  # Servicio imagenes + Real-ESRGAN + GFPGAN
│       │   └── video_service.py  # Servicio videos + ffmpeg
│       │
│       └── utils/          # Utilidades
│           ├── __init__.py
│           └── security.py # JWT y passwords
│
├── sonarqube/              # Analisis de calidad
│   └── docker-compose.sonarqube.yml
│
├── pruebas/                # Scripts de prueba
│   ├── prueba.png
│   ├── prueba_video.mp4
│   ├── prueba_video_face.mp4
│   ├── test_all_models.py
│   ├── test_all_models_face_enhance.py
│   ├── test_video.py
│   └── test_video_face_enhance.py
│
└── docs/
    ├── ARQUITECTURA.md
    ├── MANUAL_USUARIO_API.md
    ├── ESTADO_PROYECTO.md
    └── api_collection.json
```

## Base de Datos

### Colección: users
```javascript
{
  _id: ObjectId,
  username: String,       // Único
  email: String,          // Único
  hashed_password: String,
  is_active: Boolean,
  created_at: Date,
  updated_at: Date
}
```

### Coleccion: images
```javascript
{
  _id: ObjectId,
  user_id: String,
  original_filename: String,
  description: String,
  original_path: String,       // Ruta al archivo en disco
  enhanced_path: String,       // Ruta al archivo en disco
  original_width: Number,
  original_height: Number,
  enhanced_width: Number,
  enhanced_height: Number,
  model_type: String,
  scale: Number,
  face_enhance: Boolean,
  status: String,              // completed, failed
  error_message: String,
  processing_time_ms: Number,
  gpu_used: Boolean,
  created_at: Date,
  completed_at: Date
}
```

### Coleccion: videos
```javascript
{
  _id: ObjectId,
  user_id: String,
  original_filename: String,
  description: String,
  original_path: String,       // Ruta al video original (conserva extension original)
  enhanced_path: String,       // Ruta al video mejorado (siempre MKV)
  model_type: String,
  scale: Number,
  face_enhance: Boolean,
  // Metadata del video
  duration_seconds: Number,
  fps: Number,
  frame_count: Number,
  original_width: Number,
  original_height: Number,
  enhanced_width: Number,
  enhanced_height: Number,
  // Status de procesamiento
  status: String,              // pending, in_progress, completed, error
  error_message: String,
  processing_time_ms: Number,
  gpu_used: Boolean,
  frames_processed: Number,    // Progreso del procesamiento
  created_at: Date,
  completed_at: Date
}
```

### Colección: refresh_tokens
```javascript
{
  _id: ObjectId,
  user_id: String,
  token: String,           // Único
  expires_at: Date,        // TTL index
  created_at: Date
}
```

## Seguridad

### Autenticación JWT
- **Access Token**: Válido por 30 minutos (configurable)
- **Refresh Token**: Válido por 7 días (configurable)
- Algoritmo: HS256
- Los refresh tokens se almacenan en MongoDB con TTL

### Password Hashing
- Algoritmo: bcrypt
- Salt automático
- Costo de hashing configurable

### CORS
- Headers configurados para permitir requests cross-origin
- Soporte para preflight requests (OPTIONS)

### Contenedores
- Usuario no-root en contenedor API
- Healthchecks configurados
- Red aislada entre contenedores

## Configuración

### Archivo .env

Todas las variables de entorno se configuran en el archivo `.env` en la raíz del proyecto:

```env
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

# JWT Configuration
JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# GPU Configuration
USE_GPU=TRUE          # TRUE para GPU NVIDIA, FALSE para CPU

# Real-ESRGAN Configuration
DEFAULT_SCALE=4
TILE_SIZE=512
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
| MONGO_HOST | Host de MongoDB | 192.168.86.10 |
| MONGO_PORT | Puerto de MongoDB | 27017 |
| MONGO_DB | Nombre de la base de datos | image_enhancer |
| API_PORT | Puerto del API | 8888 |
| API_DEBUG | Modo debug | false |
| JWT_SECRET_KEY | Clave secreta para JWT | - |
| JWT_ACCESS_TOKEN_EXPIRE_MINUTES | Expiración access token (min) | 30 |
| JWT_REFRESH_TOKEN_EXPIRE_DAYS | Expiración refresh token (días) | 7 |
| **USE_GPU** | **Usar GPU NVIDIA** | **TRUE** |
| DEFAULT_SCALE | Escala por defecto | 4 |
| TILE_SIZE | Tamaño de tile para procesamiento | 512 |
| NETWORK_SUBNET | Subnet de la red Docker | 192.168.86.0/24 |

## Escalabilidad

### Horizontal
- El API es stateless (sin estado en servidor)
- Múltiples instancias pueden correr detrás de un load balancer
- MongoDB soporta réplicas y sharding

### Vertical
- **GPU dedicada para procesamiento de imágenes**
- Procesamiento por tiles para imágenes grandes
- Configuración de tile_size ajustable
- **Redimensionado post-procesamiento para tamaños específicos**

## Requisitos del Sistema

### Para uso con GPU (USE_GPU=TRUE)
- NVIDIA GPU con CUDA 12.1+
- NVIDIA Driver 525+
- NVIDIA Container Toolkit instalado
- Docker con soporte nvidia runtime

### Para uso con CPU (USE_GPU=FALSE)
- CPU multi-core (recomendado 4+ cores)
- 8GB+ RAM
- Procesamiento más lento pero sin requisitos de hardware especial

## Dependencias Principales

| Paquete | Versión | Propósito |
|---------|---------|-----------|
| tornado | 6.4+ | Framework web asíncrono |
| motor | 3.3.2+ | Driver async MongoDB |
| PyJWT | 2.8.0+ | Tokens JWT |
| bcrypt | 4.1.2+ | Hash de passwords |
| Pillow | 10.2.0+ | Procesamiento de imágenes |
| torch | 2.0+ | Deep learning (GPU/CPU) |
| torchvision | 0.15+ | Utilidades de visión |
| pydantic | 2.5.0+ | Validacion de datos |
| numpy | 1.26+ | Operaciones numericas |
| ffmpeg | 4.x | Procesamiento de video (/usr/bin/ffmpeg con libx264) |
| gfpgan | 1.3.8+ | Mejora de rostros |

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

# Detener y eliminar volúmenes
docker-compose down -v

# Verificar estado de GPU en contenedor
docker exec image_enhancer_api python -c "import torch; print(torch.cuda.is_available())"
```

## Calidad de Codigo - SonarQube

El proyecto incluye configuracion para analisis de calidad con SonarQube.

### Metricas Actuales (v2.2.0)

| Metrica | Valor |
|---------|-------|
| Bugs | 0 |
| Vulnerabilidades | 0 |
| Security Hotspots | 0 |
| Code Smells | 0 |
| Quality Gate | PASSED |
| Reliability Rating | A |
| Security Rating | A |
| Maintainability Rating | A |

### Ejecutar Analisis

```bash
# 1. Iniciar SonarQube
docker-compose -f sonarqube/docker-compose.sonarqube.yml up -d

# 2. Esperar que inicie (~2 minutos)
# Acceder a http://localhost:9000 (admin/admin)

# 3. Generar token en SonarQube UI o via API

# 4. Ejecutar scanner
docker run --rm --network sonarqube_sonarnet \
  -v "$(pwd)/API:/usr/src" \
  sonarsource/sonar-scanner-cli:latest \
  -Dsonar.projectKey=image-enhancer-api \
  -Dsonar.sources=. \
  -Dsonar.host.url=http://sonarqube:9000 \
  -Dsonar.login=<TOKEN> \
  -Dsonar.python.version=3.11 \
  -Dsonar.exclusions="**/__pycache__/**,**/*.pyc,**/weights/**,**/swagger.py"
```

### Refactorizaciones Aplicadas

Para cumplir con los estandares de calidad, se realizaron las siguientes refactorizaciones:

**image_service.py:**
- Parametro `format` renombrado a `img_format` (evita ocultar builtin de Python)
- Metodos extraidos en GFPGANer: `_load_model_weights()`, `_get_state_dict_key()`, `_apply_compatible_weights()`
- Metodos extraidos: `_process_image_enhancement()`, `_apply_face_enhancement()`

**video_service.py:**
- Excepcion personalizada `VideoProcessingError` creada
- Excepciones genericas reemplazadas por `VideoProcessingError`
- Metodos extraidos: `_extract_audio()`, `_extract_frames()`, `_process_frames()`, `_create_video_from_frames()`, `_merge_audio_video()`
