# Image Enhancer API

API REST para mejora de imágenes utilizando Real-ESRGAN con autenticación JWT.

## Inicio Rápido

### 1. Requisitos Previos
- Python 3.10+
- Docker Desktop
- GPU NVIDIA (opcional, para mejor rendimiento)

### 2. Levantar MongoDB

```bash
# Iniciar Docker Desktop primero, luego:
docker-compose up -d
```

### 3. Instalar Dependencias

```bash
cd API
pip install -r requirements.txt
```

### 4. Descargar Modelos (opcional, ya incluidos)

```bash
python download_models.py
```

### 5. Iniciar el Servidor

```bash
python main.py
```

El API estará disponible en `http://localhost:8888`

## Endpoints Principales

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | /api/auth/register | Registrar usuario |
| POST | /api/auth/login | Iniciar sesión |
| POST | /api/auth/refresh | Refrescar tokens |
| POST | /api/images/enhance | Mejorar imagen |
| GET | /api/images | Listar imágenes |
| GET | /api/images/{id} | Obtener imagen |
| DELETE | /api/images/{id} | Eliminar imagen |
| GET | /api/health | Estado del servicio |

## Ejemplo de Uso

```python
import requests
import base64

API = "http://localhost:8888"

# Login
r = requests.post(f"{API}/api/auth/login", json={
    "email": "usuario@ejemplo.com",
    "password": "mipassword"
})
token = r.json()["tokens"]["access_token"]

# Mejorar imagen
with open("imagen.jpg", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

r = requests.post(
    f"{API}/api/images/enhance",
    headers={"Authorization": f"Bearer {token}"},
    json={"image_base64": img_b64, "scale": 4}
)

# Guardar resultado
result = r.json()["image"]["enhanced_base64"]
with open("mejorada.png", "wb") as f:
    f.write(base64.b64decode(result))
```

## Documentación

- [Arquitectura](docs/ARQUITECTURA.md)
- [Manual de Usuario API](docs/MANUAL_USUARIO_API.md)

## Estructura del Proyecto

```
calidad_imagen/
├── API/
│   ├── app/
│   │   ├── handlers/      # Controladores HTTP
│   │   ├── models/        # Modelos de datos
│   │   ├── services/      # Lógica de negocio
│   │   └── utils/         # Utilidades
│   ├── weights/           # Modelos Real-ESRGAN
│   ├── main.py            # Punto de entrada
│   └── requirements.txt
├── docs/                  # Documentación
└── docker-compose.yml     # MongoDB
```
