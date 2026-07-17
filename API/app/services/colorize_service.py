"""
Servicio de colorización de imágenes y videos usando DeOldify ONNX.
Integra el modelo DeOldify para colorear imágenes en blanco y negro.
"""

import asyncio
import base64
import io
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import cv2
import numpy as np
from bson import ObjectId
from PIL import Image

from app.database import get_collection
from app.models.colorize import (
    ColorizeStatus,
    ColorizeImageRequest,
    ColorizeVideoRequest,
    ColorizeImageResponse,
    ColorizeImageDetailResponse,
    ColorizeVideoResponse,
    ColorizeVideoDetailResponse,
    ColorizeImageListResponse,
    ColorizeVideoListResponse,
    ColorizeInfoResponse,
)
from app.config import config

# Lazy import para evitar dependencia circular
_face_enhancer_module = None

# Intentar importar onnxruntime
try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    print("Warning: onnxruntime not available, colorization features will not work")

# Directorio base para almacenar archivos
COLORIZE_STORAGE_PATH = "/image_history"
MODELS_DIR = Path("/app/models")

# Usar ffmpeg del sistema
FFMPEG_PATH = "/usr/bin/ffmpeg"
FFPROBE_PATH = "/usr/bin/ffprobe"

# Configuración del modelo ONNX en Hugging Face
HF_REPO_ONNX = "facefusion/models-3.0.0"
ONNX_FILENAME = "deoldify.onnx"


class ColorizationError(Exception):
    """Excepción personalizada para errores en la colorización."""
    pass


