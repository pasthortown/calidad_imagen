"""Handlers para colorización de imágenes y videos."""

import json
from app.handlers.base import BaseHandler, AuthenticatedHandler
from app.services.colorize_service import colorize_service
from app.models.colorize import ColorizeImageRequest, ColorizeVideoRequest


class ColorizeInfoHandler(BaseHandler):
    """Handler para información del servicio de colorización."""

    async def get(self):
        """GET /api/colorize/info - Información del modelo de colorización."""
        try:
            info = colorize_service.get_info()
            self.write_json(info.model_dump())
        except Exception as e:
            self.set_status(500)
            self.write_json({"error": f"Error obteniendo información: {str(e)}"})


class ColorizeImageHandler(AuthenticatedHandler):
    """Handler para colorear imágenes."""

    async def post(self):
        """POST /api/colorize/images - Colorear una imagen en blanco y negro."""
        try:
            data = json.loads(self.request.body)
            request = ColorizeImageRequest(**data)

            result, error = await colorize_service.colorize_image(
                user_id=self.get_current_user_id(),
                request=request
            )

            if error:
                self.write_json({"error": error}, status=400)
                return

            self.write_json({
                "message": "Imagen coloreada exitosamente",
                "image": result.model_dump(mode='json')
            }, status=201)

        except json.JSONDecodeError:
            self.write_json({"error": "JSON inválido"}, status=400)
        except Exception as e:
            self.write_json({"error": f"Error procesando imagen: {str(e)}"}, status=500)


class ColorizeImageListHandler(AuthenticatedHandler):
    """Handler para listar imágenes coloreadas."""

    async def get(self):
        """GET /api/colorize/images - Listar imágenes coloreadas del usuario."""
        try:
            page = int(self.get_argument("page", "1"))
            per_page = int(self.get_argument("per_page", "10"))
            status = self.get_argument("status", None)

            result = await colorize_service.list_colorized_images(
                user_id=self.get_current_user_id(),
                page=page,
                per_page=per_page,
                status=status
            )

            self.write_json(result.model_dump(mode='json'))

        except Exception as e:
            self.write_json({"error": f"Error listando imágenes: {str(e)}"}, status=500)


class ColorizeImageDetailHandler(AuthenticatedHandler):
    """Handler para detalle de imagen coloreada."""

    async def get(self, image_id: str):
        """GET /api/colorize/images/{id} - Obtener imagen coloreada por ID."""
        try:
            result = await colorize_service.get_colorized_image(
                image_id=image_id,
                user_id=self.get_current_user_id()
            )

            if not result:
                self.write_json({"error": "Imagen no encontrada"}, status=404)
                return

            self.write_json({"image": result.model_dump(mode='json')})

        except Exception as e:
            self.write_json({"error": f"Error obteniendo imagen: {str(e)}"}, status=500)

    async def delete(self, image_id: str):
        """DELETE /api/colorize/images/{id} - Eliminar imagen coloreada."""
        try:
            deleted = await colorize_service.delete_colorized_image(
                image_id=image_id,
                user_id=self.get_current_user_id()
            )

            if not deleted:
                self.write_json({"error": "Imagen no encontrada"}, status=404)
                return

            self.write_json({"message": "Imagen eliminada exitosamente"})

        except Exception as e:
            self.write_json({"error": f"Error eliminando imagen: {str(e)}"}, status=500)


class ColorizeVideoHandler(AuthenticatedHandler):
    """Handler para colorear videos."""

    async def post(self):
        """POST /api/colorize/videos - Colorear un video en blanco y negro."""
        try:
            data = json.loads(self.request.body)
            request = ColorizeVideoRequest(**data)

            result, error = await colorize_service.colorize_video(
                user_id=self.get_current_user_id(),
                request=request
            )

            if error:
                self.write_json({"error": error}, status=400)
                return

            self.write_json({
                "message": "Video enviado para colorización",
                "video": result.model_dump(mode='json')
            }, status=202)

        except json.JSONDecodeError:
            self.write_json({"error": "JSON inválido"}, status=400)
        except Exception as e:
            self.write_json({"error": f"Error procesando video: {str(e)}"}, status=500)


class ColorizeVideoListHandler(AuthenticatedHandler):
    """Handler para listar videos coloreados."""

    async def get(self):
        """GET /api/colorize/videos - Listar videos coloreados del usuario."""
        try:
            page = int(self.get_argument("page", "1"))
            per_page = int(self.get_argument("per_page", "10"))
            status = self.get_argument("status", None)

            result = await colorize_service.list_colorized_videos(
                user_id=self.get_current_user_id(),
                page=page,
                per_page=per_page,
                status=status
            )

            self.write_json(result.model_dump(mode='json'))

        except Exception as e:
            self.write_json({"error": f"Error listando videos: {str(e)}"}, status=500)


class ColorizeVideoDetailHandler(AuthenticatedHandler):
    """Handler para detalle de video coloreado."""

    async def get(self, video_id: str):
        """GET /api/colorize/videos/{id} - Obtener video coloreado por ID."""
        try:
            result = await colorize_service.get_colorized_video(
                video_id=video_id,
                user_id=self.get_current_user_id()
            )

            if not result:
                self.write_json({"error": "Video no encontrado"}, status=404)
                return

            self.write_json({"video": result.model_dump(mode='json')})

        except Exception as e:
            self.write_json({"error": f"Error obteniendo video: {str(e)}"}, status=500)

    async def delete(self, video_id: str):
        """DELETE /api/colorize/videos/{id} - Eliminar video coloreado."""
        try:
            deleted = await colorize_service.delete_colorized_video(
                video_id=video_id,
                user_id=self.get_current_user_id()
            )

            if not deleted:
                self.write_json({"error": "Video no encontrado"}, status=404)
                return

            self.write_json({"message": "Video eliminado exitosamente"})

        except Exception as e:
            self.write_json({"error": f"Error eliminando video: {str(e)}"}, status=500)
