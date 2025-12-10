import motor.motor_asyncio
from app.config import config


class Database:
    client: motor.motor_asyncio.AsyncIOMotorClient = None
    db: motor.motor_asyncio.AsyncIOMotorDatabase = None


db = Database()


async def connect_to_mongodb():
    """Establece conexión con MongoDB."""
    db.client = motor.motor_asyncio.AsyncIOMotorClient(config.MONGODB_URI)
    db.db = db.client[config.MONGODB_DB_NAME]

    # Verificar conexión
    try:
        await db.client.admin.command('ping')
        print(f"Conectado a MongoDB: {config.MONGODB_DB_NAME}")
    except Exception as e:
        print(f"Error conectando a MongoDB: {e}")
        raise


async def close_mongodb_connection():
    """Cierra la conexión con MongoDB."""
    if db.client:
        db.client.close()
        print("Conexión a MongoDB cerrada")


def get_database() -> motor.motor_asyncio.AsyncIOMotorDatabase:
    """Retorna la instancia de la base de datos."""
    return db.db


def get_collection(collection_name: str):
    """Retorna una colección específica."""
    return db.db[collection_name]
