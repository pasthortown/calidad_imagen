import asyncio
import signal
import tornado.web
import tornado.ioloop

from app.config import config
from app.database import connect_to_mongodb, close_mongodb_connection
from app.handlers import (
    RegisterHandler,
    LoginHandler,
    RefreshTokenHandler,
    LogoutHandler,
    MeHandler,
    ImageEnhanceHandler,
    ImageListHandler,
    ImageDetailHandler,
    VideoEnhanceHandler,
    VideoListHandler,
    VideoDetailHandler,
    HealthHandler,
    InfoHandler,
    ModelsHandler,
    SwaggerUIHandler,
    OpenAPISpecHandler,
)


def make_app() -> tornado.web.Application:
    """Crea y configura la aplicación Tornado."""
    routes = [
        # Auth endpoints
        (r"/api/auth/register", RegisterHandler),
        (r"/api/auth/login", LoginHandler),
        (r"/api/auth/refresh", RefreshTokenHandler),
        (r"/api/auth/logout", LogoutHandler),
        (r"/api/auth/me", MeHandler),

        # Image endpoints
        (r"/api/images/enhance", ImageEnhanceHandler),
        (r"/api/images", ImageListHandler),
        (r"/api/images/([a-f0-9]{24})", ImageDetailHandler),

        # Video endpoints
        (r"/api/videos/enhance", VideoEnhanceHandler),
        (r"/api/videos", VideoListHandler),
        (r"/api/videos/([a-f0-9]{24})", VideoDetailHandler),

        # System endpoints
        (r"/api/health", HealthHandler),
        (r"/api/info", InfoHandler),
        (r"/api/models", ModelsHandler),

        # Documentation endpoints
        (r"/api/docs", SwaggerUIHandler),
        (r"/api/docs/openapi.json", OpenAPISpecHandler),
    ]

    return tornado.web.Application(
        routes,
        debug=config.DEBUG,
    )


async def main():
    """Función principal que inicia el servidor."""
    print("=" * 50)
    print("Image Enhancer API")
    print("=" * 50)

    # Conectar a MongoDB
    print("\nConectando a MongoDB...")
    await connect_to_mongodb()

    # Crear aplicación
    app = make_app()
    app.listen(config.SERVER_PORT)

    print(f"\nServidor iniciado en http://localhost:{config.SERVER_PORT}")
    print(f"Modo debug: {config.DEBUG}")
    print(f"GPU disponible: {config.REALESRGAN_USE_GPU}")
    print("\nEndpoints disponibles:")
    print("  Auth:")
    print("    - POST /api/auth/register")
    print("    - POST /api/auth/login")
    print("    - POST /api/auth/refresh")
    print("    - POST /api/auth/logout")
    print("    - GET  /api/auth/me")
    print("  Images:")
    print("    - POST /api/images/enhance")
    print("    - GET  /api/images")
    print("    - GET  /api/images/{id}")
    print("    - DELETE /api/images/{id}")
    print("  Videos:")
    print("    - POST /api/videos/enhance")
    print("    - GET  /api/videos")
    print("    - GET  /api/videos/{id}")
    print("    - DELETE /api/videos/{id}")
    print("  System:")
    print("    - GET  /api/health")
    print("    - GET  /api/info")
    print("    - GET  /api/models")
    print("  Documentation:")
    print("    - GET  /api/docs          (Swagger UI)")
    print("    - GET  /api/docs/openapi.json")
    print("\n" + "=" * 50)

    # Configurar manejo de señales para cierre graceful
    shutdown_event = asyncio.Event()

    def signal_handler(sig, frame):
        print("\nRecibida señal de cierre...")
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Mantener el servidor corriendo
    await shutdown_event.wait()

    # Cerrar conexión a MongoDB
    await close_mongodb_connection()
    print("Servidor detenido.")


if __name__ == "__main__":
    asyncio.run(main())
