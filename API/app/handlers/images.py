from pydantic import ValidationError
from app.handlers.base import AuthenticatedHandler
from app.models.image import ImageEnhanceRequest
from app.services.image_service import image_service


class ImageEnhanceHandler(AuthenticatedHandler):
    """Handler para mejorar imágenes."""

    async def post(self):
        """POST /api/images/enhance - Mejora una imagen."""
        try:
            body = self.get_json_body()
            request_data = ImageEnhanceRequest(**body)
        except ValidationError as e:
            self.write_error_json("Datos de imagen inválidos", 400, e.errors())
            return

        user_id = self.get_current_user_id()
        result, error = await image_service.enhance_image(user_id, request_data)

        if error:
            self.write_error_json(error, 400)
            return

        self.write_json({
            "message": "Imagen procesada exitosamente",
            "image": result.model_dump()
        }, 201)


class ImageListHandler(AuthenticatedHandler):
    """Handler para listar imágenes."""

    async def get(self):
        """GET /api/images - Lista las imágenes del usuario."""
        user_id = self.get_current_user_id()

        # Obtener parámetros de paginación
        page = int(self.get_argument("page", 1))
        per_page = int(self.get_argument("per_page", 10))
        status = self.get_argument("status", None)

        # Validar parámetros
        if page < 1:
            page = 1
        if per_page < 1 or per_page > 100:
            per_page = 10

        result = await image_service.list_images(user_id, page, per_page, status)

        self.write_json(result.model_dump())


class ImageDetailHandler(AuthenticatedHandler):
    """Handler para obtener/eliminar una imagen específica."""

    async def get(self, image_id: str):
        """GET /api/images/{id} - Obtiene una imagen por ID."""
        user_id = self.get_current_user_id()
        result = await image_service.get_image(image_id, user_id)

        if not result:
            self.write_error_json("Imagen no encontrada", 404)
            return

        self.write_json({"image": result.model_dump()})

    async def delete(self, image_id: str):
        """DELETE /api/images/{id} - Elimina una imagen."""
        user_id = self.get_current_user_id()
        deleted = await image_service.delete_image(image_id, user_id)

        if not deleted:
            self.write_error_json("Imagen no encontrada", 404)
            return

        self.write_json({"message": "Imagen eliminada exitosamente"})
