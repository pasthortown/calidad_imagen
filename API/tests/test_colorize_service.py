"""Unit tests for colorization service."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import base64
import io
from PIL import Image

from app.services.colorize_service import (
    ColorizeService,
    DeOldifyColorizer,
    ColorizationError,
)
from app.models.colorize import (
    ColorizeImageRequest,
    ColorizeVideoRequest,
    ColorizeInfoResponse,
)


class TestDeOldifyColorizer:
    """Tests for DeOldifyColorizer class."""

    def test_init_without_onnx(self):
        """Test initialization when ONNX is not available."""
        with patch('app.services.colorize_service.ONNX_AVAILABLE', False):
            colorizer = DeOldifyColorizer()
            assert colorizer.session is None
            assert colorizer._model_loaded is False

    def test_is_loaded_property(self):
        """Test is_loaded property."""
        colorizer = DeOldifyColorizer.__new__(DeOldifyColorizer)
        colorizer._model_loaded = False
        assert colorizer.is_loaded is False

        colorizer._model_loaded = True
        assert colorizer.is_loaded is True


class TestColorizeService:
    """Tests for ColorizeService class."""

    def test_service_initialization(self):
        """Test service initialization."""
        service = ColorizeService()
        assert service.colorized_images_collection is None
        assert service.colorized_videos_collection is None
        assert service._colorizer is None

    def test_decode_base64_image_valid(self):
        """Test decoding valid base64 image."""
        service = ColorizeService()

        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='gray')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        base64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')

        decoded_img, error = service._decode_base64_image(base64_string)
        assert decoded_img is not None
        assert error is None
        assert decoded_img.size == (100, 100)

    def test_decode_base64_image_with_prefix(self):
        """Test decoding base64 image with data URL prefix."""
        service = ColorizeService()

        img = Image.new('RGB', (100, 100), color='gray')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        base64_string = f"data:image/png;base64,{base64_data}"

        decoded_img, error = service._decode_base64_image(base64_string)
        assert decoded_img is not None
        assert error is None

    def test_decode_base64_image_invalid(self):
        """Test decoding invalid base64 string."""
        service = ColorizeService()
        decoded_img, error = service._decode_base64_image("invalid_base64!")
        assert decoded_img is None
        assert error is not None
        assert "Error decodificando imagen" in error

    def test_encode_image_base64(self):
        """Test encoding image to base64."""
        service = ColorizeService()
        img = Image.new('RGB', (100, 100), color='red')
        base64_string = service._encode_image_base64(img, "PNG")
        assert base64_string is not None
        assert len(base64_string) > 0

        # Verify it can be decoded back
        decoded = base64.b64decode(base64_string)
        assert len(decoded) > 0

    def test_encode_image_base64_jpeg(self):
        """Test encoding image to JPEG base64."""
        service = ColorizeService()
        img = Image.new('RGB', (100, 100), color='blue')
        base64_string = service._encode_image_base64(img, "JPG")
        assert base64_string is not None

    def test_generate_file_path(self):
        """Test generating file path."""
        service = ColorizeService()
        path = service._generate_file_path("test-id", "colorized", "png")
        assert "test-id_colorized.png" in path

    def test_generate_description(self):
        """Test generating automatic description."""
        service = ColorizeService()
        from datetime import datetime
        now = datetime.utcnow()
        description = service._generate_description("test.png", 640, 480, now)
        assert "test.png" in description
        assert "640x480" in description

    def test_decode_base64_video_valid(self):
        """Test decoding valid base64 video."""
        service = ColorizeService()
        # Create some dummy video data
        video_data = b"fake video data for testing"
        base64_string = base64.b64encode(video_data).decode('utf-8')

        decoded_data, error = service._decode_base64_video(base64_string)
        assert decoded_data == video_data
        assert error is None

    def test_decode_base64_video_with_prefix(self):
        """Test decoding base64 video with data URL prefix."""
        service = ColorizeService()
        video_data = b"fake video data"
        base64_data = base64.b64encode(video_data).decode('utf-8')
        base64_string = f"data:video/mp4;base64,{base64_data}"

        decoded_data, error = service._decode_base64_video(base64_string)
        assert decoded_data == video_data
        assert error is None

    def test_decode_base64_video_invalid(self):
        """Test decoding invalid base64 video."""
        service = ColorizeService()
        decoded_data, error = service._decode_base64_video("invalid!")
        assert decoded_data is None
        assert error is not None

    def test_get_info(self):
        """Test getting colorization info."""
        service = ColorizeService()

        # Mock the colorizer
        mock_colorizer = Mock()
        mock_colorizer.render_factor = 16
        mock_colorizer.device = "cpu"
        mock_colorizer.is_loaded = False

        with patch.object(service, '_init_colorizer', return_value=mock_colorizer):
            info = service.get_info()
            assert isinstance(info, ColorizeInfoResponse)
            assert info.render_factor == 16
            assert info.device == "cpu"

    def test_get_image_info(self):
        """Test getting image info."""
        service = ColorizeService()

        img = Image.new('RGB', (640, 480), color='gray')
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        base64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')

        info = service._get_image_info(img, base64_string)
        assert info["width"] == 640
        assert info["height"] == 480
        assert info["format"] == "PNG" or info["format"] is None
        assert info["size"] > 0

    def test_read_file_base64_nonexistent(self):
        """Test reading non-existent file."""
        service = ColorizeService()
        result = service._read_file_base64("/nonexistent/path/file.png")
        assert result is None

    def test_delete_file_nonexistent(self):
        """Test deleting non-existent file."""
        service = ColorizeService()
        result = service._delete_file("/nonexistent/path/file.png")
        assert result is False


class TestColorizationError:
    """Tests for ColorizationError exception."""

    def test_error_message(self):
        """Test error message is preserved."""
        error = ColorizationError("Test error message")
        assert str(error) == "Test error message"

    def test_raise_error(self):
        """Test raising ColorizationError."""
        with pytest.raises(ColorizationError) as exc_info:
            raise ColorizationError("Model not loaded")
        assert "Model not loaded" in str(exc_info.value)
