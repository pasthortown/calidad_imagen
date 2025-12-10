"""Handler para servir documentación Swagger/OpenAPI."""

from app.handlers.base import BaseHandler
from app.models.image import ModelType, MODEL_CONFIG

# Especificación OpenAPI 3.0
# NOSONAR: Los literales duplicados como "application/json" son inherentes al formato OpenAPI
OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Image Enhancer API",
        "description": "API REST para mejora de imágenes usando Real-ESRGAN con múltiples modelos",
        "version": "1.1.0",
        "contact": {
            "name": "Image Enhancer API"
        }
    },
    "servers": [
        {
            "url": "http://localhost:8888",
            "description": "Servidor de desarrollo"
        }
    ],
    "tags": [
        {"name": "Auth", "description": "Autenticacion y gestion de usuarios"},
        {"name": "Images", "description": "Procesamiento y gestion de imagenes"},
        {"name": "Videos", "description": "Procesamiento y gestion de videos"},
        {"name": "System", "description": "Estado del sistema y configuracion"}
    ],
    "paths": {
        "/api/auth/register": {
            "post": {
                "tags": ["Auth"],
                "summary": "Registrar nuevo usuario",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RegisterRequest"}
                        }
                    }
                },
                "responses": {
                    "201": {"description": "Usuario registrado exitosamente"},
                    "400": {"description": "Datos inválidos o usuario ya existe"}
                }
            }
        },
        "/api/auth/login": {
            "post": {
                "tags": ["Auth"],
                "summary": "Iniciar sesión",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/LoginRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {
                        "description": "Login exitoso",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/LoginResponse"}
                            }
                        }
                    },
                    "401": {"description": "Credenciales inválidas"}
                }
            }
        },
        "/api/auth/refresh": {
            "post": {
                "tags": ["Auth"],
                "summary": "Refrescar token de acceso",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/RefreshRequest"}
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Token refrescado"},
                    "401": {"description": "Token inválido"}
                }
            }
        },
        "/api/auth/logout": {
            "post": {
                "tags": ["Auth"],
                "summary": "Cerrar sesión",
                "security": [{"bearerAuth": []}],
                "responses": {
                    "200": {"description": "Sesión cerrada"}
                }
            }
        },
        "/api/auth/me": {
            "get": {
                "tags": ["Auth"],
                "summary": "Obtener información del usuario actual",
                "security": [{"bearerAuth": []}],
                "responses": {
                    "200": {"description": "Información del usuario"}
                }
            }
        },
        "/api/images/enhance": {
            "post": {
                "tags": ["Images"],
                "summary": "Mejorar una imagen",
                "description": "Procesa una imagen con Real-ESRGAN usando el modelo especificado",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ImageEnhanceRequest"}
                        }
                    }
                },
                "responses": {
                    "201": {
                        "description": "Imagen procesada exitosamente",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ImageDetailResponse"}
                            }
                        }
                    },
                    "400": {"description": "Datos inválidos"},
                    "401": {"description": "No autorizado"}
                }
            }
        },
        "/api/images": {
            "get": {
                "tags": ["Images"],
                "summary": "Listar imágenes del usuario",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {
                        "name": "page",
                        "in": "query",
                        "schema": {"type": "integer", "default": 1}
                    },
                    {
                        "name": "per_page",
                        "in": "query",
                        "schema": {"type": "integer", "default": 10}
                    },
                    {
                        "name": "status",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["pending", "processing", "completed", "failed"]}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de imágenes",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ImageListResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/images/{id}": {
            "get": {
                "tags": ["Images"],
                "summary": "Obtener imagen por ID",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Detalle de la imagen",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ImageDetailResponse"}
                            }
                        }
                    },
                    "404": {"description": "Imagen no encontrada"}
                }
            },
            "delete": {
                "tags": ["Images"],
                "summary": "Eliminar imagen",
                "description": "Elimina la imagen de la base de datos y los archivos del disco",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {"description": "Imagen eliminada"},
                    "404": {"description": "Imagen no encontrada"}
                }
            }
        },
        "/api/videos/enhance": {
            "post": {
                "tags": ["Videos"],
                "summary": "Mejorar un video",
                "description": "Inicia el procesamiento de un video con Real-ESRGAN. El procesamiento es asincrono.",
                "security": [{"bearerAuth": []}],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/VideoEnhanceRequest"}
                        }
                    }
                },
                "responses": {
                    "202": {
                        "description": "Video recibido, procesamiento iniciado",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/VideoResponse"}
                            }
                        }
                    },
                    "400": {"description": "Datos invalidos"},
                    "401": {"description": "No autorizado"}
                }
            }
        },
        "/api/videos": {
            "get": {
                "tags": ["Videos"],
                "summary": "Listar videos del usuario",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {
                        "name": "page",
                        "in": "query",
                        "schema": {"type": "integer", "default": 1}
                    },
                    {
                        "name": "per_page",
                        "in": "query",
                        "schema": {"type": "integer", "default": 10}
                    },
                    {
                        "name": "status",
                        "in": "query",
                        "schema": {"type": "string", "enum": ["pending", "in_progress", "completed", "error"]}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Lista de videos",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/VideoListResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/videos/{id}": {
            "get": {
                "tags": ["Videos"],
                "summary": "Obtener video por ID",
                "description": "Obtiene el detalle de un video. Si status es 'completed', incluye los videos en base64.",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {
                        "description": "Detalle del video",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/VideoDetailResponse"}
                            }
                        }
                    },
                    "404": {"description": "Video no encontrado"}
                }
            },
            "delete": {
                "tags": ["Videos"],
                "summary": "Eliminar video",
                "description": "Elimina el video de la base de datos y los archivos del disco",
                "security": [{"bearerAuth": []}],
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"}
                    }
                ],
                "responses": {
                    "200": {"description": "Video eliminado"},
                    "404": {"description": "Video no encontrado"}
                }
            }
        },
        "/api/health": {
            "get": {
                "tags": ["System"],
                "summary": "Estado del sistema",
                "responses": {
                    "200": {
                        "description": "Estado del sistema",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/HealthResponse"}
                            }
                        }
                    }
                }
            }
        },
        "/api/info": {
            "get": {
                "tags": ["System"],
                "summary": "Información del API",
                "responses": {
                    "200": {"description": "Información del API"}
                }
            }
        },
        "/api/models": {
            "get": {
                "tags": ["System"],
                "summary": "Listar modelos disponibles",
                "description": "Retorna la lista de modelos de Real-ESRGAN disponibles",
                "responses": {
                    "200": {
                        "description": "Lista de modelos",
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/ModelsResponse"}
                            }
                        }
                    }
                }
            }
        }
    },
    "components": {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        },
        "schemas": {
            "RegisterRequest": {
                "type": "object",
                "required": ["email", "username", "password"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "username": {"type": "string", "minLength": 3},
                    "password": {"type": "string", "minLength": 6}
                }
            },
            "LoginRequest": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string"}
                }
            },
            "LoginResponse": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "user": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "email": {"type": "string"},
                            "username": {"type": "string"}
                        }
                    },
                    "tokens": {
                        "type": "object",
                        "properties": {
                            "access_token": {"type": "string"},
                            "refresh_token": {"type": "string"},
                            "token_type": {"type": "string"}
                        }
                    }
                }
            },
            "RefreshRequest": {
                "type": "object",
                "required": ["refresh_token"],
                "properties": {
                    "refresh_token": {"type": "string"}
                }
            },
            "ImageEnhanceRequest": {
                "type": "object",
                "required": ["image_base64"],
                "properties": {
                    "image_base64": {
                        "type": "string",
                        "description": "Imagen codificada en base64"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Nombre del archivo original"
                    },
                    "description": {
                        "type": "string",
                        "description": "Descripción de la imagen. Si está vacía, se genera automáticamente"
                    },
                    "model_type": {
                        "type": "string",
                        "enum": ["general_x4", "general_x2", "anime", "anime_video", "general_v3"],
                        "default": "general_x4",
                        "description": "Tipo de modelo a usar"
                    },
                    "scale": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 4,
                        "description": "Factor de escala (1-4)"
                    },
                    "face_enhance": {
                        "type": "boolean",
                        "default": False,
                        "description": "Aplicar mejora de rostros con GFPGAN después del upscaling"
                    },
                    "output_width": {
                        "type": "integer",
                        "description": "Ancho de salida deseado"
                    },
                    "output_height": {
                        "type": "integer",
                        "description": "Alto de salida deseado"
                    }
                }
            },
            "ImageResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "original_filename": {"type": "string"},
                    "description": {"type": "string"},
                    "original_width": {"type": "integer"},
                    "original_height": {"type": "integer"},
                    "enhanced_width": {"type": "integer"},
                    "enhanced_height": {"type": "integer"},
                    "model_type": {"type": "string"},
                    "scale": {"type": "integer"},
                    "face_enhance": {"type": "boolean"},
                    "status": {"type": "string"},
                    "processing_time_ms": {"type": "integer"},
                    "gpu_used": {"type": "boolean"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "completed_at": {"type": "string", "format": "date-time"}
                }
            },
            "ImageDetailResponse": {
                "allOf": [
                    {"$ref": "#/components/schemas/ImageResponse"},
                    {
                        "type": "object",
                        "properties": {
                            "original_base64": {"type": "string"},
                            "enhanced_base64": {"type": "string"},
                            "error_message": {"type": "string"}
                        }
                    }
                ]
            },
            "ImageListResponse": {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "page": {"type": "integer"},
                    "per_page": {"type": "integer"},
                    "images": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/ImageResponse"}
                    }
                }
            },
            "VideoEnhanceRequest": {
                "type": "object",
                "required": ["video_base64", "filename"],
                "properties": {
                    "video_base64": {
                        "type": "string",
                        "description": "Video codificado en base64"
                    },
                    "filename": {
                        "type": "string",
                        "description": "Nombre del archivo original con extension"
                    },
                    "description": {
                        "type": "string",
                        "description": "Descripcion del video. Si esta vacia, se genera automaticamente"
                    },
                    "model_type": {
                        "type": "string",
                        "enum": ["general_x4", "general_x2", "anime", "anime_video", "general_v3"],
                        "default": "general_x4",
                        "description": "Tipo de modelo a usar"
                    },
                    "scale": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 4,
                        "description": "Factor de escala (1-4)"
                    },
                    "face_enhance": {
                        "type": "boolean",
                        "default": False,
                        "description": "Aplicar mejora de rostros con GFPGAN despues del upscaling"
                    }
                }
            },
            "VideoResponse": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "original_filename": {"type": "string"},
                    "description": {"type": "string"},
                    "original_width": {"type": "integer"},
                    "original_height": {"type": "integer"},
                    "enhanced_width": {"type": "integer"},
                    "enhanced_height": {"type": "integer"},
                    "duration_seconds": {"type": "number"},
                    "fps": {"type": "number"},
                    "frame_count": {"type": "integer"},
                    "model_type": {"type": "string"},
                    "scale": {"type": "integer"},
                    "face_enhance": {"type": "boolean"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "error"]},
                    "error_message": {"type": "string"},
                    "processing_time_ms": {"type": "integer"},
                    "gpu_used": {"type": "boolean"},
                    "frames_processed": {"type": "integer"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "completed_at": {"type": "string", "format": "date-time"}
                }
            },
            "VideoDetailResponse": {
                "allOf": [
                    {"$ref": "#/components/schemas/VideoResponse"},
                    {
                        "type": "object",
                        "properties": {
                            "original_base64": {"type": "string"},
                            "enhanced_base64": {"type": "string"}
                        }
                    }
                ]
            },
            "VideoListResponse": {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "page": {"type": "integer"},
                    "per_page": {"type": "integer"},
                    "videos": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/VideoResponse"}
                    }
                }
            },
            "HealthResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string"},
                    "services": {
                        "type": "object",
                        "properties": {
                            "api": {"type": "string"},
                            "mongodb": {"type": "string"},
                            "gpu": {"type": "string"}
                        }
                    }
                }
            },
            "ModelsResponse": {
                "type": "object",
                "properties": {
                    "total": {"type": "integer"},
                    "models": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "name": {"type": "string"},
                                "description": {"type": "string"},
                                "default_scale": {"type": "integer"},
                                "supported_scales": {
                                    "type": "array",
                                    "items": {"type": "integer"}
                                },
                                "use_case": {"type": "string"},
                                "recommended_for": {
                                    "type": "array",
                                    "items": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

# HTML de Swagger UI
SWAGGER_UI_HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image Enhancer API - Swagger UI</title>
    <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    <style>
        body { margin: 0; padding: 0; }
        .swagger-ui .topbar { display: none; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {
            SwaggerUIBundle({
                url: "/api/docs/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
                deepLinking: true,
                showExtensions: true,
                showCommonExtensions: true
            });
        };
    </script>
</body>
</html>
"""


class SwaggerUIHandler(BaseHandler):
    """Sirve la interfaz de Swagger UI."""

    async def get(self):
        """GET /api/docs - Swagger UI"""
        self.set_header("Content-Type", "text/html")
        self.write(SWAGGER_UI_HTML)


class OpenAPISpecHandler(BaseHandler):
    """Sirve la especificación OpenAPI en JSON."""

    async def get(self):
        """GET /api/docs/openapi.json - OpenAPI Specification"""
        self.write_json(OPENAPI_SPEC)
