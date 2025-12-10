from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum

from app.models.image import ModelType


class VideoStatus(str, Enum):
    """Estados posibles para el procesamiento de video."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"


# Extensiones de video soportadas
VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'}

# Extensiones de imagen soportadas
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif'}


class VideoEnhanceRequest(BaseModel):
    """Request para mejorar un video."""
    video_base64: str = Field(..., description="Video codificado en base64")
    filename: str = Field(..., description="Nombre del archivo original con extension")
    description: Optional[str] = Field(
        None,
        description="Descripcion del video. Si esta vacia, se genera automaticamente"
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
        description="Aplicar mejora de rostros con GFPGAN despues del upscaling"
    )


class VideoRecord(BaseModel):
    """Modelo para el registro de video en MongoDB."""
    id: Optional[str] = Field(default=None, alias="_id")
    user_id: str
    original_filename: str
    description: str
    # Rutas a los archivos en disco
    original_path: str
    enhanced_path: Optional[str] = None
    # Configuracion de procesamiento
    model_type: str
    scale: int
    face_enhance: bool = False
    # Metadata del video
    duration_seconds: Optional[float] = None
    fps: Optional[float] = None
    frame_count: Optional[int] = None
    original_width: Optional[int] = None
    original_height: Optional[int] = None
    enhanced_width: Optional[int] = None
    enhanced_height: Optional[int] = None
    # Status de procesamiento
    status: VideoStatus
    error_message: Optional[str] = None
    processing_time_ms: Optional[int] = None
    gpu_used: Optional[bool] = None
    frames_processed: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    class Config:
        populate_by_name = True
        use_enum_values = True


class VideoResponse(BaseModel):
    """Respuesta con metadata de video (sin datos binarios)."""
    id: str
    original_filename: str
    description: str
    original_width: Optional[int]
    original_height: Optional[int]
    enhanced_width: Optional[int]
    enhanced_height: Optional[int]
    duration_seconds: Optional[float]
    fps: Optional[float]
    frame_count: Optional[int]
    model_type: str
    scale: int
    face_enhance: bool = False
    status: str
    error_message: Optional[str] = None
    processing_time_ms: Optional[int]
    gpu_used: Optional[bool]
    frames_processed: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class VideoDetailResponse(VideoResponse):
    """Respuesta detallada con los videos en base64."""
    original_base64: Optional[str] = None
    enhanced_base64: Optional[str] = None


class VideoListResponse(BaseModel):
    """Respuesta de lista paginada de videos."""
    total: int
    page: int
    per_page: int
    videos: list[VideoResponse]
