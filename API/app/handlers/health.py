import torch
from app.handlers.base import BaseHandler
from app.database import db
from app.models.image import ModelType, MODEL_CONFIG


class HealthHandler(BaseHandler):
    """Handler para health checks."""

    async def get(self):
        """GET /api/health - Verifica el estado del servicio."""
        health_status = {
            "status": "healthy",
            "services": {
                "api": "ok",
                "mongodb": "unknown",
                "gpu": "unknown"
            }
        }

        # Verificar MongoDB
        try:
            await db.client.admin.command('ping')
            health_status["services"]["mongodb"] = "ok"
        except Exception as e:
            health_status["services"]["mongodb"] = f"error: {str(e)}"
            health_status["status"] = "degraded"

        # Verificar GPU
        if torch.cuda.is_available():
            health_status["services"]["gpu"] = f"ok ({torch.cuda.get_device_name(0)})"
        else:
            health_status["services"]["gpu"] = "not available (using CPU)"

        self.write_json(health_status)


class InfoHandler(BaseHandler):
    """Handler para información del API."""

    async def get(self):
        """GET /api/info - Información del API."""
        # Construir información de modelos disponibles
        models_info = {}
        for model_type in ModelType:
            cfg = MODEL_CONFIG[model_type]
            models_info[model_type.value] = {
                "description": cfg["description"],
                "default_scale": cfg["scale"],
                "use_case": self._get_use_case(model_type)
            }

        info = {
            "name": "Image Enhancer API",
            "version": "1.1.0",
            "description": "API para mejora de imágenes usando Real-ESRGAN con múltiples modelos",
            "endpoints": {
                "auth": {
                    "POST /api/auth/register": "Registrar nuevo usuario",
                    "POST /api/auth/login": "Iniciar sesión",
                    "POST /api/auth/refresh": "Refrescar tokens",
                    "POST /api/auth/logout": "Cerrar sesión",
                    "GET /api/auth/me": "Obtener usuario actual"
                },
                "images": {
                    "POST /api/images/enhance": "Mejorar imagen",
                    "GET /api/images": "Listar imágenes",
                    "GET /api/images/{id}": "Obtener imagen",
                    "DELETE /api/images/{id}": "Eliminar imagen"
                },
                "system": {
                    "GET /api/health": "Estado del servicio",
                    "GET /api/info": "Información del API",
                    "GET /api/models": "Listar modelos disponibles"
                }
            },
            "supported_formats": ["png", "jpg", "jpeg", "webp"],
            "max_scale": 4,
            "available_models": models_info
        }

        self.write_json(info)

    def _get_use_case(self, model_type: ModelType) -> str:
        """Retorna el caso de uso recomendado para cada modelo."""
        use_cases = {
            ModelType.GENERAL_X4: "Fotos reales, retratos, paisajes - Alta calidad",
            ModelType.GENERAL_X2: "Fotos reales cuando se necesita escala 2x",
            ModelType.ANIME: "Anime, manga, ilustraciones, arte digital",
            ModelType.ANIME_VIDEO: "Frames de video anime, animaciones",
            ModelType.GENERAL_V3: "Uso general, más rápido que x4plus"
        }
        return use_cases.get(model_type, "Uso general")


class ModelsHandler(BaseHandler):
    """Handler para listar modelos disponibles."""

    async def get(self):
        """GET /api/models - Lista los modelos disponibles para mejora de imágenes."""
        models = []
        for model_type in ModelType:
            cfg = MODEL_CONFIG[model_type]
            models.append({
                "id": model_type.value,
                "name": cfg["filename"].replace(".pth", ""),
                "description": cfg["description"],
                "default_scale": cfg["scale"],
                "supported_scales": self._get_supported_scales(model_type),
                "use_case": self._get_use_case(model_type),
                "recommended_for": self._get_recommended_for(model_type)
            })

        self.write_json({
            "total": len(models),
            "models": models
        })

    def _get_supported_scales(self, model_type: ModelType) -> list:
        """Retorna las escalas soportadas por cada modelo."""
        if model_type == ModelType.GENERAL_X2:
            return [2]
        elif model_type in [ModelType.ANIME_VIDEO, ModelType.GENERAL_V3]:
            return [1, 2, 3, 4]  # Modelos v3 soportan escalas variables
        else:
            return [4]

    def _get_use_case(self, model_type: ModelType) -> str:
        """Retorna el caso de uso recomendado para cada modelo."""
        use_cases = {
            ModelType.GENERAL_X4: "Fotos reales, retratos, paisajes - Alta calidad",
            ModelType.GENERAL_X2: "Fotos reales cuando se necesita escala 2x",
            ModelType.ANIME: "Anime, manga, ilustraciones, arte digital",
            ModelType.ANIME_VIDEO: "Frames de video anime, animaciones",
            ModelType.GENERAL_V3: "Uso general, más rápido que x4plus"
        }
        return use_cases.get(model_type, "Uso general")

    def _get_recommended_for(self, model_type: ModelType) -> list:
        """Retorna los tipos de contenido recomendados para cada modelo."""
        recommendations = {
            ModelType.GENERAL_X4: ["fotografías", "retratos", "paisajes", "arquitectura"],
            ModelType.GENERAL_X2: ["fotografías grandes", "imágenes de alta resolución"],
            ModelType.ANIME: ["anime", "manga", "ilustraciones", "arte digital", "comics"],
            ModelType.ANIME_VIDEO: ["frames de anime", "animaciones", "sprites"],
            ModelType.GENERAL_V3: ["uso general", "procesamiento rápido", "lotes de imágenes"]
        }
        return recommendations.get(model_type, ["uso general"])
