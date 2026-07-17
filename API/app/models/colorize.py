"""Modelos Pydantic para colorización de imágenes y videos."""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class ColorizeStatus(str, Enum):
    """Estados posibles del proceso de colorización."""
    PENDING = "pending"
    PROCESSING = "processing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ERROR = "error"


class ColorizeImageRequest(BaseModel):
    """Request para colorear una imagen en blanco y negro."""
    image_base64: str = Field(..., description="Imagen en blanco y negro codificada en base64")
    filename: Optional[str] = Field(None, description="Nombre del archivo original")
    description: Optional[str] = Field(
        None,
        description="Descripción de la imagen. Si está vacía, se genera automáticamente"
    )
    output_format: Optional[str] = Field(
        "PNG",
        description="Formato de salida (PNG o JPEG)"
    )
    face_enhance: bool = Field(
        False,
        description="Aplicar mejora de rostros con GFPGAN después de colorear"
    )


class ColorizeVideoRequest(BaseModel):
    """Request para colorear un video en blanco y negro."""
    video_base64: str = Field(..., description="Video en blanco y negro codificado en base64")
    filename: str = Field(..., description="Nombre del archivo original con extensión")
    description: Optional[str] = Field(
        None,
        description="Descripción del video. Si está vacía, se genera automáticamente"
    )
    face_enhance: bool = Field(
        False,
        description="Aplicar mejora de rostros con GFPGAN después de colorear cada frame"
    )


class ColorizeImageResponse(BaseModel):
    """Respuesta con metadata de imagen coloreada (sin datos binarios)."""
    id: str
    original_filename: str
    description: str
    original_width: int
    original_height: int
    colorized_width: int
    colorized_height: int
    face_enhance: bool = False
    status: str
    processing_time_ms: Optional[int]
    gpu_used: Optional[bool]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ColorizeImageDetailResponse(ColorizeImageResponse):
    """Respuesta detallada con las imágenes en base64."""
    original_base64: Optional[str] = None
    colorized_base64: Optional[str] = None
    error_message: Optional[str] = None


class ColorizeVideoResponse(BaseModel):
    """Respuesta con metadata de video coloreado."""
    id: str
    original_filename: str
    description: str
    original_width: Optional[int]
    original_height: Optional[int]
    colorized_width: Optional[int]
    colorized_height: Optional[int]
    face_enhance: bool = False
    duration_seconds: Optional[float]
    fps: Optional[float]
    frame_count: Optional[int]
    status: str
    error_message: Optional[str]
    processing_time_ms: Optional[int]
    gpu_used: Optional[bool]
    frames_processed: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True


class ColorizeVideoDetailResponse(ColorizeVideoResponse):
    """Respuesta detallada con los videos en base64."""
    original_base64: Optional[str] = None
    colorized_base64: Optional[str] = None


class ColorizeImageListResponse(BaseModel):
    """Respuesta de lista paginada de imágenes coloreadas."""
    total: int
    page: int
    per_page: int
    images: list[ColorizeImageResponse]


class ColorizeVideoListResponse(BaseModel):
    """Respuesta de lista paginada de videos coloreados."""
    total: int
    page: int
    per_page: int
    videos: list[ColorizeVideoResponse]


class ColorizeInfoResponse(BaseModel):
    """Información del servicio de colorización."""
    model_type: str
    render_factor: int
    device: str
    gpu_available: bool
    model_loaded: bool
