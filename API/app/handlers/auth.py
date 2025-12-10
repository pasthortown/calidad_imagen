from pydantic import ValidationError
from app.handlers.base import BaseHandler, AuthenticatedHandler
from app.models.user import UserCreate, UserLogin, RefreshTokenRequest
from app.services.auth_service import auth_service


class RegisterHandler(BaseHandler):
    """Handler para registro de usuarios."""

    async def post(self):
        """POST /api/auth/register - Registra un nuevo usuario."""
        try:
            body = self.get_json_body()
            user_data = UserCreate(**body)
        except ValidationError as e:
            self.write_error_json("Datos de registro inválidos", 400, e.errors())
            return

        user, error = await auth_service.register_user(user_data)

        if error:
            self.write_error_json(error, 400)
            return

        self.write_json({
            "message": "Usuario registrado exitosamente",
            "user": user.model_dump()
        }, 201)


class LoginHandler(BaseHandler):
    """Handler para login de usuarios."""

    async def post(self):
        """POST /api/auth/login - Autentica un usuario."""
        try:
            body = self.get_json_body()
            login_data = UserLogin(**body)
        except ValidationError as e:
            self.write_error_json("Datos de login inválidos", 400, e.errors())
            return

        tokens, error = await auth_service.authenticate_user(
            login_data.email, login_data.password
        )

        if error:
            self.write_error_json(error, 401)
            return

        self.write_json({
            "message": "Login exitoso",
            "tokens": tokens.model_dump()
        })


class RefreshTokenHandler(BaseHandler):
    """Handler para refrescar tokens."""

    async def post(self):
        """POST /api/auth/refresh - Refresca los tokens."""
        try:
            body = self.get_json_body()
            refresh_data = RefreshTokenRequest(**body)
        except ValidationError as e:
            self.write_error_json("Token de refresco requerido", 400, e.errors())
            return

        tokens, error = await auth_service.refresh_tokens(refresh_data.refresh_token)

        if error:
            self.write_error_json(error, 401)
            return

        self.write_json({
            "message": "Tokens refrescados exitosamente",
            "tokens": tokens.model_dump()
        })


class LogoutHandler(AuthenticatedHandler):
    """Handler para logout de usuarios."""

    async def post(self):
        """POST /api/auth/logout - Cierra sesión del usuario."""
        user_id = self.get_current_user_id()
        body = self.get_json_body()
        refresh_token = body.get("refresh_token")

        await auth_service.logout(user_id, refresh_token)

        self.write_json({"message": "Sesión cerrada exitosamente"})


class MeHandler(AuthenticatedHandler):
    """Handler para obtener información del usuario actual."""

    async def get(self):
        """GET /api/auth/me - Obtiene información del usuario actual."""
        user_id = self.get_current_user_id()
        user = await auth_service.get_user_by_id(user_id)

        if not user:
            self.write_error_json("Usuario no encontrado", 404)
            return

        self.write_json({"user": user.model_dump()})
