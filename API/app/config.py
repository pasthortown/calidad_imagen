import os
from dotenv import load_dotenv

load_dotenv()


def build_mongodb_uri():
    """Construye la URI de MongoDB desde variables de entorno separadas."""
    if os.getenv("MONGODB_URI"):
        return os.getenv("MONGODB_URI")

    host = os.getenv("MONGO_HOST", "localhost")
    port = os.getenv("MONGO_PORT", "27017")
    user = os.getenv("MONGO_USER", "")
    password = os.getenv("MONGO_PASSWORD", "")
    db = os.getenv("MONGO_DB", "image_enhancer")

    if user and password:
        return f"mongodb://{user}:{password}@{host}:{port}/{db}?authSource=admin"
    return f"mongodb://{host}:{port}/{db}"


class Config:
    # Server
    SERVER_PORT = int(os.getenv("SERVER_PORT", 8888))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    # MongoDB
    MONGODB_URI = build_mongodb_uri()
    MONGODB_DB_NAME = os.getenv("MONGO_DB", os.getenv("MONGODB_DB_NAME", "image_enhancer"))

    # JWT
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-this-secret-key")
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
        os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 30)
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS = int(
        os.getenv("JWT_REFRESH_TOKEN_EXPIRE_DAYS", 7)
    )

    # Real-ESRGAN
    REALESRGAN_MODEL = os.getenv("REALESRGAN_MODEL", "RealESRGAN_x4plus")
    REALESRGAN_SCALE = int(os.getenv("REALESRGAN_SCALE", 4))
    REALESRGAN_TILE_SIZE = int(os.getenv("REALESRGAN_TILE_SIZE", 512))
    REALESRGAN_USE_GPU = os.getenv("REALESRGAN_USE_GPU", "True").lower() == "true"

    # Storage
    MAX_IMAGE_SIZE_MB = int(os.getenv("MAX_IMAGE_SIZE_MB", 10))
    ALLOWED_IMAGE_FORMATS = os.getenv(
        "ALLOWED_IMAGE_FORMATS", "png,jpg,jpeg,webp"
    ).split(",")


config = Config()
