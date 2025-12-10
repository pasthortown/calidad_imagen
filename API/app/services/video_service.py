import asyncio
import base64
import os
import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from bson import ObjectId
import numpy as np
from PIL import Image


class VideoProcessingError(Exception):
    """Excepción personalizada para errores en el procesamiento de video."""
    pass


# Usar ffmpeg del sistema que tiene libx264 en lugar del de Conda
FFMPEG_PATH = "/usr/bin/ffmpeg"
FFPROBE_PATH = "/usr/bin/ffprobe"

from app.database import get_collection
from app.models.video import (
    VideoStatus,
    VideoEnhanceRequest,
    VideoResponse,
    VideoDetailResponse,
    VideoListResponse,
)
from app.models.image import ModelType, MODEL_CONFIG
from app.services.image_service import image_service

# Directorio base para almacenar videos
VIDEO_STORAGE_PATH = "/image_history"


class VideoService:
    """Servicio para procesamiento de videos con Real-ESRGAN."""

    def __init__(self):
        self.videos_collection = None

    def _get_collection(self):
        if self.videos_collection is None:
            self.videos_collection = get_collection("videos")

    def _decode_base64_video(self, base64_string: str) -> Tuple[Optional[bytes], Optional[str]]:
        """Decodifica un video desde base64."""
        try:
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]
            video_data = base64.b64decode(base64_string)
            return video_data, None
        except Exception as e:
            return None, f"Error decodificando video: {str(e)}"

    def _read_file_base64(self, file_path: str) -> Optional[str]:
        """Lee un archivo desde disco y lo retorna como base64."""
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            return None

    def _get_video_info(self, video_path: str) -> dict:
        """Obtiene informacion del video usando ffprobe."""
        try:
            cmd = [
                FFPROBE_PATH, '-v', 'quiet', '-print_format', 'json',
                '-show_format', '-show_streams', video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            import json
            info = json.loads(result.stdout)

            video_stream = None
            for stream in info.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break

            if video_stream:
                # Calcular FPS
                fps_parts = video_stream.get('r_frame_rate', '30/1').split('/')
                fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0

                return {
                    'width': int(video_stream.get('width', 0)),
                    'height': int(video_stream.get('height', 0)),
                    'fps': fps,
                    'duration': float(info.get('format', {}).get('duration', 0)),
                    'frame_count': int(video_stream.get('nb_frames', 0)) or int(fps * float(info.get('format', {}).get('duration', 0)))
                }
            return {'width': 0, 'height': 0, 'fps': 30.0, 'duration': 0, 'frame_count': 0}
        except Exception as e:
            print(f"Error obteniendo info del video: {e}")
            return {'width': 0, 'height': 0, 'fps': 30.0, 'duration': 0, 'frame_count': 0}

    def _generate_description(self, filename: str, width: int, height: int,
                              model_type: str, now: datetime) -> str:
        """Genera una descripcion automatica para el video."""
        date_str = now.strftime("%d/%m/%Y %H:%M")
        return f"Tratamiento de video {filename} de dimensiones {width}x{height} con el filtro {model_type}, hoy {date_str}"

    def _extract_audio(self, video_path: str, process_dir: str) -> Tuple[str, bool]:
        """Extrae el audio del video."""
        audio_path = os.path.join(process_dir, "audio.aac")
        cmd_audio = [
            FFMPEG_PATH, '-i', video_path, '-vn', '-acodec', 'copy',
            '-y', audio_path
        ]
        subprocess.run(cmd_audio, capture_output=True)
        has_audio = os.path.exists(audio_path) and os.path.getsize(audio_path) > 0
        return audio_path, has_audio

    def _extract_frames(self, video_path: str, process_dir: str) -> Tuple[str, list]:
        """Extrae los frames del video como imágenes PNG."""
        frames_dir = os.path.join(process_dir, "frames")
        os.makedirs(frames_dir, exist_ok=True)

        cmd_frames = [
            FFMPEG_PATH, '-i', video_path,
            '-qscale:v', '2',
            os.path.join(frames_dir, "frame_%08d.png")
        ]
        subprocess.run(cmd_frames, capture_output=True, check=True)

        frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.png')])
        return frames_dir, frame_files

    def _create_video_from_frames(self, enhanced_dir: str, fps: float,
                                   audio_path: str, has_audio: bool,
                                   enhanced_video_path: str, process_dir: str):
        """Crea el video final desde los frames procesados."""
        fps_str = f"{fps:.2f}"
        enhanced_files = sorted([f for f in os.listdir(enhanced_dir) if f.endswith('.png')])
        print(f"Frames enhanced encontrados: {len(enhanced_files)}")

        if len(enhanced_files) == 0:
            raise VideoProcessingError("No se generaron frames enhanced")

        video_only_path = os.path.join(process_dir, "video_only.mkv")
        cmd_video = [
            FFMPEG_PATH, '-framerate', fps_str,
            '-i', os.path.join(enhanced_dir, "frame_%08d.png"),
            '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
            '-y', video_only_path
        ]
        print(f"Ejecutando ffmpeg: {' '.join(cmd_video)}")
        result_video = subprocess.run(cmd_video, capture_output=True, text=True)

        if result_video.returncode != 0:
            print(f"Error ffmpeg creando video: {result_video.stderr}")
            raise VideoProcessingError(f"Error creando video desde frames: {result_video.stderr[:500]}")

        if not os.path.exists(video_only_path) or os.path.getsize(video_only_path) == 0:
            raise VideoProcessingError(f"El video temporal no se creo correctamente: {video_only_path}")

        # Agregar audio si existe
        self._merge_audio_video(video_only_path, audio_path, has_audio, enhanced_video_path)

        if not os.path.exists(enhanced_video_path):
            raise VideoProcessingError(f"No se pudo crear el video final: {enhanced_video_path}")
        print(f"Video enhanced creado: {enhanced_video_path} ({os.path.getsize(enhanced_video_path)} bytes)")

    def _merge_audio_video(self, video_only_path: str, audio_path: str,
                           has_audio: bool, enhanced_video_path: str):
        """Combina el video con el audio."""
        print(f"Creando video final: {enhanced_video_path}")
        if has_audio:
            print("Agregando audio al video...")
            cmd_merge = [
                FFMPEG_PATH, '-i', video_only_path,
                '-i', audio_path,
                '-c:v', 'copy', '-c:a', 'aac',
                '-y', enhanced_video_path
            ]
            result_merge = subprocess.run(cmd_merge, capture_output=True, text=True)
            if result_merge.returncode != 0:
                print(f"Error ffmpeg merge audio: {result_merge.stderr}")
                shutil.copy2(video_only_path, enhanced_video_path)
        else:
            print("Video sin audio, copiando directamente...")
            shutil.copy2(video_only_path, enhanced_video_path)

    async def _process_frames(self, video_id: str, frames_dir: str, enhanced_dir: str,
                               frame_files: list, model_type: ModelType, scale: int,
                               face_enhance: bool) -> int:
        """Procesa todos los frames del video con Real-ESRGAN."""
        import cv2

        total_frames = len(frame_files)
        upscaler = image_service._init_upscaler(model_type, scale)
        face_enhancer = image_service._init_face_enhancer(upscale=1) if face_enhance else None

        print(f"Procesando {total_frames} frames...")
        for i, frame_file in enumerate(frame_files):
            frame_path = os.path.join(frames_dir, frame_file)
            enhanced_frame_path = os.path.join(enhanced_dir, frame_file)

            # Leer y procesar frame
            img = Image.open(frame_path).convert('RGB')
            img_array = np.array(img)
            enhanced_array = upscaler.enhance(img_array)

            # Aplicar face enhancement si esta habilitado
            if face_enhance and face_enhancer is not None:
                enhanced_bgr = cv2.cvtColor(enhanced_array, cv2.COLOR_RGB2BGR)
                _, _, restored_img = face_enhancer.enhance(
                    enhanced_bgr, has_aligned=False,
                    only_center_face=False, paste_back=True
                )
                enhanced_array = cv2.cvtColor(restored_img, cv2.COLOR_BGR2RGB)

            # Guardar frame procesado
            enhanced_img = Image.fromarray(enhanced_array)
            enhanced_img.save(enhanced_frame_path, 'PNG')

            frames_processed = i + 1

            # Actualizar progreso cada 10 frames o en el ultimo
            if frames_processed % 10 == 0 or frames_processed == total_frames:
                print(f"  Frame {frames_processed}/{total_frames}")
                await self.videos_collection.update_one(
                    {"_id": ObjectId(video_id)},
                    {"$set": {"frames_processed": frames_processed}}
                )

            # Liberar memoria
            del img, img_array, enhanced_array, enhanced_img

        return total_frames

    async def _process_video_async(self, video_id: str, _user_id: str, process_dir: str,
                                   video_path: str, model_type: ModelType, scale: int,
                                   face_enhance: bool, video_info: dict, original_ext: str):
        """Procesa el video de forma asincrona en background."""
        start_time = time.time()
        frames_processed = 0

        try:
            # Actualizar status a in_progress
            await self.videos_collection.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": {"status": VideoStatus.IN_PROGRESS.value}}
            )

            fps = video_info['fps']

            # 1. Extraer audio del video
            audio_path, has_audio = self._extract_audio(video_path, process_dir)

            # 2. Extraer frames del video
            frames_dir, frame_files = self._extract_frames(video_path, process_dir)
            total_frames = len(frame_files)

            if total_frames == 0:
                raise VideoProcessingError("No se pudieron extraer frames del video")

            # 3. Crear directorio para frames procesados
            enhanced_dir = os.path.join(process_dir, "enhanced")
            os.makedirs(enhanced_dir, exist_ok=True)

            # 4. Procesar frames
            frames_processed = await self._process_frames(
                video_id, frames_dir, enhanced_dir, frame_files,
                model_type, scale, face_enhance
            )

            # 5. Obtener dimensiones del video mejorado
            first_enhanced = Image.open(os.path.join(enhanced_dir, frame_files[0]))
            enhanced_width, enhanced_height = first_enhanced.size
            first_enhanced.close()

            # 6. Preparar rutas de video
            enhanced_video_path = os.path.join(VIDEO_STORAGE_PATH, f"{video_id}_enhanced.mkv")
            original_video_final = os.path.join(VIDEO_STORAGE_PATH, f"{video_id}_original{original_ext}")

            # Copiar video original a su ubicacion final
            shutil.copy2(video_path, original_video_final)

            # 7. Crear video desde frames
            self._create_video_from_frames(
                enhanced_dir, fps, audio_path, has_audio,
                enhanced_video_path, process_dir
            )

            # 8. Limpiar carpeta de procesamiento
            shutil.rmtree(process_dir)

            processing_time = int((time.time() - start_time) * 1000)
            completed_at = datetime.utcnow()

            # 11. Actualizar registro en DB como completado
            await self.videos_collection.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": {
                    "status": VideoStatus.COMPLETED.value,
                    "enhanced_path": enhanced_video_path,
                    "original_path": original_video_final,
                    "enhanced_width": enhanced_width,
                    "enhanced_height": enhanced_height,
                    "frames_processed": frames_processed,
                    "processing_time_ms": processing_time,
                    "gpu_used": image_service._gpu_used,
                    "completed_at": completed_at
                }}
            )

            print(f"Video {video_id} procesado exitosamente en {processing_time}ms")

        except Exception as e:
            error_msg = str(e)
            print(f"Error procesando video {video_id}: {error_msg}")

            # Limpiar carpeta de procesamiento si existe
            if os.path.exists(process_dir):
                shutil.rmtree(process_dir)

            await self.videos_collection.update_one(
                {"_id": ObjectId(video_id)},
                {"$set": {
                    "status": VideoStatus.ERROR.value,
                    "error_message": error_msg,
                    "frames_processed": frames_processed
                }}
            )

    async def enhance_video(
        self,
        user_id: str,
        request: VideoEnhanceRequest
    ) -> Tuple[Optional[VideoResponse], Optional[str]]:
        """Inicia el procesamiento de un video."""
        self._get_collection()

        # Decodificar video
        video_data, error = self._decode_base64_video(request.video_base64)
        if error:
            return None, error

        # Generar ID unico para el video
        video_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Determinar modelo y escala
        model_type = request.model_type or ModelType.GENERAL_X4
        model_cfg = MODEL_CONFIG[model_type]
        effective_scale = request.scale if request.scale is not None else model_cfg["scale"]

        # Crear carpeta de procesamiento
        process_dir = os.path.join(VIDEO_STORAGE_PATH, f"{video_id}_process")
        os.makedirs(process_dir, exist_ok=True)

        # Guardar video original temporalmente
        original_ext = os.path.splitext(request.filename)[1].lower()
        temp_video_path = os.path.join(process_dir, f"original{original_ext}")

        with open(temp_video_path, 'wb') as f:
            f.write(video_data)

        # Obtener info del video
        video_info = self._get_video_info(temp_video_path)

        # Generar descripcion
        description = request.description
        if not description or description.strip() == "":
            description = self._generate_description(
                request.filename,
                video_info['width'],
                video_info['height'],
                model_type.value,
                now
            )

        # Crear registro en DB con status pending
        video_doc = {
            "user_id": user_id,
            "original_filename": request.filename,
            "description": description,
            "original_path": temp_video_path,
            "enhanced_path": None,
            "model_type": model_type.value,
            "scale": effective_scale,
            "face_enhance": request.face_enhance or False,
            "duration_seconds": video_info['duration'],
            "fps": video_info['fps'],
            "frame_count": video_info['frame_count'],
            "original_width": video_info['width'],
            "original_height": video_info['height'],
            "enhanced_width": None,
            "enhanced_height": None,
            "status": VideoStatus.PENDING.value,
            "error_message": None,
            "processing_time_ms": None,
            "gpu_used": None,
            "frames_processed": 0,
            "created_at": now,
            "completed_at": None
        }

        result = await self.videos_collection.insert_one(video_doc)
        db_video_id = str(result.inserted_id)

        # Iniciar procesamiento en background
        asyncio.create_task(
            self._process_video_async(
                db_video_id, user_id, process_dir, temp_video_path,
                model_type, effective_scale, request.face_enhance or False, video_info,
                original_ext
            )
        )

        # Retornar respuesta inmediata
        return VideoResponse(
            id=db_video_id,
            original_filename=request.filename,
            description=description,
            original_width=video_info['width'],
            original_height=video_info['height'],
            enhanced_width=None,
            enhanced_height=None,
            duration_seconds=video_info['duration'],
            fps=video_info['fps'],
            frame_count=video_info['frame_count'],
            model_type=model_type.value,
            scale=effective_scale,
            face_enhance=request.face_enhance or False,
            status=VideoStatus.PENDING.value,
            error_message=None,
            processing_time_ms=None,
            gpu_used=None,
            frames_processed=0,
            created_at=now,
            completed_at=None
        ), None

    async def get_video(self, video_id: str, user_id: str) -> Optional[VideoDetailResponse]:
        """Obtiene un video por su ID."""
        self._get_collection()

        try:
            video_doc = await self.videos_collection.find_one({
                "_id": ObjectId(video_id),
                "user_id": user_id
            })

            if not video_doc:
                return None

            # Leer videos desde disco solo si estan completos
            original_base64 = None
            enhanced_base64 = None

            if video_doc["status"] == VideoStatus.COMPLETED.value:
                if video_doc.get("original_path"):
                    original_base64 = self._read_file_base64(video_doc["original_path"])
                if video_doc.get("enhanced_path"):
                    enhanced_base64 = self._read_file_base64(video_doc["enhanced_path"])

            return VideoDetailResponse(
                id=str(video_doc["_id"]),
                original_filename=video_doc["original_filename"],
                description=video_doc.get("description", ""),
                original_width=video_doc.get("original_width"),
                original_height=video_doc.get("original_height"),
                enhanced_width=video_doc.get("enhanced_width"),
                enhanced_height=video_doc.get("enhanced_height"),
                duration_seconds=video_doc.get("duration_seconds"),
                fps=video_doc.get("fps"),
                frame_count=video_doc.get("frame_count"),
                model_type=video_doc.get("model_type", ModelType.GENERAL_X4.value),
                scale=video_doc["scale"],
                face_enhance=video_doc.get("face_enhance", False),
                status=video_doc["status"],
                error_message=video_doc.get("error_message"),
                processing_time_ms=video_doc.get("processing_time_ms"),
                gpu_used=video_doc.get("gpu_used"),
                frames_processed=video_doc.get("frames_processed"),
                created_at=video_doc["created_at"],
                completed_at=video_doc.get("completed_at"),
                original_base64=original_base64,
                enhanced_base64=enhanced_base64
            )
        except Exception:
            return None

    async def list_videos(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 10,
        status: Optional[str] = None
    ) -> VideoListResponse:
        """Lista los videos de un usuario con paginacion."""
        self._get_collection()

        filter_query = {"user_id": user_id}
        if status:
            filter_query["status"] = status

        total = await self.videos_collection.count_documents(filter_query)

        skip = (page - 1) * per_page
        cursor = self.videos_collection.find(filter_query).sort(
            "created_at", -1
        ).skip(skip).limit(per_page)

        videos = []
        async for doc in cursor:
            videos.append(VideoResponse(
                id=str(doc["_id"]),
                original_filename=doc["original_filename"],
                description=doc.get("description", ""),
                original_width=doc.get("original_width"),
                original_height=doc.get("original_height"),
                enhanced_width=doc.get("enhanced_width"),
                enhanced_height=doc.get("enhanced_height"),
                duration_seconds=doc.get("duration_seconds"),
                fps=doc.get("fps"),
                frame_count=doc.get("frame_count"),
                model_type=doc.get("model_type", ModelType.GENERAL_X4.value),
                scale=doc["scale"],
                face_enhance=doc.get("face_enhance", False),
                status=doc["status"],
                error_message=doc.get("error_message"),
                processing_time_ms=doc.get("processing_time_ms"),
                gpu_used=doc.get("gpu_used"),
                frames_processed=doc.get("frames_processed"),
                created_at=doc["created_at"],
                completed_at=doc.get("completed_at")
            ))

        return VideoListResponse(
            total=total,
            page=page,
            per_page=per_page,
            videos=videos
        )

    async def delete_video(self, video_id: str, user_id: str) -> bool:
        """Elimina un video de la base de datos y del disco."""
        self._get_collection()

        try:
            video_doc = await self.videos_collection.find_one({
                "_id": ObjectId(video_id),
                "user_id": user_id
            })

            if not video_doc:
                return False

            # Eliminar archivos del disco
            if video_doc.get("original_path") and os.path.exists(video_doc["original_path"]):
                os.remove(video_doc["original_path"])

            if video_doc.get("enhanced_path") and os.path.exists(video_doc["enhanced_path"]):
                os.remove(video_doc["enhanced_path"])

            # Eliminar carpeta de procesamiento si existe
            process_dir = os.path.join(VIDEO_STORAGE_PATH, f"{video_id}_process")
            if os.path.exists(process_dir):
                shutil.rmtree(process_dir)

            # Eliminar registro de la base de datos
            result = await self.videos_collection.delete_one({
                "_id": ObjectId(video_id),
                "user_id": user_id
            })

            return result.deleted_count > 0
        except Exception as e:
            print(f"Error eliminando video: {e}")
            return False


video_service = VideoService()
