from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ImageStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ModelType(str, Enum):
    """Tipos de modelos disponibles para mejora de imágenes.

    Cada modelo está optimizado para diferentes casos de uso:
    - GENERAL_X4: Modelo general para fotos reales, escala 4x (default)
    - GENERAL_X2: Modelo general para fotos reales, escala 2x
    - ANIME: Optimizado para anime e ilustraciones, escala 4x
    - ANIME_VIDEO: Optimizado para video anime (también funciona con imágenes)
    - GENERAL_V3: Modelo general compacto v3, bueno para escenas generales
    """
    GENERAL_X4 = "general_x4"      # RealESRGAN_x4plus - Fotos reales 4x
    GENERAL_X2 = "general_x2"      # RealESRGAN_x2plus - Fotos reales 2x
    ANIME = "anime"                # RealESRGAN_x4plus_anime_6B - Anime/ilustraciones
    ANIME_VIDEO = "anime_video"    # realesr-animevideov3 - Video anime
    GENERAL_V3 = "general_v3"      # realesr-general-x4v3 - General compacto


# Configuración de cada modelo
MODEL_CONFIG = {
    ModelType.GENERAL_X4: {
        "filename": "RealESRGAN_x4plus.pth",
        "scale": 4,
        "num_block": 23,
        "num_feat": 64,
        "num_grow_ch": 32,
        "description": "Modelo general para fotos reales - Alta calidad, escala 4x",
    },
    ModelType.GENERAL_X2: {
        "filename": "RealESRGAN_x2plus.pth",
        "scale": 2,
        "num_block": 23,
        "num_feat": 64,
        "num_grow_ch": 32,
        "description": "Modelo general para fotos reales - Escala 2x",
    },
    ModelType.ANIME: {
        "filename": "RealESRGAN_x4plus_anime_6B.pth",
        "scale": 4,
        "num_block": 6,  # Modelo más pequeño
        "num_feat": 64,
        "num_grow_ch": 32,
        "description": "Optimizado para anime e ilustraciones - Más rápido",
    },
    ModelType.ANIME_VIDEO: {
        "filename": "realesr-animevideov3.pth",
        "scale": 4,  # Soporta x1, x2, x3, x4
        "num_block": 6,
        "num_feat": 64,
        "num_grow_ch": 32,
        "num_conv": 16,  # Arquitectura VGG-style
        "description": "Modelo para video anime - También funciona con imágenes",
    },
    ModelType.GENERAL_V3: {
        "filename": "realesr-general-x4v3.pth",
        "scale": 4,
        "num_block": 6,
        "num_feat": 64,
        "num_grow_ch": 32,
        "num_conv": 32,  # Arquitectura VGG-style
        "description": "Modelo general compacto v3 - Rápido y eficiente",
    },
}


class ImageEnhanceRequest(BaseModel):
    """Request para mejorar una imagen."""
    image_base64: str = Field(..., description="Imagen codificada en base64")
    filename: Optional[str] = Field(None, description="Nombre del archivo original")
    description: Optional[str] = Field(
        None,
        description="Descripción de la imagen. Si está vacía, se genera automáticamente"
    )
    model_type: Optional[ModelType] = Field(
        ModelType.GENERAL_X4,
        description="Tipo de modelo a usar: general_x4, general_x2, anime, anime_video, general_v3"
    )
    scale: Optional[int] = Field(
        None,
        ge=1,
        le=4,
        description="Factor de escala (1-4). Si no se especifica, usa el default del modelo"
    )
    face_enhance: Optional[bool] = Field(
        False,
        description="Aplicar mejora de rostros con GFPGAN después del upscaling"
    )
    output_width: Optional[int] = Field(None, ge=1, description="Ancho de salida deseado (opcional)")
    output_height: Optional[int] = Field(None, ge=1, description="Alto de salida deseado (opcional)")


class ImageRecord(BaseModel):
    """Modelo para el registro de imagen en MongoDB (sin datos binarios)."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    original_filename: str
    description: str
    original_width: int
    original_height: int
    enhanced_width: Optional[int] = None
    enhanced_height: Optional[int] = None
    model_type: str
    scale: int
    face_enhance: bool = False
    # Rutas a los archivos en disco
    original_path: str
    enhanced_path: Optional[str] = None
    # Metadata
    status: ImageStatus
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    gpu_used: Optional[bool] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        use_enum_values = True


class ImageResponse(BaseModel):
    """Respuesta con metadata de imagen (sin datos binarios)."""
    id: str
    original_filename: str
    description: str
    original_width: int
    original_height: int
    enhanced_width: Optional[int]
    enhanced_height: Optional[int]
    model_type: str
    scale: int
    face_enhance: bool = False
    status: str
    processing_time_ms: Optional[int]
    gpu_used: Optional[bool]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ImageDetailResponse(ImageResponse):
    """Respuesta detallada con las imágenes en base64."""
    original_base64: Optional[str] = None
    enhanced_base64: Optional[str] = None
    error_message: Optional[str] = None


class ImageListResponse(BaseModel):
    """Respuesta de lista paginada de imágenes."""
    total: int
    page: int
    per_page: int
    images: list[ImageResponse]
