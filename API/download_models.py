#!/usr/bin/env python3
"""Script para descargar los modelos preentrenados de Real-ESRGAN."""

import os
import urllib.request
import sys

# Modelos disponibles de Real-ESRGAN
# Referencia: https://github.com/xinntao/Real-ESRGAN
REALESRGAN_MODELS = {
    # Modelos generales para fotos reales
    "RealESRGAN_x4plus.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "RealESRGAN_x2plus.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth",

    # Modelo optimizado para anime/ilustraciones (más pequeño y rápido)
    "RealESRGAN_x4plus_anime_6B.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",

    # Modelo para video anime (también funciona con imágenes)
    "realesr-animevideov3.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-animevideov3.pth",

    # Modelo general v3 (más pequeño, bueno para escenas generales)
    "realesr-general-x4v3.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth",
}

# Modelo DeOldify para colorización (ONNX)
# Se descarga automáticamente desde Hugging Face cuando se usa el servicio
# Repo: facefusion/models-3.0.0
# Archivo: deoldify.onnx
DEOLDIFY_MODEL_INFO = {
    "repo_id": "facefusion/models-3.0.0",
    "filename": "deoldify.onnx",
    "description": "Modelo DeOldify ONNX para colorización de imágenes B/N"
}


def download_file(url: str, dest: str):
    """Descarga un archivo mostrando progreso."""
    print(f"Descargando {os.path.basename(dest)}...")

    def progress_hook(count, block_size, total_size):
        percent = int(count * block_size * 100 / total_size)
        sys.stdout.write(f"\r  Progreso: {percent}%")
        sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, dest, reporthook=progress_hook)
        print("\n  Completado!")
        return True
    except Exception as e:
        print(f"\n  Error: {e}")
        return False


def download_deoldify_model(weights_dir: str):
    """Descarga el modelo DeOldify desde Hugging Face."""
    try:
        from huggingface_hub import hf_hub_download

        deoldify_path = os.path.join(weights_dir, DEOLDIFY_MODEL_INFO["filename"])

        if os.path.exists(deoldify_path):
            print(f"✓ {DEOLDIFY_MODEL_INFO['filename']} ya existe, saltando...")
            return True

        print(f"Descargando {DEOLDIFY_MODEL_INFO['filename']} desde Hugging Face...")
        hf_hub_download(
            repo_id=DEOLDIFY_MODEL_INFO["repo_id"],
            filename=DEOLDIFY_MODEL_INFO["filename"],
            local_dir=weights_dir,
            local_dir_use_symlinks=False
        )
        print("  Completado!")
        return True
    except ImportError:
        print("  Warning: huggingface_hub no está instalado, no se puede descargar DeOldify")
        print("  El modelo se descargará automáticamente cuando se use el servicio")
        return False
    except Exception as e:
        print(f"  Error: {e}")
        return False


def main():
    weights_dir = os.path.join(os.path.dirname(__file__), "weights")
    os.makedirs(weights_dir, exist_ok=True)

    print("=" * 50)
    print("Descargador de modelos Real-ESRGAN y DeOldify")
    print("=" * 50)
    print(f"\nDirectorio de destino: {weights_dir}\n")

    # Descargar modelos Real-ESRGAN
    print("\n--- Modelos Real-ESRGAN ---")
    for model_name, url in REALESRGAN_MODELS.items():
        dest_path = os.path.join(weights_dir, model_name)

        if os.path.exists(dest_path):
            print(f"✓ {model_name} ya existe, saltando...")
            continue

        success = download_file(url, dest_path)
        if not success:
            print(f"✗ Error descargando {model_name}")

    # Descargar modelo DeOldify (colorización)
    print("\n--- Modelo DeOldify (Colorización) ---")
    download_deoldify_model(weights_dir)

    print("\n" + "=" * 50)
    print("Proceso completado!")
    print("=" * 50)


if __name__ == "__main__":
    main()
