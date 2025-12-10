// Inicialización de MongoDB para Image Enhancer API
db = db.getSiblingDB('image_enhancer');

// Crear usuario de aplicación
db.createUser({
    user: 'app_user',
    pwd: 'app_password_secure',
    roles: [
        {
            role: 'readWrite',
            db: 'image_enhancer'
        }
    ]
});

// Crear colecciones
db.createCollection('users');
db.createCollection('images');
db.createCollection('refresh_tokens');

// Crear índices para usuarios
db.users.createIndex({ "email": 1 }, { unique: true });
db.users.createIndex({ "username": 1 }, { unique: true });

// Crear índices para imágenes
db.images.createIndex({ "user_id": 1 });
db.images.createIndex({ "created_at": -1 });
db.images.createIndex({ "status": 1 });

// Crear índices para refresh tokens
db.refresh_tokens.createIndex({ "user_id": 1 });
db.refresh_tokens.createIndex({ "token": 1 }, { unique: true });
db.refresh_tokens.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 });

print('Database initialized successfully!');
