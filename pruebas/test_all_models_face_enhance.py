#!/usr/bin/env python3
"""
Script de prueba para validar todos los modelos de Real-ESRGAN con Face Enhancement.

Este script:
1. Lee una imagen de prueba (prueba.png)
2. Se autentica con el API
3. Prueba cada modelo disponible CON face_enhance activado
4. Guarda los resultados en ./output/ con formato: {nombre}_face_{modelo}.png
"""

import os
import sys
import base64
import time
import requests
from pathlib import Path

# Configuración
API_URL = "http://localhost:8888"
TEST_IMAGE = "prueba.png"
OUTPUT_DIR = "output"

# Credenciales de prueba
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"
TEST_USERNAME = "testuser"

# Modelos disponibles
MODELS = [
    "general_x4",   # RealESRGAN_x4plus - Fotos reales 4x
    "general_x2",   # RealESRGAN_x2plus - Fotos reales 2x
    "anime",        # RealESRGAN_x4plus_anime_6B - Anime/ilustraciones
    "anime_video",  # realesr-animevideov3 - Video anime
    "general_v3",   # realesr-general-x4v3 - General compacto
]


def setup_directories():
    """Crea el directorio de salida si no existe."""
    script_dir = Path(__file__).parent
    output_path = script_dir / OUTPUT_DIR
    output_path.mkdir(exist_ok=True)
    return script_dir, output_path


