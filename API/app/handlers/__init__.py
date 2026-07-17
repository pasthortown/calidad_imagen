from app.handlers.auth import (
    RegisterHandler,
    LoginHandler,
    RefreshTokenHandler,
    LogoutHandler,
    MeHandler,
)
from app.handlers.images import (
    ImageEnhanceHandler,
    ImageListHandler,
    ImageDetailHandler,
)
from app.handlers.videos import (
    VideoEnhanceHandler,
    VideoListHandler,
    VideoDetailHandler,
)
from app.handlers.health import HealthHandler, InfoHandler, ModelsHandler
from app.handlers.swagger import SwaggerUIHandler, OpenAPISpecHandler
from app.handlers.colorize import (
    ColorizeInfoHandler,
    ColorizeImageHandler,
    ColorizeImageListHandler,
    ColorizeImageDetailHandler,
    ColorizeVideoHandler,
    ColorizeVideoListHandler,
    ColorizeVideoDetailHandler,
)

__all__ = [
    "RegisterHandler",
    "LoginHandler",
    "RefreshTokenHandler",
    "LogoutHandler",
    "MeHandler",
    "ImageEnhanceHandler",
    "ImageListHandler",
    "ImageDetailHandler",
    "VideoEnhanceHandler",
    "VideoListHandler",
    "VideoDetailHandler",
    "HealthHandler",
    "InfoHandler",
    "ModelsHandler",
    "SwaggerUIHandler",
    "OpenAPISpecHandler",
    "ColorizeInfoHandler",
    "ColorizeImageHandler",
    "ColorizeImageListHandler",
    "ColorizeImageDetailHandler",
    "ColorizeVideoHandler",
    "ColorizeVideoListHandler",
    "ColorizeVideoDetailHandler",
]
