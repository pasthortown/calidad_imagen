from datetime import datetime
from typing import Optional, Tuple
from bson import ObjectId
from app.database import get_collection
from app.models.user import UserCreate, UserInDB, UserResponse, TokenPair
from app.utils.security import (
    hash_password,
    verify_password,
    create_token_pair,
)


class AuthService:
    def __init__(self):
        self.users_collection = None
        self.tokens_collection = None

    def _get_collections(self):
        if self.users_collection is None:
            self.users_collection = get_collection("users")
            self.tokens_collection = get_collection("refresh_tokens")

    async def register_user(self, user_data: UserCreate) -> Tuple[Optional[UserResponse], Optional[str]]:
        """Registra un nuevo usuario."""
        self._get_collections()

        # Verificar si el email ya existe
        existing_email = await self.users_collection.find_one({"email": user_data.email})
        if existing_email:
            return None, "El email ya está registrado"

        # Verificar si el username ya existe
        existing_username = await self.users_collection.find_one({"username": user_data.username})
        if existing_username:
            return None, "El nombre de usuario ya está en uso"

        # Crear usuario
        user_dict = {
            "username": user_data.username,
            "email": user_data.email,
            "hashed_password": hash_password(user_data.password),
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }

        result = await self.users_collection.insert_one(user_dict)

        return UserResponse(
            id=str(result.inserted_id),
            username=user_data.username,
            email=user_data.email,
            is_active=True,
            created_at=user_dict["created_at"]
        ), None

    async def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[Optional[TokenPair], Optional[str]]:
        """Autentica un usuario y retorna tokens."""
        self._get_collections()

        # Buscar usuario
        user = await self.users_collection.find_one({"email": email})
        if not user:
            return None, "Credenciales inválidas"

        # Verificar contraseña
        if not verify_password(password, user["hashed_password"]):
            return None, "Credenciales inválidas"

        # Verificar si el usuario está activo
        if not user.get("is_active", True):
            return None, "Usuario desactivado"

        # Crear tokens
        user_id = str(user["_id"])
        access_token, refresh_token, expires_at = create_token_pair(user_id, email)

        # Guardar refresh token en DB
        await self.tokens_collection.insert_one({
            "user_id": user_id,
            "token": refresh_token,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
        })

        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token
        ), None

    async def refresh_tokens(self, refresh_token: str) -> Tuple[Optional[TokenPair], Optional[str]]:
        """Refresca los tokens usando el refresh token."""
        self._get_collections()

        # Buscar refresh token
        token_doc = await self.tokens_collection.find_one({"token": refresh_token})
        if not token_doc:
            return None, "Token de refresco inválido"

        # Verificar expiración
        if token_doc["expires_at"] < datetime.utcnow():
            await self.tokens_collection.delete_one({"_id": token_doc["_id"]})
            return None, "Token de refresco expirado"

        # Buscar usuario
        user = await self.users_collection.find_one(
            {"_id": ObjectId(token_doc["user_id"])}
        )
        if not user:
            return None, "Usuario no encontrado"

        if not user.get("is_active", True):
            return None, "Usuario desactivado"

        # Eliminar token anterior
        await self.tokens_collection.delete_one({"_id": token_doc["_id"]})

        # Crear nuevos tokens
        user_id = str(user["_id"])
        access_token, new_refresh_token, expires_at = create_token_pair(
            user_id, user["email"]
        )

        # Guardar nuevo refresh token
        await self.tokens_collection.insert_one({
            "user_id": user_id,
            "token": new_refresh_token,
            "expires_at": expires_at,
            "created_at": datetime.utcnow(),
        })

        return TokenPair(
            access_token=access_token,
            refresh_token=new_refresh_token
        ), None

    async def logout(self, user_id: str, refresh_token: Optional[str] = None):
        """Cierra sesión eliminando tokens."""
        self._get_collections()

        if refresh_token:
            # Eliminar token específico
            await self.tokens_collection.delete_one({
                "user_id": user_id,
                "token": refresh_token
            })
        else:
            # Eliminar todos los tokens del usuario
            await self.tokens_collection.delete_many({"user_id": user_id})

    async def get_user_by_id(self, user_id: str) -> Optional[UserResponse]:
        """Obtiene un usuario por su ID."""
        self._get_collections()

        try:
            user = await self.users_collection.find_one({"_id": ObjectId(user_id)})
            if not user:
                return None

            return UserResponse(
                id=str(user["_id"]),
                username=user["username"],
                email=user["email"],
                is_active=user.get("is_active", True),
                created_at=user["created_at"]
            )
        except Exception:
            return None


auth_service = AuthService()