def read_image_base64(image_path: Path) -> str:
    """Lee una imagen y la convierte a base64."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def save_image_from_base64(base64_string: str, output_path: Path):
    """Guarda una imagen desde base64."""
    image_data = base64.b64decode(base64_string)
    with open(output_path, "wb") as f:
        f.write(image_data)


def register_user():
    """Registra un usuario de prueba (ignora si ya existe)."""
    try:
        response = requests.post(
            f"{API_URL}/api/auth/register",
            json={
                "email": TEST_EMAIL,
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
            },
            timeout=30
        )
        if response.status_code == 201:
            print(f"  Usuario registrado: {TEST_EMAIL}")
        elif response.status_code == 400 and "ya existe" in response.text.lower():
            print(f"  Usuario ya existe: {TEST_EMAIL}")
        else:
            print(f"  Registro: {response.status_code} - {response.text[:100]}")
    except Exception as e:
        print(f"  Error en registro: {e}")


def login() -> str:
    """Inicia sesión y retorna el access token."""
    response = requests.post(
        f"{API_URL}/api/auth/login",
        json={
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD,
        },
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Error de login: {response.status_code} - {response.text}")

    data = response.json()
    return data["tokens"]["access_token"]


def get_available_models(token: str) -> list:
    """Obtiene la lista de modelos disponibles desde el API."""
    response = requests.get(
        f"{API_URL}/api/models",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30
    )

    if response.status_code == 200:
        data = response.json()
        return [m["id"] for m in data.get("models", [])]
    return MODELS  # Fallback a lista local


def enhance_image_with_face(token: str, image_base64: str, model_type: str, filename: str, description: str = None) -> dict:
    """Envía una imagen al API para mejorarla con face enhancement activado."""
    payload = {
        "image_base64": image_base64,
        "filename": filename,
        "model_type": model_type,
        "face_enhance": True,  # Activar mejora de rostros
    }

    # Si se proporciona descripción, agregarla
    if description:
        payload["description"] = description

    response = requests.post(
        f"{API_URL}/api/images/enhance",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=600  # 10 minutos para procesamiento
    )

    if response.status_code != 201:
        raise Exception(f"Error: {response.status_code} - {response.text[:200]}")

    return response.json()


def main():
    print("=" * 60)
    print("Test de Modelos Real-ESRGAN + Face Enhancement (GFPGAN)")
    print("=" * 60)

    # Setup
    script_dir, output_path = setup_directories()
    test_image_path = script_dir / TEST_IMAGE

    # Verificar imagen de prueba
    if not test_image_path.exists():
        print(f"\nERROR: No se encontró la imagen de prueba: {test_image_path}")
        print("Por favor, coloca una imagen llamada 'prueba.png' en la carpeta 'pruebas/'")
        sys.exit(1)

    print(f"\nImagen de prueba: {test_image_path}")
    print(f"Directorio de salida: {output_path}")
    print(f"Face Enhancement: ACTIVADO")

    # Leer imagen
    print("\n[1/4] Leyendo imagen de prueba...")
    image_base64 = read_image_base64(test_image_path)
    print(f"  Tamaño base64: {len(image_base64):,} caracteres")

    # Registrar usuario (si no existe)
    print("\n[2/4] Verificando usuario de prueba...")
    register_user()

    # Login
    print("\n[3/4] Autenticando...")
    try:
        token = login()
        print(f"  Token obtenido: {token[:30]}...")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # Obtener modelos disponibles
    print("\n[4/4] Probando cada modelo con Face Enhancement...")
    available_models = get_available_models(token)
    print(f"  Modelos disponibles: {', '.join(available_models)}")

    # Probar cada modelo
    results = []
    image_name = test_image_path.stem  # Nombre sin extensión

    print("\n" + "-" * 60)

    for i, model_type in enumerate(available_models, 1):
        print(f"\n[{i}/{len(available_models)}] Procesando con modelo: {model_type} + face_enhance")

        try:
            start_time = time.time()

            # Llamar al API con face_enhance=True
            result = enhance_image_with_face(token, image_base64, model_type, TEST_IMAGE)

            elapsed = time.time() - start_time
            image_data = result["image"]

            # Guardar resultado con formato: {nombre}_face_{modelo}.png
            output_filename = f"{image_name}_face_{model_type}.png"
            output_file = output_path / output_filename
            save_image_from_base64(image_data["enhanced_base64"], output_file)

            # Mostrar info
            print(f"  Estado: {image_data['status']}")
            print(f"  Descripción: {image_data.get('description', 'N/A')[:60]}...")
            print(f"  Original: {image_data['original_width']}x{image_data['original_height']}")
            print(f"  Mejorada: {image_data['enhanced_width']}x{image_data['enhanced_height']}")
            print(f"  Face Enhance: {image_data.get('face_enhance', 'N/A')}")
            print(f"  Tiempo API: {image_data['processing_time_ms']}ms")
            print(f"  Tiempo total: {elapsed:.2f}s")
            print(f"  GPU usada: {image_data['gpu_used']}")
            print(f"  Guardado: {output_file}")

            results.append({
                "model": model_type,
                "status": "OK",
                "time_ms": image_data['processing_time_ms'],
                "output_size": f"{image_data['enhanced_width']}x{image_data['enhanced_height']}",
                "gpu_used": image_data['gpu_used'],
                "face_enhance": image_data.get('face_enhance', False),
            })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "model": model_type,
                "status": "ERROR",
                "error": str(e),
            })

    # Resumen
    print("\n" + "=" * 60)
    print("RESUMEN DE RESULTADOS (con Face Enhancement)")
    print("=" * 60)

    successful = sum(1 for r in results if r["status"] == "OK")
    print(f"\nModelos probados: {len(results)}")
    print(f"Exitosos: {successful}")
    print(f"Fallidos: {len(results) - successful}")

    print("\nDetalle:")
    print("-" * 60)
    for r in results:
        if r["status"] == "OK":
            face_str = "SI" if r.get('face_enhance') else "NO"
            print(f"  {r['model']:15} | OK | {r['time_ms']:6}ms | {r['output_size']:12} | GPU: {r['gpu_used']} | Face: {face_str}")
        else:
            print(f"  {r['model']:15} | ERROR | {r.get('error', 'Unknown')[:40]}")

    print("\n" + "=" * 60)
    print(f"Imágenes guardadas en: {output_path}")
    print("Formato de archivo: {nombre}_face_{modelo}.png")
    print("=" * 60)

    return 0 if successful == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