class DeOldifyColorizer:
    """Colorizer basado en DeOldify ONNX para transformar imágenes B/N a color."""

    def __init__(self, render_factor: int = 16):
        """
        Inicializa el colorizer.

        Args:
            render_factor: Factor de renderizado (afecta calidad y uso de memoria)
        """
        self.render_factor = render_factor
        self._original_gray = None
        self.session = None
        self._model_loaded = False
        self.device = "cpu"
        self.providers = ['CPUExecutionProvider']

        if ONNX_AVAILABLE:
            self._init_providers()
            self._load_model()

    def _init_providers(self):
        """Inicializa los proveedores ONNX disponibles."""
        providers = ort.get_available_providers()
        if 'CUDAExecutionProvider' in providers:
            self.providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
            self.device = "cuda"
        else:
            self.providers = ['CPUExecutionProvider']
            self.device = "cpu"

        print(f"DeOldify - Dispositivo: {self.device}")
        print(f"DeOldify - Proveedores ONNX disponibles: {providers}")

    def _download_model(self) -> Optional[Path]:
        """Descarga el modelo ONNX desde Hugging Face si no existe localmente."""
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        model_path = MODELS_DIR / ONNX_FILENAME

        if not model_path.exists():
            try:
                from huggingface_hub import hf_hub_download
                print(f"Descargando modelo {ONNX_FILENAME} desde Hugging Face...")
                model_path = Path(hf_hub_download(
                    repo_id=HF_REPO_ONNX,
                    filename=ONNX_FILENAME,
                    local_dir=MODELS_DIR,
                    local_dir_use_symlinks=False
                ))
                print(f"Modelo descargado en: {model_path}")
            except Exception as e:
                print(f"Error descargando modelo DeOldify: {e}")
                return None
        else:
            print(f"DeOldify - Usando modelo existente: {model_path}")

        return model_path

    def _load_model(self):
        """Carga el modelo ONNX."""
        model_path = self._download_model()

        if model_path is None or not model_path.exists():
            print("DeOldify - Modelo no disponible")
            self._model_loaded = False
            return

        try:
            print("DeOldify - Cargando modelo ONNX...")
            sess_options = ort.SessionOptions()
            sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

            self.session = ort.InferenceSession(
                str(model_path),
                sess_options=sess_options,
                providers=self.providers
            )

            self._model_loaded = True
            print("DeOldify - Modelo ONNX cargado exitosamente!")
            print(f"DeOldify - Input: {self.session.get_inputs()[0].name}, "
                  f"shape: {self.session.get_inputs()[0].shape}")
            print(f"DeOldify - Output: {self.session.get_outputs()[0].name}, "
                  f"shape: {self.session.get_outputs()[0].shape}")

        except Exception as e:
            print(f"Error cargando modelo DeOldify: {e}")
            self._model_loaded = False
            self.session = None

    def _preprocess_image(self, image: Image.Image) -> Tuple[np.ndarray, tuple]:
        """Preprocesa la imagen para el modelo ONNX."""
        # Convertir a RGB si es necesario
        if image.mode != "RGB":
            image = image.convert("RGB")

        orig_size = image.size
        orig_w, orig_h = orig_size

        # Convertir a numpy array BGR
        img_array = np.array(image)
        img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

        # Guardar imagen original en escala de grises para LAB blending
        self._original_gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Calcular tamaño de renderizado (debe ser múltiplo de 32 para ONNX)
        render_size = self.render_factor * 32

        # Redimensionar manteniendo aspect ratio cuadrado
        img_resized = cv2.resize(img_bgr, (render_size, render_size), interpolation=cv2.INTER_AREA)

        # Convertir a escala de grises y luego a RGB (3 canales)
        img_gray = cv2.cvtColor(img_resized, cv2.COLOR_BGR2GRAY)
        img_gray_rgb = cv2.cvtColor(img_gray, cv2.COLOR_GRAY2RGB)

        # El modelo espera float32 con valores en rango 0-255
        img_float = img_gray_rgb.astype(np.float32)

        # Transponer HWC -> CHW y agregar batch dimension
        img_transposed = np.transpose(img_float, (2, 0, 1))
        img_batch = np.expand_dims(img_transposed, axis=0)

        return img_batch, orig_size

    def _postprocess_image(self, output: np.ndarray, original_size: tuple) -> Image.Image:
        """Postprocesa la salida del modelo ONNX usando LAB blending."""
        # Output shape: (1, 3, H, W) o similar
        if len(output.shape) == 4:
            output = output[0]

        # Transponer de CHW a HWC
        if output.shape[0] == 3:
            output = np.transpose(output, (1, 2, 0))

        # Clamp valores a [0, 255] y convertir a uint8
        output = np.clip(output, 0, 255).astype(np.uint8)

        # Output está en RGB, convertir a BGR para OpenCV
        colorized_bgr = cv2.cvtColor(output, cv2.COLOR_RGB2BGR)

        # Redimensionar colorizado al tamaño original
        orig_w, orig_h = original_size
        colorized_resized = cv2.resize(colorized_bgr, (orig_w, orig_h), interpolation=cv2.INTER_CUBIC)

        # Aplicar suavizado gaussiano
        colorized_smooth = cv2.GaussianBlur(colorized_resized, (13, 13), 0)

        # Técnica LAB: preservar luminosidad original, usar crominancia del modelo
        colorized_lab = cv2.cvtColor(colorized_smooth, cv2.COLOR_BGR2LAB)

        # Obtener canal L de la imagen original en escala de grises
        original_gray_resized = self._original_gray
        original_lab = cv2.cvtColor(
            cv2.cvtColor(original_gray_resized, cv2.COLOR_GRAY2BGR),
            cv2.COLOR_BGR2LAB
        )

        # Combinar: L del original, A y B del colorizado
        result_lab = colorized_lab.copy()
        result_lab[:, :, 0] = original_lab[:, :, 0]

        # Convertir de vuelta a BGR
        result_bgr = cv2.cvtColor(result_lab, cv2.COLOR_LAB2BGR)

        # Convertir a RGB para PIL
        result_rgb = cv2.cvtColor(result_bgr, cv2.COLOR_BGR2RGB)

        return Image.fromarray(result_rgb)

    def colorize(self, image: Image.Image) -> Image.Image:
        """
        Colorea una imagen en blanco y negro.

        Args:
            image: Imagen PIL en blanco y negro

        Returns:
            Imagen PIL coloreada
        """
        if not self._model_loaded or self.session is None:
            raise ColorizationError("Modelo DeOldify no está cargado")

        # Preprocesar
        input_tensor, orig_size = self._preprocess_image(image)

        # Obtener nombre del input
        input_name = self.session.get_inputs()[0].name

        # Inferencia
        outputs = self.session.run(None, {input_name: input_tensor})
        output = outputs[0]

        # Postprocesar
        return self._postprocess_image(output, orig_size)

    @property
    def is_loaded(self) -> bool:
        """Retorna si el modelo está cargado."""
        return self._model_loaded


# Singleton del colorizer
_colorizer_instance: Optional[DeOldifyColorizer] = None


def get_colorizer(render_factor: int = 16) -> DeOldifyColorizer:
    """Obtiene una instancia del colorizer (singleton)."""
    global _colorizer_instance
    if _colorizer_instance is None:
        _colorizer_instance = DeOldifyColorizer(render_factor)
    return _colorizer_instance


