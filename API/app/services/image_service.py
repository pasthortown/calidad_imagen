import base64
import io
import os
import time
import uuid
import cv2
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Dict, List
from PIL import Image
from bson import ObjectId
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
from scipy.ndimage import gaussian_filter

from app.database import get_collection
from app.models.image import (
    ImageStatus,
    ImageEnhanceRequest,
    ImageResponse,
    ImageDetailResponse,
    ImageListResponse,
    ModelType,
    MODEL_CONFIG,
)
from app.config import config

# Directorio base para almacenar imágenes
IMAGE_STORAGE_PATH = "/image_history"
WEIGHTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'weights')


class ResidualDenseBlock(nn.Module):
    """Bloque denso residual para RRDB."""

    def __init__(self, num_feat=64, num_grow_ch=32):
        super().__init__()
        self.conv1 = nn.Conv2d(num_feat, num_grow_ch, 3, 1, 1)
        self.conv2 = nn.Conv2d(num_feat + num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv3 = nn.Conv2d(num_feat + 2 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv4 = nn.Conv2d(num_feat + 3 * num_grow_ch, num_grow_ch, 3, 1, 1)
        self.conv5 = nn.Conv2d(num_feat + 4 * num_grow_ch, num_feat, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        x1 = self.lrelu(self.conv1(x))
        x2 = self.lrelu(self.conv2(torch.cat((x, x1), 1)))
        x3 = self.lrelu(self.conv3(torch.cat((x, x1, x2), 1)))
        x4 = self.lrelu(self.conv4(torch.cat((x, x1, x2, x3), 1)))
        x5 = self.conv5(torch.cat((x, x1, x2, x3, x4), 1))
        return x5 * 0.2 + x


class RRDB(nn.Module):
    """Residual in Residual Dense Block."""

    def __init__(self, num_feat, num_grow_ch=32):
        super().__init__()
        self.rdb1 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb2 = ResidualDenseBlock(num_feat, num_grow_ch)
        self.rdb3 = ResidualDenseBlock(num_feat, num_grow_ch)

    def forward(self, x):
        out = self.rdb1(x)
        out = self.rdb2(out)
        out = self.rdb3(out)
        return out * 0.2 + x


class RRDBNet(nn.Module):
    """Arquitectura RRDBNet para Real-ESRGAN (modelos x2plus, x4plus, anime_6B)."""

    def __init__(self, num_in_ch=3, num_out_ch=3, scale=4, num_feat=64, num_block=23, num_grow_ch=32):
        super().__init__()
        self.scale = scale

        self.conv_first = nn.Conv2d(num_in_ch, num_feat, 3, 1, 1)
        self.body = nn.Sequential(*[RRDB(num_feat, num_grow_ch) for _ in range(num_block)])
        self.conv_body = nn.Conv2d(num_feat, num_feat, 3, 1, 1)

        # Upsampling - ajustado para soportar escala 2 y 4
        self.conv_up1 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_up2 = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_hr = nn.Conv2d(num_feat, num_feat, 3, 1, 1)
        self.conv_last = nn.Conv2d(num_feat, num_out_ch, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(negative_slope=0.2, inplace=True)

    def forward(self, x):
        feat = self.conv_first(x)
        body_feat = self.conv_body(self.body(feat))
        feat = feat + body_feat

        # Upsample - para escala 4 hacemos 2x2, para escala 2 solo 1x2
        feat = self.lrelu(self.conv_up1(F.interpolate(feat, scale_factor=2, mode='nearest')))
        if self.scale == 4:
            feat = self.lrelu(self.conv_up2(F.interpolate(feat, scale_factor=2, mode='nearest')))
        out = self.conv_last(self.lrelu(self.conv_hr(feat)))
        return out


class SRVGGNetCompact(nn.Module):
    """Arquitectura VGG-style compacta para modelos v3 (animevideov3, general-x4v3).

    Esta arquitectura es más rápida y ligera que RRDBNet.
    """

    def __init__(self, num_in_ch=3, num_out_ch=3, num_feat=64, num_conv=16, upscale=4, act_type='prelu'):
        super().__init__()
        self.num_in_ch = num_in_ch
        self.num_out_ch = num_out_ch
        self.num_feat = num_feat
        self.num_conv = num_conv
        self.upscale = upscale
        self.act_type = act_type

        self.body = nn.ModuleList()
        # Primera capa
        self.body.append(nn.Conv2d(num_in_ch, num_feat, 3, 1, 1))
        # Capa de activación
        if act_type == 'relu':
            self.body.append(nn.ReLU(inplace=True))
        elif act_type == 'prelu':
            self.body.append(nn.PReLU(num_parameters=num_feat))
        elif act_type == 'leakyrelu':
            self.body.append(nn.LeakyReLU(negative_slope=0.1, inplace=True))

        # Capas intermedias
        for _ in range(num_conv):
            self.body.append(nn.Conv2d(num_feat, num_feat, 3, 1, 1))
            if act_type == 'relu':
                self.body.append(nn.ReLU(inplace=True))
            elif act_type == 'prelu':
                self.body.append(nn.PReLU(num_parameters=num_feat))
            elif act_type == 'leakyrelu':
                self.body.append(nn.LeakyReLU(negative_slope=0.1, inplace=True))

        # Capa de upsampling con PixelShuffle
        self.body.append(nn.Conv2d(num_feat, num_out_ch * (upscale ** 2), 3, 1, 1))
        self.body.append(nn.PixelShuffle(upscale))

    def forward(self, x):
        out = x
        for layer in self.body:
            out = layer(out)
        # Agregar la entrada interpolada para residual learning
        base = F.interpolate(x, scale_factor=self.upscale, mode='nearest')
        out = out + base
        return out


class RealESRGANUpscaler:
    """Upscaler usando Real-ESRGAN con procesamiento por tiles.

    Soporta múltiples arquitecturas:
    - RRDBNet: para modelos x2plus, x4plus, anime_6B
    - SRVGGNetCompact: para modelos v3 (animevideov3, general-x4v3)
    """

    def __init__(self, model_type: ModelType = ModelType.GENERAL_X4, scale: Optional[int] = None,
                 tile_size: int = 512, device=None, use_gpu: bool = True):
        self.model_type = model_type
        self.model_config = MODEL_CONFIG[model_type]
        # Usar escala proporcionada o la default del modelo
        self.scale = scale if scale is not None else self.model_config["scale"]
        self.tile_size = tile_size
        self.tile_pad = 10
        self.use_gpu = use_gpu

        # Determinar dispositivo
        if device is None:
            if use_gpu and torch.cuda.is_available():
                self.device = torch.device('cuda')
                self.gpu_available = True
            else:
                self.device = torch.device('cpu')
                self.gpu_available = False
        else:
            self.device = device
            self.gpu_available = device.type == 'cuda'

        self.model = None
        self._model_loaded = False

    def _create_model(self) -> nn.Module:
        """Crea el modelo según el tipo seleccionado."""
        cfg = self.model_config

        # Los modelos v3 usan arquitectura SRVGGNetCompact
        if self.model_type in [ModelType.ANIME_VIDEO, ModelType.GENERAL_V3]:
            return SRVGGNetCompact(
                num_in_ch=3,
                num_out_ch=3,
                num_feat=cfg["num_feat"],
                num_conv=cfg["num_conv"],
                upscale=self.scale,
                act_type='prelu'
            )
        else:
            # Modelos RRDBNet (x2plus, x4plus, anime_6B)
            return RRDBNet(
                num_in_ch=3,
                num_out_ch=3,
                scale=self.scale,
                num_feat=cfg["num_feat"],
                num_block=cfg["num_block"],
                num_grow_ch=cfg["num_grow_ch"]
            )

    def load_model(self, model_path: Optional[str] = None):
        """Carga el modelo. Si no hay modelo, usa modo simulación."""
        try:
            self.model = self._create_model()

            if model_path and os.path.exists(model_path):
                state_dict = torch.load(model_path, map_location=self.device, weights_only=True)
                if 'params_ema' in state_dict:
                    state_dict = state_dict['params_ema']
                elif 'params' in state_dict:
                    state_dict = state_dict['params']
                self.model.load_state_dict(state_dict, strict=True)
                self._model_loaded = True
                print(f"Modelo {self.model_type.value} cargado desde {model_path}")
            else:
                self._model_loaded = False
                print(f"Modo simulación: modelo {self.model_type.value} no encontrado, usando upscaling básico")

            self.model.eval()
            self.model = self.model.to(self.device)

        except Exception as e:
            print(f"Error cargando modelo {self.model_type.value}: {e}")
            self._model_loaded = False
            self.model = None

    def _tile_process(self, img: torch.Tensor) -> torch.Tensor:
        """Procesa la imagen por tiles para manejar imágenes grandes."""
        batch, channel, height, width = img.shape
        output_height = height * self.scale
        output_width = width * self.scale

        output = img.new_zeros((batch, channel, output_height, output_width))
        tiles_x = (width + self.tile_size - 1) // self.tile_size
        tiles_y = (height + self.tile_size - 1) // self.tile_size

        for y in range(tiles_y):
            for x in range(tiles_x):
                x_start = x * self.tile_size
                y_start = y * self.tile_size
                x_end = min(x_start + self.tile_size, width)
                y_end = min(y_start + self.tile_size, height)

                x_start_pad = max(x_start - self.tile_pad, 0)
                y_start_pad = max(y_start - self.tile_pad, 0)
                x_end_pad = min(x_end + self.tile_pad, width)
                y_end_pad = min(y_end + self.tile_pad, height)

                tile = img[:, :, y_start_pad:y_end_pad, x_start_pad:x_end_pad]

                with torch.no_grad():
                    tile_output = self.model(tile)

                out_x_start = x_start * self.scale
                out_y_start = y_start * self.scale
                out_x_end = x_end * self.scale
                out_y_end = y_end * self.scale

                pad_left = (x_start - x_start_pad) * self.scale
                pad_top = (y_start - y_start_pad) * self.scale

                output[:, :, out_y_start:out_y_end, out_x_start:out_x_end] = \
                    tile_output[:, :, pad_top:pad_top + (out_y_end - out_y_start),
                                pad_left:pad_left + (out_x_end - out_x_start)]

        return output

    def enhance(self, img: np.ndarray) -> np.ndarray:
        """Mejora una imagen."""
        img_tensor = torch.from_numpy(img.transpose(2, 0, 1)).float().unsqueeze(0) / 255.0
        img_tensor = img_tensor.to(self.device)

        if self._model_loaded and self.model is not None:
            with torch.no_grad():
                if img_tensor.shape[2] > self.tile_size or img_tensor.shape[3] > self.tile_size:
                    output = self._tile_process(img_tensor)
                else:
                    output = self.model(img_tensor)
        else:
            output = F.interpolate(img_tensor, scale_factor=self.scale, mode='bicubic', align_corners=False)

        output = output.squeeze(0).cpu().clamp(0, 1).numpy()
        output = (output.transpose(1, 2, 0) * 255).astype(np.uint8)

        return output


# =============================================================================
# GFPGAN - Face Enhancement
# =============================================================================

class StyleConv(nn.Module):
    """Convolución con modulación de estilo para GFPGAN."""

    def __init__(self, in_channels, out_channels, kernel_size, num_style_feat,
                 demodulate=True, sample_mode=None):
        super().__init__()
        self.demodulate = demodulate
        self.sample_mode = sample_mode
        self.weight = nn.Parameter(
            torch.randn(1, out_channels, in_channels, kernel_size, kernel_size))
        self.bias = nn.Parameter(torch.zeros(1, out_channels, 1, 1))
        self.modulation = nn.Linear(num_style_feat, in_channels, bias=True)
        self.weight.data.normal_(0, 1)
        self.modulation.bias.data.fill_(1)

    def forward(self, x, style):
        b, c, h, w = x.shape
        style = self.modulation(style).view(b, 1, c, 1, 1)
        weight = self.weight * style

        if self.demodulate:
            demod = torch.rsqrt(weight.pow(2).sum([2, 3, 4]) + 1e-8)
            weight = weight * demod.view(b, -1, 1, 1, 1)

        weight = weight.view(b * weight.shape[1], *weight.shape[2:])

        if self.sample_mode == 'upsample':
            x = F.interpolate(x, scale_factor=2, mode='bilinear', align_corners=False)
        elif self.sample_mode == 'downsample':
            x = F.interpolate(x, scale_factor=0.5, mode='bilinear', align_corners=False)

        b, c, h, w = x.shape
        x = x.view(1, b * c, h, w)
        out = F.conv2d(x, weight, padding=self.weight.shape[-1] // 2, groups=b)
        out = out.view(b, -1, *out.shape[2:]) + self.bias
        return out


class ResBlock(nn.Module):
    """Bloque residual simple."""

    def __init__(self, in_channels, out_channels=None):
        super().__init__()
        out_channels = out_channels or in_channels
        self.conv1 = nn.Conv2d(in_channels, in_channels, 3, 1, 1)
        self.conv2 = nn.Conv2d(in_channels, out_channels, 3, 1, 1)
        self.skip = nn.Conv2d(in_channels, out_channels, 1, bias=False) if in_channels != out_channels else nn.Identity()
        self.lrelu = nn.LeakyReLU(0.2, True)

    def forward(self, x):
        out = self.lrelu(self.conv1(x))
        out = self.conv2(out)
        return self.skip(x) + out


class GFPGANBilinear(nn.Module):
    """Versión simplificada de GFPGAN para face enhancement.

    Esta implementación es una versión simplificada que se enfoca
    en la restauración de rostros mediante un encoder-decoder con skip connections.
    """

    def __init__(self, out_size=512, num_style_feat=512, channel_multiplier=1,
                 narrow=1, input_is_latent=False):
        super().__init__()
        self.input_is_latent = input_is_latent
        self.num_style_feat = num_style_feat

        channels = {
            '4': int(512 * narrow),
            '8': int(512 * narrow),
            '16': int(512 * narrow),
            '32': int(512 * narrow),
            '64': int(256 * channel_multiplier * narrow),
            '128': int(128 * channel_multiplier * narrow),
            '256': int(64 * channel_multiplier * narrow),
            '512': int(32 * channel_multiplier * narrow),
            '1024': int(16 * channel_multiplier * narrow)
        }

        self.log_size = int(np.log2(out_size))

        # Encoder - más simple
        self.conv_body_first = nn.Conv2d(3, channels[f'{out_size}'], 1)

        in_channels = channels[f'{out_size}']
        self.conv_body_down = nn.ModuleList()
        for i in range(self.log_size, 2, -1):
            out_channels = channels[f'{2**(i-1)}']
            self.conv_body_down.append(ResBlock(in_channels, out_channels))
            in_channels = out_channels

        self.final_conv = nn.Conv2d(in_channels, channels['4'], 3, 1, 1)

        # Decoder simple - upsampling con convolución
        self.conv_body_up = nn.ModuleList()
        in_channels = channels['4']
        for i in range(3, self.log_size + 1):
            out_channels = channels[f'{2**i}']
            self.conv_body_up.append(nn.Sequential(
                nn.Upsample(scale_factor=2, mode='bilinear', align_corners=False),
                nn.Conv2d(in_channels, out_channels, 3, 1, 1),
                nn.LeakyReLU(0.2, True),
                nn.Conv2d(out_channels, out_channels, 3, 1, 1),
                nn.LeakyReLU(0.2, True),
            ))
            in_channels = out_channels

        self.final_linear = nn.Conv2d(in_channels, 3, 3, 1, 1)
        self.lrelu = nn.LeakyReLU(0.2, True)

    def forward(self, x, return_rgb=True):
        feat = self.lrelu(self.conv_body_first(x))

        # Encode
        for conv in self.conv_body_down:
            feat = conv(feat)
            feat = F.interpolate(feat, scale_factor=0.5, mode='bilinear', align_corners=False)

        feat = self.lrelu(self.final_conv(feat))

        # Decode
        for up_conv in self.conv_body_up:
            feat = up_conv(feat)

        out = self.final_linear(feat)
        return out, None


class FaceRestoreHelper:
    """Ayudante para detectar, alinear y restaurar rostros.

    Implementación simplificada que usa detección de rostros con OpenCV
    y aplica GFPGAN a cada rostro detectado.
    """

    def __init__(self, upscale_factor, face_size=512, crop_ratio=(1, 1),
                 det_model='retinaface_resnet50', device=None):
        self.upscale_factor = upscale_factor
        self.face_size = face_size
        self.crop_ratio = crop_ratio
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')

        # Parámetros para el crop del rostro
        self.center_face_size = int(face_size * 0.7)

        # Cargar detector de rostros de OpenCV (Haar Cascade)
        self.face_cascade = None
        self._load_face_detector()

        # Lista para almacenar rostros detectados
        self.all_landmarks_5 = []
        self.det_faces = []
        self.affine_matrices = []
        self.inverse_affine_matrices = []
        self.cropped_faces = []
        self.restored_faces = []
        self.pad_input_imgs = []

    def _load_face_detector(self):
        """Carga el detector de rostros."""
        try:
            # Usar clasificador Haar de OpenCV
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self.face_cascade = cv2.CascadeClassifier(cascade_path)
        except Exception as e:
            print(f"Error cargando detector de rostros: {e}")
            self.face_cascade = None

    def clean_all(self):
        """Limpia todas las listas."""
        self.all_landmarks_5 = []
        self.det_faces = []
        self.affine_matrices = []
        self.inverse_affine_matrices = []
        self.cropped_faces = []
        self.restored_faces = []
        self.pad_input_imgs = []

    def read_image(self, img):
        """Lee una imagen (numpy array BGR)."""
        self.input_img = img
        if img is not None:
            self.pad_input_imgs.append(img)

    def get_face_landmarks_5(self, **_kwargs):
        """Detecta rostros y obtiene landmarks aproximados."""
        if self.face_cascade is None or self.input_img is None:
            return 0

        img = self.input_img
        h, w = img.shape[:2]

        # Convertir a escala de grises para detección
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detectar rostros
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        for (x, y, fw, fh) in faces:
            # Crear bounding box
            bbox = [x, y, x + fw, y + fh]
            self.det_faces.append(bbox)

            # Crear landmarks aproximados basados en proporciones típicas del rostro
            # 5 puntos: ojo izquierdo, ojo derecho, nariz, esquina izq boca, esquina der boca
            cx, cy = x + fw // 2, y + fh // 2
            eye_y = y + int(fh * 0.35)
            eye_dist = int(fw * 0.25)
            nose_y = y + int(fh * 0.55)
            mouth_y = y + int(fh * 0.75)
            mouth_dist = int(fw * 0.2)

            landmarks = np.array([
                [cx - eye_dist, eye_y],  # Ojo izquierdo
                [cx + eye_dist, eye_y],  # Ojo derecho
                [cx, nose_y],             # Nariz
                [cx - mouth_dist, mouth_y],  # Boca izquierda
                [cx + mouth_dist, mouth_y]   # Boca derecha
            ], dtype=np.float32)

            self.all_landmarks_5.append(landmarks)

        return len(self.det_faces)

    def align_warp_face(self, border_mode='constant'):
        """Alinea y recorta cada rostro detectado."""
        for idx, landmark in enumerate(self.all_landmarks_5):
            # Calcular transformación afín para alinear el rostro
            # Puntos de referencia estándar para un rostro de face_size x face_size
            std_landmarks = np.array([
                [0.31556875 * self.face_size, 0.4615741 * self.face_size],
                [0.6826229 * self.face_size, 0.4615741 * self.face_size],
                [0.5002625 * self.face_size, 0.6405054 * self.face_size],
                [0.3467342 * self.face_size, 0.8246919 * self.face_size],
                [0.6534658 * self.face_size, 0.8246919 * self.face_size]
            ], dtype=np.float32)

            # Calcular matriz de transformación afín
            affine_matrix = cv2.estimateAffinePartial2D(landmark, std_landmarks)[0]

            if affine_matrix is None:
                # Fallback: usar transformación simple basada en bounding box
                bbox = self.det_faces[idx]
                x, y, x2, y2 = bbox
                fw, fh = x2 - x, y2 - y
                # Escalar y centrar
                scale_x = self.face_size / fw
                scale_y = self.face_size / fh
                affine_matrix = np.array([
                    [scale_x, 0, -x * scale_x],
                    [0, scale_y, -y * scale_y]
                ], dtype=np.float32)

            self.affine_matrices.append(affine_matrix)

            # Calcular matriz inversa
            inverse_affine = cv2.invertAffineTransform(affine_matrix)
            self.inverse_affine_matrices.append(inverse_affine)

            # Aplicar transformación para obtener el rostro recortado
            border_value = 0 if border_mode == 'constant' else None
            cropped_face = cv2.warpAffine(
                self.input_img, affine_matrix, (self.face_size, self.face_size),
                borderMode=cv2.BORDER_CONSTANT if border_mode == 'constant' else cv2.BORDER_REFLECT_101,
                borderValue=(border_value, border_value, border_value) if border_value is not None else None
            )
            self.cropped_faces.append(cropped_face)

    def add_restored_face(self, restored_face):
        """Añade un rostro restaurado a la lista."""
        self.restored_faces.append(restored_face)

    def get_inverse_affine(self):
        """Obtiene las matrices de transformación inversa."""
        return self.inverse_affine_matrices

    def paste_faces_to_input_image(self, upsample_img=None):
        """Pega los rostros restaurados en la imagen original."""
        if upsample_img is None:
            upsample_img = self.input_img.copy()

        h, w = upsample_img.shape[:2]

        for idx, (restored_face, inverse_affine) in enumerate(
                zip(self.restored_faces, self.inverse_affine_matrices)):

            # Escalar la matriz inversa al factor de upscale
            inv_soft = inverse_affine.copy()
            inv_soft[:, 2] *= self.upscale_factor

            # Crear máscara suave para blending
            mask = np.ones((self.face_size, self.face_size), dtype=np.float32)
            # Aplicar gradiente en los bordes
            border = int(self.face_size * 0.1)
            mask[:border, :] *= np.linspace(0, 1, border).reshape(-1, 1)
            mask[-border:, :] *= np.linspace(1, 0, border).reshape(-1, 1)
            mask[:, :border] *= np.linspace(0, 1, border).reshape(1, -1)
            mask[:, -border:] *= np.linspace(1, 0, border).reshape(1, -1)
            mask = gaussian_filter(mask, sigma=3)
            mask = np.stack([mask] * 3, axis=-1)

            # Aplicar transformación inversa al rostro restaurado
            inv_restored = cv2.warpAffine(
                restored_face, inv_soft, (w, h),
                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
            )
            inv_mask = cv2.warpAffine(
                mask, inv_soft, (w, h),
                borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0)
            )

            # Blending
            upsample_img = upsample_img.astype(np.float32)
            upsample_img = inv_mask * inv_restored + (1 - inv_mask) * upsample_img
            upsample_img = np.clip(upsample_img, 0, 255).astype(np.uint8)

        return upsample_img


class GFPGANer:
    """Clase principal para face enhancement usando GFPGAN."""

    def __init__(self, model_path, upscale=2, arch='clean', channel_multiplier=2,
                 device=None):
        self.upscale = upscale
        self.device = device or torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self._model_loaded = False

        # Inicializar modelo GFPGAN simplificado
        self.gfpgan = GFPGANBilinear(
            out_size=512,
            num_style_feat=512,
            channel_multiplier=channel_multiplier,
            narrow=1
        )

        # Cargar pesos si el archivo existe
        if model_path and os.path.exists(model_path):
            self._load_model_weights(model_path)

        self.gfpgan.eval()
        self.gfpgan = self.gfpgan.to(self.device)

        # Face helper
        self.face_helper = FaceRestoreHelper(
            upscale_factor=upscale,
            face_size=512,
            device=self.device
        )

    def _load_model_weights(self, model_path: str):
        """Carga los pesos del modelo GFPGAN desde el archivo."""
        try:
            loadnet = torch.load(model_path, map_location=self.device, weights_only=False)
            keyname = self._get_state_dict_key(loadnet)

            if keyname:
                self._apply_compatible_weights(loadnet[keyname])
        except Exception as e:
            print(f"Error cargando GFPGAN: {e}")
            self._model_loaded = False

    def _get_state_dict_key(self, loadnet: dict) -> Optional[str]:
        """Determina la clave correcta para el state_dict."""
        if 'params_ema' in loadnet:
            return 'params_ema'
        if 'params' in loadnet:
            return 'params'
        return None

    def _apply_compatible_weights(self, state_dict: dict):
        """Aplica los pesos compatibles al modelo."""
        model_dict = self.gfpgan.state_dict()
        compatible_dict = {
            k: v for k, v in state_dict.items()
            if k in model_dict and model_dict[k].shape == v.shape
        }

        if compatible_dict:
            model_dict.update(compatible_dict)
            self.gfpgan.load_state_dict(model_dict, strict=False)
            self._model_loaded = True
            print(f"GFPGAN: cargadas {len(compatible_dict)}/{len(model_dict)} claves del modelo")
        else:
            print("GFPGAN: modelo complejo detectado, usando modo simplificado")
            self._model_loaded = False

    @torch.no_grad()
    def enhance(self, img, has_aligned=False, only_center_face=False, paste_back=True):
        """Mejora los rostros en una imagen.

        Args:
            img: Imagen BGR (numpy array)
            has_aligned: Si la imagen ya está alineada (un solo rostro)
            only_center_face: Solo procesar el rostro central
            paste_back: Pegar los rostros restaurados en la imagen original

        Returns:
            cropped_faces: Lista de rostros recortados
            restored_faces: Lista de rostros restaurados
            restored_img: Imagen con rostros restaurados (si paste_back=True)
        """
        self.face_helper.clean_all()
        self.face_helper.read_image(img)

        # Detectar y alinear rostros
        num_faces = self.face_helper.get_face_landmarks_5()

        if num_faces == 0:
            # No se detectaron rostros, retornar imagen original escalada
            h, w = img.shape[:2]
            if self.upscale != 1:
                img = cv2.resize(img, (w * self.upscale, h * self.upscale),
                               interpolation=cv2.INTER_LANCZOS4)
            return [], [], img

        # Alinear rostros
        self.face_helper.align_warp_face()

        # Procesar cada rostro
        for cropped_face in self.face_helper.cropped_faces:
            # Preparar input para el modelo
            cropped_face_t = torch.from_numpy(
                cropped_face.transpose(2, 0, 1)).float().unsqueeze(0) / 255.0
            cropped_face_t = cropped_face_t.to(self.device)

            # Normalizar a [-1, 1]
            cropped_face_t = (cropped_face_t - 0.5) / 0.5

            # Aplicar modelo
            if self._model_loaded:
                try:
                    output, _ = self.gfpgan(cropped_face_t, return_rgb=True)
                except Exception as e:
                    print(f"Error en GFPGAN forward: {e}")
                    output = cropped_face_t
            else:
                # Modo fallback: aplicar sharpening y ajuste de contraste
                output = cropped_face_t
                # Aplicar un poco de sharpening usando convolución
                kernel = torch.tensor([
                    [0, -0.5, 0],
                    [-0.5, 3, -0.5],
                    [0, -0.5, 0]
                ], device=self.device).float().view(1, 1, 3, 3).repeat(3, 1, 1, 1)
                sharpened = F.conv2d(output, kernel, padding=1, groups=3)
                output = 0.7 * output + 0.3 * sharpened

            # Desnormalizar
            output = output * 0.5 + 0.5
            output = output.squeeze(0).clamp(0, 1).cpu().numpy()
            output = (output.transpose(1, 2, 0) * 255).astype(np.uint8)

            self.face_helper.add_restored_face(output)

        # Pegar rostros en la imagen
        if paste_back:
            # Escalar imagen de fondo
            h, w = img.shape[:2]
            if self.upscale != 1:
                bg_img = cv2.resize(img, (w * self.upscale, h * self.upscale),
                                   interpolation=cv2.INTER_LANCZOS4)
            else:
                bg_img = img.copy()

            restored_img = self.face_helper.paste_faces_to_input_image(bg_img)
            return self.face_helper.cropped_faces, self.face_helper.restored_faces, restored_img
        else:
            return self.face_helper.cropped_faces, self.face_helper.restored_faces, None


class ImageService:
    """Servicio para procesamiento de imágenes con almacenamiento en disco."""

    def __init__(self):
        self.images_collection = None
        self._upscalers: Dict[str, RealESRGANUpscaler] = {}
        self._face_enhancer: Optional[GFPGANer] = None
        self._gpu_used = False
        self._ensure_storage_dir()

    def _ensure_storage_dir(self):
        """Asegura que el directorio de almacenamiento exista."""
        Path(IMAGE_STORAGE_PATH).mkdir(parents=True, exist_ok=True)

    def _get_collection(self):
        if self.images_collection is None:
            self.images_collection = get_collection("images")

    def _get_upscaler_key(self, model_type: ModelType, scale: int) -> str:
        """Genera una clave única para el upscaler."""
        return f"{model_type.value}_{scale}"

    def _init_upscaler(self, model_type: ModelType = ModelType.GENERAL_X4, scale: Optional[int] = None):
        """Inicializa el upscaler para el modelo y escala especificados."""
        model_cfg = MODEL_CONFIG[model_type]
        effective_scale = scale if scale is not None else model_cfg["scale"]

        cache_key = self._get_upscaler_key(model_type, effective_scale)
        if cache_key in self._upscalers:
            return self._upscalers[cache_key]

        use_gpu = config.REALESRGAN_USE_GPU

        if use_gpu and torch.cuda.is_available():
            device = torch.device('cuda')
            self._gpu_used = True
            print(f"GPU detectada: {torch.cuda.get_device_name(0)}")
        else:
            device = torch.device('cpu')
            self._gpu_used = False
            if use_gpu and not torch.cuda.is_available():
                print("GPU solicitada pero no disponible, usando CPU")

        upscaler = RealESRGANUpscaler(
            model_type=model_type,
            scale=effective_scale,
            tile_size=config.REALESRGAN_TILE_SIZE,
            device=device,
            use_gpu=use_gpu
        )

        weights_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'weights')
        model_filename = model_cfg["filename"]
        model_path = os.path.join(weights_dir, model_filename)

        upscaler.load_model(model_path if os.path.exists(model_path) else None)
        self._upscalers[cache_key] = upscaler

        print(f"Upscaler inicializado (model={model_type.value}, scale={effective_scale}, "
              f"device={device}, gpu_used={self._gpu_used})")

        return upscaler

    def _init_face_enhancer(self, upscale: int = 1) -> Optional[GFPGANer]:
        """Inicializa el face enhancer GFPGAN."""
        if self._face_enhancer is not None and self._face_enhancer.upscale == upscale:
            return self._face_enhancer

        use_gpu = config.REALESRGAN_USE_GPU
        if use_gpu and torch.cuda.is_available():
            device = torch.device('cuda')
        else:
            device = torch.device('cpu')

        gfpgan_path = os.path.join(WEIGHTS_DIR, 'GFPGANv1.4.pth')

        try:
            self._face_enhancer = GFPGANer(
                model_path=gfpgan_path if os.path.exists(gfpgan_path) else None,
                upscale=upscale,
                device=device
            )
            print(f"GFPGAN inicializado (upscale={upscale}, device={device})")
        except Exception as e:
            print(f"Error inicializando GFPGAN: {e}")
            self._face_enhancer = None

        return self._face_enhancer

    def _decode_base64_image(self, base64_string: str) -> Tuple[Optional[Image.Image], Optional[str]]:
        """Decodifica una imagen desde base64."""
        try:
            if ',' in base64_string:
                base64_string = base64_string.split(',')[1]

            image_data = base64.b64decode(base64_string)
            image = Image.open(io.BytesIO(image_data))
            return image, None
        except Exception as e:
            return None, f"Error decodificando imagen: {str(e)}"

    def _encode_image_base64(self, image: Image.Image, img_format: str = "PNG") -> str:
        """Codifica una imagen a base64."""
        buffer = io.BytesIO()
        if img_format.upper() == "JPG":
            img_format = "JPEG"
        image.save(buffer, format=img_format)
        return base64.b64encode(buffer.getvalue()).decode('utf-8')

    def _read_image_base64(self, file_path: str) -> Optional[str]:
        """Lee una imagen desde disco y la retorna como base64."""
        try:
            if not os.path.exists(file_path):
                return None
            with open(file_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        except Exception:
            return None

    def _save_image_to_disk(self, image: Image.Image, file_path: str, img_format: str = "PNG"):
        """Guarda una imagen en disco."""
        if img_format.upper() == "JPG":
            img_format = "JPEG"
        image.save(file_path, format=img_format)

    def _delete_file(self, file_path: str) -> bool:
        """Elimina un archivo del disco."""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
        except Exception:
            return False

    def _generate_file_path(self, _user_id: str, image_id: str, suffix: str, extension: str) -> str:
        """Genera la ruta del archivo para una imagen en la raíz de image_history."""
        filename = f"{image_id}_{suffix}.{extension.lower()}"
        return os.path.join(IMAGE_STORAGE_PATH, filename)

    def _generate_description(self, filename: str, width: int, height: int,
                              model_type: str, now: datetime) -> str:
        """Genera una descripción automática para la imagen."""
        date_str = now.strftime("%d/%m/%Y %H:%M")
        return f"Tratamiento de imagen {filename} de dimensiones {width}x{height} con el filtro {model_type}, hoy {date_str}"

    def _get_image_info(self, image: Image.Image, base64_string: str) -> dict:
        """Obtiene información de una imagen."""
        if ',' in base64_string:
            base64_string = base64_string.split(',')[1]
        size_bytes = len(base64.b64decode(base64_string))

        return {
            "width": image.width,
            "height": image.height,
            "format": image.format or "PNG",
            "size": size_bytes
        }

    def _resize_to_output(self, image: Image.Image, output_width: Optional[int],
                          output_height: Optional[int]) -> Image.Image:
        """Redimensiona la imagen a las dimensiones de salida especificadas."""
        if output_width is None and output_height is None:
            return image

        current_width, current_height = image.size

        if output_width and output_height:
            new_size = (output_width, output_height)
        elif output_width:
            ratio = output_width / current_width
            new_size = (output_width, int(current_height * ratio))
        else:
            ratio = output_height / current_height
            new_size = (int(current_width * ratio), output_height)

        return image.resize(new_size, Image.Resampling.LANCZOS)

    def _process_image_enhancement(
        self,
        image_rgb: Image.Image,
        model_type: ModelType,
        effective_scale: int,
        face_enhance: bool,
        output_width: Optional[int],
        output_height: Optional[int]
    ) -> Image.Image:
        """Procesa la imagen con Real-ESRGAN y opcionalmente GFPGAN."""
        # Inicializar upscaler con el modelo seleccionado
        upscaler = self._init_upscaler(model_type, effective_scale)

        # Convertir a numpy array y procesar
        img_array = np.array(image_rgb)
        enhanced_array = upscaler.enhance(img_array)

        # Aplicar face enhancement si se solicitó
        if face_enhance:
            enhanced_array = self._apply_face_enhancement(enhanced_array)

        # Convertir de vuelta a PIL
        enhanced_image = Image.fromarray(enhanced_array)

        # Aplicar redimensionado si se especificó
        if output_width or output_height:
            enhanced_image = self._resize_to_output(enhanced_image, output_width, output_height)

        return enhanced_image

    def _apply_face_enhancement(self, enhanced_array: np.ndarray) -> np.ndarray:
        """Aplica mejora de rostros con GFPGAN."""
        print("Aplicando face enhancement con GFPGAN...")
        face_enhancer = self._init_face_enhancer(upscale=1)
        if face_enhancer is not None:
            enhanced_bgr = cv2.cvtColor(enhanced_array, cv2.COLOR_RGB2BGR)
            _, _, restored_img = face_enhancer.enhance(
                enhanced_bgr,
                has_aligned=False,
                only_center_face=False,
                paste_back=True
            )
            enhanced_array = cv2.cvtColor(restored_img, cv2.COLOR_BGR2RGB)
            print("Face enhancement completado")
        return enhanced_array

    async def enhance_image(
        self,
        user_id: str,
        request: ImageEnhanceRequest
    ) -> Tuple[Optional[ImageDetailResponse], Optional[str]]:
        """Procesa y mejora una imagen, guardando en disco."""
        self._get_collection()

        # Decodificar imagen
        image, error = self._decode_base64_image(request.image_base64)
        if error:
            return None, error

        # Validar formato
        img_format = image.format or "PNG"
        if img_format.lower() not in [f.lower() for f in config.ALLOWED_IMAGE_FORMATS]:
            return None, f"Formato no soportado: {img_format}"

        # Obtener info de la imagen original
        img_info = self._get_image_info(image, request.image_base64)

        # Validar tamaño
        max_size = config.MAX_IMAGE_SIZE_MB * 1024 * 1024
        if img_info["size"] > max_size:
            return None, f"Imagen excede el tamaño máximo de {config.MAX_IMAGE_SIZE_MB}MB"

        # Determinar modelo y escala a usar
        model_type = request.model_type or ModelType.GENERAL_X4
        model_cfg = MODEL_CONFIG[model_type]
        effective_scale = request.scale if request.scale is not None else model_cfg["scale"]

        # Generar ID único para la imagen
        image_id = str(uuid.uuid4())
        now = datetime.utcnow()
        original_filename = request.filename or "image.png"
        extension = img_format.lower() if img_format.lower() != "jpeg" else "jpg"

        # Generar rutas de archivo
        original_path = self._generate_file_path(user_id, image_id, "original", extension)
        enhanced_path = self._generate_file_path(user_id, image_id, "enhanced", extension)

        # Generar descripción
        description = request.description
        if not description or description.strip() == "":
            description = self._generate_description(
                original_filename,
                img_info["width"],
                img_info["height"],
                model_type.value,
                now
            )

        # Guardar imagen original en disco
        if image.mode != 'RGB':
            image_rgb = image.convert('RGB')
        else:
            image_rgb = image
        self._save_image_to_disk(image_rgb, original_path, extension.upper())

        # Determinar si se aplicará face enhancement
        face_enhance = request.face_enhance or False

        # Crear registro en DB (sin datos binarios)
        image_doc = {
            "user_id": user_id,
            "original_filename": original_filename,
            "description": description,
            "original_width": img_info["width"],
            "original_height": img_info["height"],
            "model_type": model_type.value,
            "scale": effective_scale,
            "face_enhance": face_enhance,
            "original_path": original_path,
            "enhanced_path": None,
            "status": ImageStatus.PROCESSING.value,
            "created_at": now,
        }

        result = await self.images_collection.insert_one(image_doc)
        db_image_id = str(result.inserted_id)

        # Procesar imagen
        start_time = time.time()

        try:
            # Procesar imagen con Real-ESRGAN y opcionalmente GFPGAN
            enhanced_image = self._process_image_enhancement(
                image_rgb,
                model_type,
                effective_scale,
                face_enhance,
                request.output_width,
                request.output_height
            )

            # Guardar imagen mejorada en disco
            self._save_image_to_disk(enhanced_image, enhanced_path, extension.upper())

            processing_time = int((time.time() - start_time) * 1000)
            completed_at = datetime.utcnow()

            # Actualizar registro en DB
            update_data = {
                "enhanced_path": enhanced_path,
                "enhanced_width": enhanced_image.width,
                "enhanced_height": enhanced_image.height,
                "status": ImageStatus.COMPLETED.value,
                "processing_time_ms": processing_time,
                "gpu_used": self._gpu_used,
                "completed_at": completed_at,
            }

            await self.images_collection.update_one(
                {"_id": ObjectId(db_image_id)},
                {"$set": update_data}
            )

            # Leer imágenes como base64 para la respuesta
            original_base64 = self._read_image_base64(original_path)
            enhanced_base64 = self._read_image_base64(enhanced_path)

            return ImageDetailResponse(
                id=db_image_id,
                original_filename=original_filename,
                description=description,
                original_width=img_info["width"],
                original_height=img_info["height"],
                enhanced_width=enhanced_image.width,
                enhanced_height=enhanced_image.height,
                model_type=model_type.value,
                scale=effective_scale,
                face_enhance=face_enhance,
                status=ImageStatus.COMPLETED.value,
                processing_time_ms=processing_time,
                gpu_used=self._gpu_used,
                created_at=now,
                completed_at=completed_at,
                original_base64=original_base64,
                enhanced_base64=enhanced_base64,
                error_message=None
            ), None

        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            error_msg = str(e)

            await self.images_collection.update_one(
                {"_id": ObjectId(db_image_id)},
                {"$set": {
                    "status": ImageStatus.FAILED.value,
                    "error_message": error_msg,
                    "processing_time_ms": processing_time,
                    "gpu_used": self._gpu_used,
                }}
            )

            return None, f"Error procesando imagen: {error_msg}"

    async def get_image(self, image_id: str, user_id: str) -> Optional[ImageDetailResponse]:
        """Obtiene una imagen por su ID, leyendo los archivos desde disco."""
        self._get_collection()

        try:
            image_doc = await self.images_collection.find_one({
                "_id": ObjectId(image_id),
                "user_id": user_id
            })

            if not image_doc:
                return None

            # Leer imágenes desde disco
            original_base64 = None
            enhanced_base64 = None

            if image_doc.get("original_path"):
                original_base64 = self._read_image_base64(image_doc["original_path"])

            if image_doc.get("enhanced_path"):
                enhanced_base64 = self._read_image_base64(image_doc["enhanced_path"])

            return ImageDetailResponse(
                id=str(image_doc["_id"]),
                original_filename=image_doc["original_filename"],
                description=image_doc.get("description", ""),
                original_width=image_doc["original_width"],
                original_height=image_doc["original_height"],
                enhanced_width=image_doc.get("enhanced_width"),
                enhanced_height=image_doc.get("enhanced_height"),
                model_type=image_doc.get("model_type", ModelType.GENERAL_X4.value),
                scale=image_doc["scale"],
                face_enhance=image_doc.get("face_enhance", False),
                status=image_doc["status"],
                processing_time_ms=image_doc.get("processing_time_ms"),
                gpu_used=image_doc.get("gpu_used"),
                created_at=image_doc["created_at"],
                completed_at=image_doc.get("completed_at"),
                original_base64=original_base64,
                enhanced_base64=enhanced_base64,
                error_message=image_doc.get("error_message")
            )
        except Exception:
            return None

    async def list_images(
        self,
        user_id: str,
        page: int = 1,
        per_page: int = 10,
        status: Optional[str] = None
    ) -> ImageListResponse:
        """Lista las imágenes de un usuario con paginación."""
        self._get_collection()

        filter_query = {"user_id": user_id}
        if status:
            filter_query["status"] = status

        total = await self.images_collection.count_documents(filter_query)

        skip = (page - 1) * per_page
        cursor = self.images_collection.find(filter_query).sort(
            "created_at", -1
        ).skip(skip).limit(per_page)

        images = []
        async for doc in cursor:
            images.append(ImageResponse(
                id=str(doc["_id"]),
                original_filename=doc["original_filename"],
                description=doc.get("description", ""),
                original_width=doc["original_width"],
                original_height=doc["original_height"],
                enhanced_width=doc.get("enhanced_width"),
                enhanced_height=doc.get("enhanced_height"),
                model_type=doc.get("model_type", ModelType.GENERAL_X4.value),
                scale=doc["scale"],
                face_enhance=doc.get("face_enhance", False),
                status=doc["status"],
                processing_time_ms=doc.get("processing_time_ms"),
                gpu_used=doc.get("gpu_used"),
                created_at=doc["created_at"],
                completed_at=doc.get("completed_at")
            ))

        return ImageListResponse(
            total=total,
            page=page,
            per_page=per_page,
            images=images
        )

    async def delete_image(self, image_id: str, user_id: str) -> bool:
        """Elimina una imagen de la base de datos y del disco."""
        self._get_collection()

        try:
            # Primero obtener el documento para conocer las rutas de archivos
            image_doc = await self.images_collection.find_one({
                "_id": ObjectId(image_id),
                "user_id": user_id
            })

            if not image_doc:
                return False

            # Eliminar archivos del disco
            if image_doc.get("original_path"):
                self._delete_file(image_doc["original_path"])

            if image_doc.get("enhanced_path"):
                self._delete_file(image_doc["enhanced_path"])

            # Eliminar registro de la base de datos
            result = await self.images_collection.delete_one({
                "_id": ObjectId(image_id),
                "user_id": user_id
            })

            return result.deleted_count > 0
        except Exception as e:
            print(f"Error eliminando imagen: {e}")
            return False


image_service = ImageService()
