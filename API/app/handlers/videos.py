from pydantic import ValidationError
from app.handlers.base import AuthenticatedHandler
from app.models.video import VideoEnhanceRequest
from app.services.video_service import video_service


class VideoEnhanceHandler(AuthenticatedHandler):
    """Handler para mejorar videos."""

    async def post(self):
        """POST /api/videos/enhance - Inicia el procesamiento de un video."""
        try:
            body = self.get_json_body()
            request_data = VideoEnhanceRequest(**body)
        except ValidationError as e:
            self.write_error_json("Datos de video invalidos", 400, e.errors())
            return

        user_id = self.get_current_user_id()
        result, error = await video_service.enhance_video(user_id, request_data)

        if error:
            self.write_error_json(error, 400)
            return

        self.write_json({
            "message": "Video recibido, procesamiento iniciado. Consulte el estado con GET /api/videos/{id}",
            "video": result.model_dump()
        }, 202)


class VideoListHandler(AuthenticatedHandler):
    """Handler para listar videos."""

    async def get(self):
        """GET /api/videos - Lista los videos del usuario."""
        user_id = self.get_current_user_id()

        # Obtener parametros de paginacion
        page = int(self.get_argument("page", 1))
        per_page = int(self.get_argument("per_page", 10))
        status = self.get_argument("status", None)

        # Validar parametros
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 10

        result = await video_service.list_videos(user_id, page, per_page, status)

        self.write_json(result.model_dump())


class VideoDetailHandler(AuthenticatedHandler):
    """Handler para obtener/eliminar un video especifico."""

    async def get(self, video_id: str):
        """GET /api/videos/{id} - Obtiene un video por ID."""
        user_id = self.get_current_user_id()
        result = await video_service.get_video(video_id, user_id)

        if not result:
            self.write_error_json("Video no encontrado", 404)
            return

        self.write_json({"video": result.model_dump()})

    async def delete(self, video_id: str):
        """DELETE /api/videos/{id} - Elimina un video."""
        user_id = self.get_current_user_id()
        deleted = await video_service.delete_video(video_id, user_id)

        if not deleted:
            self.write_error_json("Video no encontrado", 404)
            return

        self.write_json({"message": "Video eliminado exitosamente"})