class ColorizeService:
    """Servicio para colorización de imágenes y videos con almacenamiento en disco."""

    def __init__(self):
        self.colorized_images_collection = None
        self.colorized_videos_collection = None
        self._colorizer: Optional[DeOldifyColorizer] = None
        self._face_enhancer = None
        self._gpu_used = False
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        """Asegura que el directorio de almacenamiento exista."""
        Path(COLORIZE_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

    def _get_collections(self):
        """Inicializa las colecciones de MongoDB."""
        if self.colorized_images_collection is None:
            self.colorized_images_collection = get_collection("colorized_images")
        if self.colorized_videos_collection is None:
            self.colorized_videos_collection = get_collection("colorized_videos")

    def _init_colorizer(self) -> DeOldifyColorizer:
        """Inicializa el colorizer."""
        if self._colorizer is None:
            self._colorizer = get_colorizer()
            self._gpu_used = self._colorizer.device == "cuda"
        return self._colorizer

    def _get_face_enhancer(self):
        """Obtiene el face enhancer de image_service (lazy import)."""
        global _face_enhancer_module
        if _face_enhancer_module is None:
            from app.services.image_service import image_service
            _face_enhancer_module = image_service
        return _face_enhancer_module

    def _apply_face_enhancement(self, image_array: np.ndarray) -> np.ndarray:
        """Aplica mejora de rostros con GFPGAN a una imagen."""
        try:
            print("Aplicando mejora de rostros con GFPGAN...")
            image_service = self._get_face_enhancer()
            # Usar el método de image_service para aplicar face enhancement
            enhanced_array = image_service._apply_face_enhancement(image_array)
            return enhanced_array
        except Exception as e:
            print(f"Error aplicando face enhancement: {e}")
            return image_array

    def _decode_base64_image(self, base64_string: str) -> Tuple[Optional[Image.Image], Optional[str]]:
        """Decodifica una imagen desde base64."""
        try:
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]

            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))
            return image, None
        except Exception as e:
            return None, f"Error decodificando imagen: {str(e)}"

    def _encode_image_base64(self, image: Image.Image, img_format: str = "PNG") -> str:
        """Codifica una imagen a base64."""
        buffer = io.BytesIO()
        if img_format.upper() == "JPG":
            img_format = "JPEG"
        image.save(buffer, format=img_format)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _read_file_base64(self, file_path: str) -> Optional[str]:
        """Lee un archivo desde disco y lo retorna como base64."""
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            return None

    def _save_image_to_disk(self, image: Image.Image, file_path: str, img_format: str = "PNG"):
        """Guarda una imagen en disco."""
        if img_format.upper() == "JPG":
            img_format = "JPEG"
        image.save(file_path, format=img_format)

    def _delete_file(self, file_path: str) -> bool:
        """Elimina un archivo del disco."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def _generate_file_path(self, file_id: str, suffix: str, extension: str) -> str:
        """Genera la ruta del archivo."""
        filename = f"{file_id}_{suffix}.{extension.lower()}"
        return os.path.join(COLORIZE_STORAGE_PATH, filename)

    def _generate_description(self, filename: str, width: int, height: int, now: datetime) -> str:
        """Genera una descripción automática."""
        date_str = now.strftime("%d/%m/%Y %H:%M")
        return f"Colorización de {filename} ({width}x{height}), {date_str}"

    def _get_image_info(self, image: Image.Image, base64_string: str) -> dict:
        """Obtiene información de una imagen."""
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        size_bytes = len(base64.b64decode(base64_string))

        return {
            "width": image.width,
            "height": image.height,
            "format": image.format or "PNG",
            "size": size_bytes
        }

    def _decode_base64_video(self, base64_string: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Decodifica un video desde base64."""
        try:
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            video_data = base64.b64decode(base64_string)
            return video_data, None
        except Exception as e:
            return None, f"Error decodificando video: {str(e)}"

    def _get_video_info(self, video_path: str) -> dict:
        """Obtiene información del video usando ffprobe."""
        try:
            import json
            cmd = [
                FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            info = json.loads(result.stdout)

            video_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break

            if video_stream:
                fps_parts = video_stream.get('r_frame_rate', '30/1').split('/')
                fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0

                return {
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': fps,
                    'duration': float(info.get('format', {}).get('duration', 0)),
                    'frame_count': int(video_stream.get('nb_frames', 0)) or int(
                        fps * float(info.get('format', {}).get('duration', 0)))
                }
            return {'width': 0, 'height': 0, 'fps': 30.0, 'duration': 0, 'frame_count': 0}
        except Exception as e:
            print(f"Error obteniendo info del video: {e}")
            return {'width': 0, 'height': 0, 'fps': 30.0, 'duration': 0, 'frame_count': 0}

    def get_info(self) -> ColorizeInfoResponse:
        """Obtiene información del servicio de colorización."""
        colorizer = self._init_colorizer()
        return ColorizeInfoResponse(
            model_type="stable",
            render_factor=colorizer.render_factor,
            device=colorizer.device,
            gpu_available=colorizer.device == "cuda",
            model_loaded=colorizer.is_loaded
        )

    async def colorize_image(
        self,
        user_id: str,
        request: ColorizeImageRequest
    ) -> Tuple[Optional[ColorizeImageDetailResponse], Optional[str]]:
        """Colorea una imagen en blanco y negro."""
        self._get_collections()

        # Decodificar imagen
        image, error = self._decode_base64_image(request.image_base64)
        if error:
            return None, error

        # Obtener info de la imagen original
        img_info = self._get_image_info(image, request.image_base64)

        # Validar tamaño
        max_size = config.MAX_IMAGE_SIZE_MB * 1024 * 1024
        if img_info["size"] > max_size:
            return None, f"Imagen excede el tamaño máximo de {config.MAX_IMAGE_SIZE_MB}MB"

        # Generar ID único
        image_id = str(uuid.uuid4())
        now = datetime.utcnow()
        original_filename = request.filename or "image.png"
        output_format = (request.output_format or "PNG").upper()
        if output_format == "JPG":
            output_format = "JPEG"
        extension = "jpg" if output_format == "JPEG" else "png"

        # Generar rutas de archivo
        original_path = self._generate_file_path(image_id, "original_bw", extension)
        colorized_path = self._generate_file_path(image_id, "colorized", extension)

        # Generar descripción
        description = request.description
        if not description or description.strip() == "":
            description = self._generate_description(
                original_filename, img_info["width"], img_info["height"], now
            )

        # Guardar imagen original en disco
        if image.mode != 'RGB':
            image_rgb = image.convert('RGB')
        else:
            image_rgb = image
        self._save_image_to_disk(image_rgb, original_path, extension.upper())

        # Determinar si se aplicará face enhancement
        face_enhance = request.face_enhance or False

        # Crear registro en DB
        image_doc = {
            "user_id": user_id,
            "original_filename": original_filename,
            "description": description,
            "original_width": img_info["width"],
            "original_height": img_info["height"],
            "original_path": original_path,
            "colorized_path": None,
            "face_enhance": face_enhance,
            "status": ColorizeStatus.PROCESSING.value,
            "created_at": now,
        }

        result = await self.colorized_images_collection.insert_one(image_doc)
        db_image_id = str(result.inserted_id)

        # Procesar imagen
        start_time = time.time()

        try:
            # Inicializar colorizer
            colorizer = self._init_colorizer()

            if not colorizer.is_loaded:
                raise ColorizationError("Modelo DeOldify no está disponible")

            # Colorear imagen
            colorized_image = colorizer.colorize(image_rgb)

            # Aplicar face enhancement si se solicitó (en cascada)
            if face_enhance:
                colorized_array = np.array(colorized_image)
                colorized_array = self._apply_face_enhancement(colorized_array)
                colorized_image = Image.fromarray(colorized_array)

            # Guardar imagen coloreada
            self._save_image_to_disk(colorized_image, colorized_path, extension.upper())

            processing_time = int((time.time() - start_time) * 1000)
            completed_at = datetime.utcnow()

            # Actualizar registro en DB
            update_data = {
                "colorized_path": colorized_path,
                "colorized_width": colorized_image.width,
                "colorized_height": colorized_image.height,
                "face_enhance": face_enhance,
                "status": ColorizeStatus.COMPLETED.value,
                "processing_time_ms": processing_time,
                "gpu_used": self._gpu_used,
                "completed_at": completed_at,
            }

            await self.colorized_images_collection.update_one(
                {"_id": ObjectId(db_image_id)},
                {"$set": update_data}
            )

            # Leer imágenes como base64 para la respuesta
            original_base64 = self._read_file_base64(original_path)
            colorized_base64 = self._read_file_base64(colorized_path)

            return ColorizeImageDetailResponse(
                id=db_image_id,
                original_filename=original_filename,
                description=description,
                original_width=img_info["width"],
                original_height=img_info["height"],
                colorized_width=colorized_image.width,
                colorized_height=colorized_image.height,
                face_enhance=face_enhance,
                status=ColorizeStatus.COMPLETED.value,
                processing_time_ms=processing_time,
                gpu_used=self._gpu_used,
                created_at=now,
                completed_at=completed_at,
                original_base64=original_base64,
                colorized_base64=colorized_base64,
                error_message=None
            ), None

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            await self.colorized_images_collection.update_one(
                {"_id": ObjectId(db_image_id)},
                {"$set": {
                    "status": ColorizeStatus.FAILED.value,
                    "error_message": error_msg,
                    "processing_time_ms": processing_time,
                    "gpu_used": self._gpu_used,
                }}
            )

            return None, f"Error coloreando imagen: {error_msg}"

    async def colorize_video(
        self,
        user_id: str,
        request: ColorizeVideoRequest
    ) -> Tuple[Optional[ColorizeVideoResponse], Optional[str]]:
        """Inicia el procesamiento de colorización de un video."""
        self._get_collections()

        # Decodificar video
        video_data, error = self._decode_base64_video(request.video_base64)
        if error:
            return None, error

        # Generar ID único
        video_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Crear carpeta de procesamiento
        process_dir = os.path.join(COLORIZE_STORAGE_PATH, f"{video_id}_colorize_process")
        os.makedirs(process_dir, exist_ok=True)

        # Guardar video original temporalmente
        original_ext = os.path.splitext(request.filename)[1].lower()
        temp_video_path = os.path.join(process_dir, f"original{original_ext}")

        with open(temp_video_path, 'wb') as f:
            f.write(video_data)

        # Obtener info del video
        video_info = self._get_video_info(temp_video_path)

        # Generar descripción
        description = request.description
        if not description or description.strip() == "":
            description = self._generate_description(
                request.filename, video_info['width'], video_info['height'], now
            )

        # Determinar si se aplicará face enhancement
        face_enhance = request.face_enhance or False

        # Crear registro en DB
        video_doc = {
            "user_id": user_id,
            "original_filename": request.filename,
            "description": description,
            "original_path": temp_video_path,
            "colorized_path": None,
            "duration_seconds": video_info['duration'],
            "fps": video_info['fps'],
            "frame_count": video_info['frame_count'],
            "original_width": video_info['width'],
            "original_height": video_info['height'],
            "colorized_width": None,
            "colorized_height": None,
            "face_enhance": face_enhance,
            "status": ColorizeStatus.PENDING.value,
            "error_message": None,
            "processing_time_ms": None,
            "gpu_used": None,
            "frames_processed": 0,
            "created_at": now,
            "completed_at": None
        }

        result = await self.colorized_videos_collection.insert_one(video_doc)
        db_video_id = str(result.inserted_id)

        # Iniciar procesamiento en background
        asyncio.create_task(
            self._process_video_colorization(
                db_video_id, user_id, process_dir, temp_video_path,
                video_info, original_ext, face_enhance
            )
        )

        return ColorizeVideoResponse(
            id=db_video_id,
            original_filename=request.filename,
            description=description,
            original_width=video_info['width'],
            original_height=video_info['height'],
            colorized_width=None,
            colorized_height=None,
            face_enhance=face_enhance,
            duration_seconds=video_info['duration'],
            fps=video_info['fps'],
            frame_count=video_info['frame_count'],
            status=ColorizeStatus.PENDING.value,
            error_message=None,
            processing_time_ms=None,
            gpu_used=None,
            frames_processed=0,
            created_at=now,
            completed_at=None
        ), None

    async def _process_video_colorization(
        self, video_id: str, _user_id: str, process_dir: str,
        video_path: str, video_info: dict, original_ext: str,
        face_enhance: bool = False
    ):
        """Procesa la colorización del video frame a frame en background."""
        start_time = time.time()
        frames_processed = 0

        try:
            # Actualizar status
            await self.colorized_videos_collection.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": {"status": ColorizeStatus.IN_PROGRESS.value}}
            )

            # Inicializar colorizer
            colorizer = self._init_colorizer()
            if not colorizer.is_loaded:
                raise ColorizationError("Modelo DeOldify no está disponible")

            fps = video_info['fps']

            # 1. Extraer audio
            audio_path = os.path.join(process_dir, "audio.aac")
            cmd_audio = [
                FFMPEG_PATH, '-i', video_path, '-vn', '-acodec', 'copy',
                '-y', audio_path
            ]
            subprocess.run(cmd_audio, capture_output=True)
            has_audio = os.path.exists(audio_path) and os.path.getsize(audio_path) > 0

            # 2. Extraer frames
            frames_dir = os.path.join(process_dir, "frames")
            os.makedirs(frames_dir, exist_ok=True)

            cmd_frames = [
                FFMPEG_PATH, '-i', video_path,
                '-qscale:v', '2',
                os.path.join(frames_dir, "frame_%08d.png")
            ]
            subprocess.run(cmd_frames, capture_output=True, check=True)

            frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
            total_frames = len(frame_files)

            if total_frames == 0:
                raise ColorizationError("No se pudieron extraer frames del video")

            # 3. Crear directorio para frames coloreados
            colorized_dir = os.path.join(process_dir, "colorized")
            os.makedirs(colorized_dir, exist_ok=True)

            # 4. Colorear cada frame
            colorized_width = None
            colorized_height = None

            face_enhance_msg = " (con mejora de rostros)" if face_enhance else ""
            print(f"Coloreando {total_frames} frames{face_enhance_msg}...")
            for i, frame_file in enumerate(frame_files):
                frame_path = os.path.join(frames_dir, frame_file)
                colorized_frame_path = os.path.join(colorized_dir, frame_file)

                # Leer frame
                img = Image.open(frame_path).convert('RGB')

                # Colorear
                colorized_img = colorizer.colorize(img)

                # Aplicar face enhancement si se solicitó (en cascada)
                if face_enhance:
                    colorized_array = np.array(colorized_img)
                    colorized_array = self._apply_face_enhancement(colorized_array)
                    colorized_img = Image.fromarray(colorized_array)

                if colorized_width is None:
                    colorized_width = colorized_img.width
                    colorized_height = colorized_img.height

                # Guardar frame coloreado
                colorized_img.save(colorized_frame_path, 'PNG')

                frames_processed = i + 1

                # Actualizar progreso cada 10 frames
                if frames_processed % 10 == 0 or frames_processed == total_frames:
                    print(f"  Frame {frames_processed}/{total_frames}")
                    await self.colorized_videos_collection.update_one(
                        {"_id": ObjectId(video_id)},
                        {"$set": {"frames_processed": frames_processed}}
                    )

                del img, colorized_img

            # 5. Crear video desde frames coloreados
            colorized_video_path = os.path.join(COLORIZE_STORAGE_PATH, f"{video_id}_colorized.mkv")
            original_video_final = os.path.join(COLORIZE_STORAGE_PATH, f"{video_id}_original_bw{original_ext}")

            # Copiar video original
            shutil.copy2(video_path, original_video_final)

            # Crear video sin audio
            video_only_path = os.path.join(process_dir, "video_only.mkv")
            fps_str = f"{fps:.2f}"
            cmd_video = [
                FFMPEG_PATH, '-framerate', fps_str,
                '-i', os.path.join(colorized_dir, "frame_%08d.png"),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-y', video_only_path
            ]
            result_video = subprocess.run(cmd_video, capture_output=True, text=True)

            if result_video.returncode != 0:
                raise ColorizationError(f"Error creando video: {result_video.stderr[:500]}")

            # 6. Agregar audio si existe
            if has_audio:
                cmd_merge = [
                    FFMPEG_PATH, '-i', video_only_path,
                    '-i', audio_path,
                    '-c:v', 'copy', '-c:a', 'aac',
                    '-y', colorized_video_path
                ]
                result_merge = subprocess.run(cmd_merge, capture_output=True, text=True)
                if result_merge.returncode != 0:
                    shutil.copy2(video_only_path, colorized_video_path)
            else:
                shutil.copy2(video_only_path, colorized_video_path)

            # 7. Limpiar carpeta de procesamiento
            shutil.rmtree(process_dir)

            processing_time = int((time.time() - start_time) * 1000)
            completed_at = datetime.utcnow()

            # 8. Actualizar registro como completado
            await self.colorized_videos_collection.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": {
                    "status": ColorizeStatus.COMPLETED.value,
                    "colorized_path": colorized_video_path,
                    "original_path": original_video_final,
                    "colorized_width": colorized_width,
                    "colorized_height": colorized_height,
                    "frames_processed": frames_processed,
                    "processing_time_ms": processing_time,
                    "gpu_used": self._gpu_used,
                    "completed_at": completed_at
                }}
            )

            print(f"Video {video_id} coloreado exitosamente en {processing_time}ms")

        except Exception as e:
            error_msg = str(e)
            print(f"Error coloreando video {video_id}: {error_msg}")

            if os.path.exists(process_dir):
                shutil.rmtree(process_dir)

            await self.colorized_videos_collection.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": {
                    "status": ColorizeStatus.ERROR.value,
                    "error_message": error_msg,
                    "frames_processed": frames_processed
                }}
            )

    async def get_colorized_image(self, image_id: str, user_id: str) -> Optional[ColorizeImageDetailResponse]:
        """Obtiene una imagen coloreada por su ID."""
        self._get_collections()

        try:
            image_doc = await self.colorized_images_collection.find_one({
                "_id": ObjectId(image_id),
                "user_id": user_id
            })

            if not image_doc:
                return None

            # Leer imágenes desde disco
            original_base64 = None
            colorized_base64 = None

            if image_doc.get("original_path"):
                original_base64 = self._read_file_base64(image_doc["original_path"])

            if image_doc.get("colorized_path"):
                colorized_base64 = self._read_file_base64(image_doc["colorized_path"])

            return ColorizeImageDetailResponse(
                id=str(image_doc["_id"]),
                original_filename=image_doc["original_filename"],
                description=image_doc.get("description", ""),
                original_width=image_doc["original_width"],
                original_height=image_doc["original_height"],
                colorized_width=image_doc.get("colorized_width", image_doc["original_width"]),
                colorized_height=image_doc.get("colorized_height", image_doc["original_height"]),
                face_enhance=image_doc.get("face_enhance", False),
                status=image_doc["status"],
                processing_time_ms=image_doc.get("processing_time_ms"),
                gpu_used=image_doc.get("gpu_used"),
                created_at=image_doc["created_at"],
                completed_at=image_doc.get("completed_at"),
                original_base64=original_base64,
                colorized_base64=colorized_base64,
                error_message=image_doc.get("error_message")
            )
        except Exception:
            return None

    async def get_colorized_video(self, video_id: str, user_id: str) -> Optional[ColorizeVideoDetailResponse]:
        """Obtiene un video coloreado por su ID."""
        self._get_collections()

        try:
            video_doc = await self.colorized_videos_collection.find_one({
                "_id": ObjectId(video_id),
                "user_id": user_id
            })

            if not video_doc:
                return None

            # Leer videos desde disco solo si están completos
            original_base64 = None
            colorized_base64 = None

            if video_doc["status"] == ColorizeStatus.COMPLETED.value:
                if video_doc.get("original_path"):
                    original_base64 = self._read_file_base64(video_doc["original_path"])
                if video_doc.get("colorized_path"):
                    colorized_base64 = self._read_file_base64(video_doc["colorized_path"])

            return ColorizeVideoDetailResponse(
                id=str(video_doc["_id"]),
                original_filename=video_doc["original_filename"],
                description=video_doc.get("description", ""),
                original_width=video_doc.get("original_width"),
                original_height=video_doc.get("original_height"),
                colorized_width=video_doc.get("colorized_width"),
                colorized_height=video_doc.get("colorized_height"),
                face_enhance=video_doc.get("face_enhance", False),
                duration_seconds=video_doc.get("duration_seconds"),
                fps=video_doc.get("fps"),
                frame_count=video_doc.get("frame_count"),
                status=video_doc["status"],
                error_message=video_doc.get("error_message"),
                processing_time_ms=video_doc.get("processing_time_ms"),
                gpu_used=video_doc.get("gpu_used"),
                frames_processed=video_doc.get("frames_processed"),
                created_at=video_doc["created_at"],
                completed_at=video_doc.get("completed_at"),
                original_base64=original_base64,
                colorized_base64=colorized_base64
            )
        except Exception:
            return None

    async def list_colorized_images(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 10,
        status: Optional[str] = None
    ) -> ColorizeImageListResponse:
        """Lista las imágenes coloreadas de un usuario."""
        self._get_collections()

        filter_query = {"user_id": user_id}
        if status:
            filter_query["status"] = status

        total = await self.colorized_images_collection.count_documents(filter_query)

        skip = (page - 1) * per_page
        cursor = self.colorized_images_collection.find(filter_query).sort(
            "created_at", -1
        ).skip(skip).limit(per_page)

        images = []
        async for doc in cursor:
            images.append(ColorizeImageResponse(
                id=str(doc["_id"]),
                original_filename=doc["original_filename"],
                description=doc.get("description", ""),
                original_width=doc["original_width"],
                original_height=doc["original_height"],
                colorized_width=doc.get("colorized_width", doc["original_width"]),
                colorized_height=doc.get("colorized_height", doc["original_height"]),
                face_enhance=doc.get("face_enhance", False),
                status=doc["status"],
                processing_time_ms=doc.get("processing_time_ms"),
                gpu_used=doc.get("gpu_used"),
                created_at=doc["created_at"],
                completed_at=doc.get("completed_at")
            ))

        return ColorizeImageListResponse(
            total=total,
            page=page,
            per_page=per_page,
            images=images
        )

    async def list_colorized_videos(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 10,
        status: Optional[str] = None
    ) -> ColorizeVideoListResponse:
        """Lista los videos coloreados de un usuario."""
        self._get_collections()

        filter_query = {"user_id": user_id}
        if status:
            filter_query["status"] = status

        total = await self.colorized_videos_collection.count_documents(filter_query)

        skip = (page - 1) * per_page
        cursor = self.colorized_videos_collection.find(filter_query).sort(
            "created_at", -1
        ).skip(skip).limit(per_page)

        videos = []
        async for doc in cursor:
            videos.append(ColorizeVideoResponse(
                id=str(doc["_id"]),
                original_filename=doc["original_filename"],
                description=doc.get("description", ""),
                original_width=doc.get("original_width"),
                original_height=doc.get("original_height"),
                colorized_width=doc.get("colorized_width"),
                colorized_height=doc.get("colorized_height"),
                face_enhance=doc.get("face_enhance", False),
                duration_seconds=doc.get("duration_seconds"),
                fps=doc.get("fps"),
                frame_count=doc.get("frame_count"),
                status=doc["status"],
                error_message=doc.get("error_message"),
                processing_time_ms=doc.get("processing_time_ms"),
                gpu_used=doc.get("gpu_used"),
                frames_processed=doc.get("frames_processed"),
                created_at=doc["created_at"],
                completed_at=doc.get("completed_at")
            ))

        return ColorizeVideoListResponse(
            total=total,
            page=page,
            per_page=per_page,
            videos=videos
        )

    async def delete_colorized_image(self, image_id: str, user_id: str) -> bool:
        """Elimina una imagen coloreada."""
        self._get_collections()

        try:
            image_doc = await self.colorized_images_collection.find_one({
                "_id": ObjectId(image_id),
                "user_id": user_id
            })

            if not image_doc:
                return False

            # Eliminar archivos
            if image_doc.get("original_path"):
                self._delete_file(image_doc["original_path"])
            if image_doc.get("colorized_path"):
                self._delete_file(image_doc["colorized_path"])

            # Eliminar registro
            result = await self.colorized_images_collection.delete_one({
                "_id": ObjectId(image_id),
                "user_id": user_id
            })

            return result.deleted_count > 0
        except Exception as e:
            print(f"Error eliminando imagen coloreada: {e}")
            return False

    async def delete_colorized_video(self, video_id: str, user_id: str) -> bool:
        """Elimina un video coloreado."""
        self._get_collections()

        try:
            video_doc = await self.colorized_videos_collection.find_one({
                "_id": ObjectId(video_id),
                "user_id": user_id
            })

            if not video_doc:
                return False

            # Eliminar archivos
            if video_doc.get("original_path") and os.path.exists(video_doc["original_path"]):
                os.remove(video_doc["original_path"])
            if video_doc.get("colorized_path") and os.path.exists(video_doc["colorized_path"]):
                os.remove(video_doc["colorized_path"])

            # Eliminar carpeta de procesamiento si existe
            process_dir = os.path.join(COLORIZE_STORAGE_PATH, f"{video_id}_colorize_process")
            if os.path.exists(process_dir):
                shutil.rmtree(process_dir)

            # Eliminar registro
            result = await self.colorized_videos_collection.delete_one({
                "_id": ObjectId(video_id),
                "user_id": user_id
            })

            return result.deleted_count > 0
        except Exception as e:
            print(f"Error eliminando video coloreado: {e}")
            return False


# Instancia singleton del servicio
colorize_service = ColorizeService()
