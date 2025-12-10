#!/usr/bin/env python3
"""
Script de prueba para validar el procesamiento de videos con Real-ESRGAN.

Este script:
1. Lee un video de prueba (prueba_video.mp4)
2. Se autentica con el API
3. Envia el video para procesamiento
4. Espera a que termine el procesamiento
5. Descarga el resultado
"""

import os
import sys
import base64
import time
import requests
from pathlib import Path

# Configuracion
API_URL = "http://localhost:8888"
TEST_VIDEO = "prueba_video.mp4"
OUTPUT_DIR = "output"

# Credenciales de prueba
TEST_EMAIL = "test@example.com"
TEST_PASSWORD = "password123"
TEST_USERNAME = "testuser"

# Modelo a usar para el test
TEST_MODEL = "anime_video"  # Usar anime_video para videos anime
TEST_SCALE = 4  # Escala default del modelo


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
    """Inicia sesion y retorna el access token."""
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


def enhance_video(token: str, video_base64: str, filename: str, model_type: str, scale: int, face_enhance: bool = False) -> dict:
    """Envia un video al API para mejorarlo."""
    payload = {
        "video_base64": video_base64,
        "filename": filename,
        "model_type": model_type,
        "scale": scale,
        "face_enhance": face_enhance,
    }

    response = requests.post(
        f"{API_URL}/api/videos/enhance",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
        timeout=60
    )

    if response.status_code != 202:
        raise Exception(f"Error: {response.status_code} - {response.text[:200]}")

    return response.json()


def get_video_status(token: str, video_id: str) -> dict:
    """Obtiene el estado de un video."""
    response = requests.get(
        f"{API_URL}/api/videos/{video_id}",
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
            raise Exception(f"Timeout: el video no se proceso en {max_wait_seconds} segundos")

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
    print("Test de Procesamiento de Video con Real-ESRGAN")
    print("=" * 60)

    # Setup
    script_dir, output_path = setup_directories()
    test_video_path = script_dir / TEST_VIDEO

    # Verificar video de prueba
    if not test_video_path.exists():
        print(f"\nERROR: No se encontro el video de prueba: {test_video_path}")
        print("Por favor, coloca un video llamado 'prueba_video.mp4' en la carpeta 'pruebas/'")
        sys.exit(1)

    # Verificar tamano del video
    video_size = test_video_path.stat().st_size / (1024 * 1024)
    print(f"\nVideo de prueba: {test_video_path}")
    print(f"Tamano del video: {video_size:.2f} MB")
    print(f"Directorio de salida: {output_path}")

    # Leer video
    print("\n[1/5] Leyendo video de prueba...")
    video_base64 = read_file_base64(test_video_path)
    print(f"  Tamano base64: {len(video_base64):,} caracteres")

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

    # Enviar video para procesamiento
    print(f"\n[4/5] Enviando video para procesamiento...")
    print(f"  Modelo: {TEST_MODEL}")
    print(f"  Escala: {TEST_SCALE}x")

    try:
        start_time = time.time()
        result = enhance_video(token, video_base64, TEST_VIDEO, TEST_MODEL, TEST_SCALE)
        video_data = result["video"]
        video_id = video_data["id"]

        print(f"  Video ID: {video_id}")
        print(f"  Status inicial: {video_data['status']}")
        print(f"  Duracion: {video_data.get('duration_seconds', 0):.2f}s")
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
        print(f"  Dimensiones mejoradas: {video_data.get('enhanced_width', 0)}x{video_data.get('enhanced_height', 0)}")
        print(f"  Frames procesados: {video_data.get('frames_processed', 0)}")
        print(f"  Tiempo de procesamiento: {video_data.get('processing_time_ms', 0)}ms")
        print(f"  Tiempo total: {elapsed:.2f}s")
        print(f"  GPU usada: {video_data.get('gpu_used', False)}")

        # Guardar videos si estan disponibles en base64
        if video_data.get("enhanced_base64"):
            video_name = test_video_path.stem
            original_ext = test_video_path.suffix  # Conservar extension original (.mp4, .avi, etc.)
            output_original = output_path / f"{video_name}_original{original_ext}"
            output_enhanced = output_path / f"{video_name}_{TEST_MODEL}_enhanced.mkv"

            if video_data.get("original_base64"):
                save_file_from_base64(video_data["original_base64"], output_original)
                print(f"  Video original guardado: {output_original}")

            save_file_from_base64(video_data["enhanced_base64"], output_enhanced)
            print(f"  Video mejorado guardado: {output_enhanced}")
        else:
            original_ext = test_video_path.suffix
            print("  NOTA: Videos disponibles en el servidor en /image_history/")
            print(f"    Original: {video_id}_original{original_ext}")
            print(f"    Mejorado: {video_id}_enhanced.mkv")

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
