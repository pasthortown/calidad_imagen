#!/usr/bin/env python3
"""
Script de prueba para validar la colorización de videos con DeOldify.

Este script:
1. Lee un video de prueba en blanco y negro
2. Se autentica con el API
3. Envía el video para colorización (procesamiento frame a frame)
4. Espera a que termine el procesamiento
5. Descarga el resultado
"""

import os
import sys
import base64
import time
import requests
from pathlib import Path

# Configuración
API_URL = "http://localhost:8888"
TEST_VIDEO = "prueba_video_bn.mp4"  # Video en blanco y negro
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


def colorize_video(token: str, video_base64: str, filename: str) -> dict:
    """Envía un video al API para colorearlo."""
    payload = {
        "video_base64": video_base64,
        "filename": filename,
    }

    response = requests.post(
        f"{API_URL}/api/colorize/videos",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=60
    )

    if response.status_code != 202:
        raise Exception(f"Error: {response.status_code} - {response.text[:200]}")

    return response.json()


def get_video_status(token: str, video_id: str) -> dict:
    """Obtiene el estado de un video coloreado."""
    response = requests.get(
        f"{API_URL}/api/colorize/videos/{video_id}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30
    )

    if response.status_code != 200:
        raise Exception(f"Error: {response.status_code} - {response.text[:200]}")

    return response.json()


def wait_for_completion(token: str, video_id: str, max_wait_seconds: int = 3600) -> dict:
    """Espera a que el video termine de procesarse."""
    start_time = time.time()
    last_frames = 0

    while True:
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            raise Exception(f"Timeout: el video no se procesó en {max_wait_seconds} segundos")

        result = get_video_status(token, video_id)
        video = result["video"]
        status = video["status"]
        frames_processed = video.get("frames_processed", 0)
        total_frames = video.get("frame_count", 0)

        # Mostrar progreso
        if frames_processed != last_frames:
            progress = (frames_processed / total_frames * 100) if total_frames > 0 else 0
            print(f"  Progreso: {frames_processed}/{total_frames} frames ({progress:.1f}%) - Status: {status}")
            last_frames = frames_processed

        if status == "completed":
            return result
        elif status == "error":
            raise Exception(f"Error en procesamiento: {video.get('error_message', 'Unknown error')}")

        time.sleep(5)  # Esperar 5 segundos antes de consultar de nuevo


def main():
    print("=" * 60)
    print("Test de Colorización de Video con DeOldify")
    print("=" * 60)

    # Setup
    script_dir, output_path = setup_directories()
    test_video_path = script_dir / TEST_VIDEO

    # Verificar video de prueba
    if not test_video_path.exists():
        print(f"\nERROR: No se encontró el video de prueba: {test_video_path}")
        print("Por favor, coloca un video B/N llamado 'prueba_video_bn.mp4' en la carpeta 'pruebas/'")
        sys.exit(1)

    # Verificar tamaño del video
    video_size = test_video_path.stat().st_size / (1024 * 1024)
    print(f"\nVideo de prueba: {test_video_path}")
    print(f"Tamaño del video: {video_size:.2f} MB")
    print(f"Directorio de salida: {output_path}")

    # Leer video
    print("\n[1/5] Leyendo video de prueba...")
    video_base64 = read_file_base64(test_video_path)
    print(f"  Tamaño base64: {len(video_base64):,} caracteres")

    # Registrar usuario (si no existe)
    print("\n[2/5] Verificando usuario de prueba...")
    register_user()

    # Login
    print("\n[3/5] Autenticando...")
    try:
        token = login()
        print(f"  Token obtenido: {token[:30]}...")
    except Exception as e:
        print(f"  ERROR: {e}")
        sys.exit(1)

    # Enviar video para colorización
    print(f"\n[4/5] Enviando video para colorización...")

    try:
        start_time = time.time()
        result = colorize_video(token, video_base64, TEST_VIDEO)
        video_data = result["video"]
        video_id = video_data["id"]

        print(f"  Video ID: {video_id}")
        print(f"  Status inicial: {video_data['status']}")
        print(f"  Duración: {video_data.get('duration_seconds', 0):.2f}s")
        print(f"  FPS: {video_data.get('fps', 0):.2f}")
        print(f"  Frames totales: {video_data.get('frame_count', 0)}")
        print(f"  Dimensiones originales: {video_data.get('original_width', 0)}x{video_data.get('original_height', 0)}")
        print(f"  Mensaje: {result.get('message', '')}")

    except Exception as e:
        print(f"  ERROR enviando video: {e}")
        sys.exit(1)

    # Esperar a que termine
    print(f"\n[5/5] Esperando procesamiento...")
    try:
        final_result = wait_for_completion(token, video_id)
        elapsed = time.time() - start_time
        video_data = final_result["video"]

        print(f"\n  Procesamiento completado!")
        print(f"  Status: {video_data['status']}")
        print(f"  Dimensiones coloreadas: {video_data.get('colorized_width', 0)}x{video_data.get('colorized_height', 0)}")
        print(f"  Frames procesados: {video_data.get('frames_processed', 0)}")
        print(f"  Tiempo de procesamiento: {video_data.get('processing_time_ms', 0)}ms")
        print(f"  Tiempo total: {elapsed:.2f}s")
        print(f"  GPU usada: {video_data.get('gpu_used', False)}")

        # Guardar videos si están disponibles en base64
        if video_data.get("colorized_base64"):
            video_name = test_video_path.stem
            original_ext = test_video_path.suffix
            output_original = output_path / f"{video_name}_original_bw{original_ext}"
            output_colorized = output_path / f"{video_name}_colorized.mkv"

            if video_data.get("original_base64"):
                save_file_from_base64(video_data["original_base64"], output_original)
                print(f"  Video original guardado: {output_original}")

            save_file_from_base64(video_data["colorized_base64"], output_colorized)
            print(f"  Video coloreado guardado: {output_colorized}")
        else:
            original_ext = test_video_path.suffix
            print("  NOTA: Videos disponibles en el servidor en /image_history/")
            print(f"    Original: {video_id}_original_bw{original_ext}")
            print(f"    Coloreado: {video_id}_colorized.mkv")

    except Exception as e:
        print(f"  ERROR durante procesamiento: {e}")
        sys.exit(1)

    # Resumen
    print("\n" + "=" * 60)
    print("TEST COMPLETADO EXITOSAMENTE")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
