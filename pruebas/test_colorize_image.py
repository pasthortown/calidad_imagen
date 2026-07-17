#!/usr/bin/env python3
"""
Script de prueba para validar la colorización de imágenes con DeOldify.

Este script:
1. Lee una imagen de prueba en blanco y negro
2. Se autentica con el API
3. Envía la imagen para colorización
4. Descarga el resultado
"""

import os
import sys
import base64
import time
import requests
from pathlib import Path

# Configuración
API_URL = "http://localhost:8888"
TEST_IMAGE = "prueba_bn.png"  # Imagen en blanco y negro
OUTPUT_DIR = "output"

# Credenciales de prueba
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"
TEST_USERNAME = "testuser"


def setup_directories():
    """Crea el directorio de salida si no existe."""
    script_dir = Path(__file__).parent
    output_path = script_dir / OUTPUT_DIR
    output_path.mkdir(exist_ok=True)
    return script_dir, output_path


def read_file_base64(file_path: Path) -> str:
    """Lee un archivo y lo convierte a base64."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def save_file_from_base64(base64_string: str, output_path: Path):
    """Guarda un archivo desde base64."""
    file_data = base64.b64decode(base64_string)
    with open(output_path, "wb") as f:
        f.write(file_data)


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


def colorize_image(token: str, image_base64: str, filename: str) -> dict:
    """Envía una imagen al API para colorearla."""
    payload = {
        "image_base64": image_base64,
        "filename": filename,
    }

    response = requests.post(
        f"{API_URL}/api/colorize/images",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=120
    )

    if response.status_code != 201:
        raise Exception(f"Error: {response.status_code} - {response.text[:200]}")

    return response.json()


def get_colorize_info():
    """Obtiene información del servicio de colorización."""
    response = requests.get(
        f"{API_URL}/api/colorize/info",
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} - {response.text[:200]}")

    return response.json()


def main():
    print("=" * 60)
    print("Test de Colorización de Imagen con DeOldify")
    print("=" * 60)

    # Setup
    script_dir, output_path = setup_directories()
    test_image_path = script_dir / TEST_IMAGE

    # Verificar imagen de prueba
    if not test_image_path.exists():
        print(f"\nERROR: No se encontró la imagen de prueba: {test_image_path}")
        print("Por favor, coloca una imagen B/N llamada 'prueba_bn.png' en la carpeta 'pruebas/'")
        sys.exit(1)

    # Verificar tamaño de la imagen
    image_size = test_image_path.stat().st_size / (1024 * 1024)
    print(f"\nImagen de prueba: {test_image_path}")
    print(f"Tamaño de la imagen: {image_size:.2f} MB")
    print(f"Directorio de salida: {output_path}")

    # Obtener info del servicio
    print("\n[1/5] Verificando servicio de colorización...")
    try:
        info = get_colorize_info()
        print(f"  Modelo: {info.get('model_type', 'N/A')}")
        print(f"  Dispositivo: {info.get('device', 'N/A')}")
        print(f"  GPU disponible: {info.get('gpu_available', False)}")
        print(f"  Modelo cargado: {info.get('model_loaded', False)}")
    except Exception as e:
        print(f"  Warning: No se pudo obtener info del servicio: {e}")

    # Leer imagen
    print("\n[2/5] Leyendo imagen de prueba...")
    image_base64 = read_file_base64(test_image_path)
    print(f"  Tamaño base64: {len(image_base64):,} caracteres")

    # Registrar usuario (si no existe)
    print("\n[3/5] Verificando usuario de prueba...")
    register_user()

    # Login
    print("\n[4/5] Autenticando...")
    try:
        token = login()
        print(f"  Token obtenido: {token[:30]}...")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # Enviar imagen para colorización
    print(f"\n[5/5] Enviando imagen para colorización...")

    try:
        start_time = time.time()
        result = colorize_image(token, image_base64, TEST_IMAGE)
        elapsed = time.time() - start_time
        image_data = result["image"]

        print(f"  Imagen ID: {image_data['id']}")
        print(f"  Status: {image_data['status']}")
        print(f"  Dimensiones originales: {image_data.get('original_width', 0)}x{image_data.get('original_height', 0)}")
        print(f"  Dimensiones coloreadas: {image_data.get('colorized_width', 0)}x{image_data.get('colorized_height', 0)}")
        print(f"  Tiempo de procesamiento: {image_data.get('processing_time_ms', 0)}ms")
        print(f"  Tiempo total: {elapsed:.2f}s")
        print(f"  GPU usada: {image_data.get('gpu_used', False)}")
        print(f"  Mensaje: {result.get('message', '')}")

        # Guardar imágenes
        if image_data.get("colorized_base64"):
            image_name = test_image_path.stem
            original_ext = test_image_path.suffix
            output_original = output_path / f"{image_name}_original_bw{original_ext}"
            output_colorized = output_path / f"{image_name}_colorized{original_ext}"

            if image_data.get("original_base64"):
                save_file_from_base64(image_data["original_base64"], output_original)
                print(f"  Imagen original guardada: {output_original}")

            save_file_from_base64(image_data["colorized_base64"], output_colorized)
            print(f"  Imagen coloreada guardada: {output_colorized}")
        else:
            print("  NOTA: Imágenes disponibles en el servidor en /image_history/")

    except Exception as e:
        print(f"  ERROR enviando imagen: {e}")
        sys.exit(1)

    # Resumen
    print("\n" + "=" * 60)
    print("TEST COMPLETADO EXITOSAMENTE")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
