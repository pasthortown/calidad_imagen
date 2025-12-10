import json
from typing import Optional, Any
import tornado.web
from app.utils.security import decode_access_token
from app.models.user import TokenData


class BaseHandler(tornado.web.RequestHandler):
    """Handler base con utilidades comunes."""

    def set_default_headers(self):
        """Configura headers CORS."""
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.set_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.set_header("Content-Type", "application/json")

    def options(self, *args, **kwargs):
        """Maneja preflight requests de CORS."""
        self.set_status(204)
        self.finish()

    def get_json_body(self) -> dict:
        """Parsea el body como JSON."""
        try:
            return json.loads(self.request.body)
        except (json.JSONDecodeError, TypeError):
            return {}

    def write_json(self, data: Any, status: int = 200):
        """Escribe respuesta JSON."""
        self.set_status(status)
        self.write(json.dumps(data, default=str))

    def write_error_json(self, message: str, status: int = 400, errors: dict = None):
        """Escribe respuesta de error JSON."""
        response = {"error": message}
        if errors:
            response["details"] = errors
        self.write_json(response, status)


class AuthenticatedHandler(BaseHandler):
    """Handler que requiere autenticación JWT."""

    current_user_data: Optional[TokenData] = None

    def prepare(self):
        """Verifica autenticación antes de cada request."""
        if self.request.method == "OPTIONS":
            return

        auth_header = self.request.headers.get("Authorization", "")

        if not auth_header.startswith("Bearer "):
            self.set_status(401)
            self.write_json({"error": "Token de autenticación requerido"}, 401)
            self.finish()
            return

        token = auth_header.split(" ")[1]
        token_data = decode_access_token(token)

        if not token_data:
            self.set_status(401)
            self.write_json({"error": "Token inválido o expirado"}, 401)
            self.finish()
            return

        self.current_user_data = token_data

    def get_current_user_id(self) -> str:
        """Retorna el ID del usuario autenticado."""
        return self.current_user_data.user_id if self.current_user_data else None
