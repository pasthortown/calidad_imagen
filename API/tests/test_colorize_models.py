"""Unit tests for colorization models."""

import pytest
from datetime import datetime
from app.models.colorize import (
    ColorizeStatus,
    ColorizeImageRequest,
    ColorizeVideoRequest,
    ColorizeImageResponse,
    ColorizeImageDetailResponse,
    ColorizeVideoResponse,
    ColorizeVideoDetailResponse,
    ColorizeImageListResponse,
    ColorizeVideoListResponse,
    ColorizeInfoResponse,
)


class TestColorizeStatus:
    """Tests for ColorizeStatus enum."""

    def test_status_values(self):
        """Test that all expected status values exist."""
        assert ColorizeStatus.PENDING.value == "pending"
        assert ColorizeStatus.PROCESSING.value == "processing"
        assert ColorizeStatus.IN_PROGRESS.value == "in_progress"
        assert ColorizeStatus.COMPLETED.value == "completed"
        assert ColorizeStatus.FAILED.value == "failed"
        assert ColorizeStatus.ERROR.value == "error"


class TestColorizeImageRequest:
    """Tests for ColorizeImageRequest model."""

    def test_required_field(self):
        """Test that image_base64 is required."""
        request = ColorizeImageRequest(image_base64="base64data")
        assert request.image_base64 == "base64data"

    def test_optional_fields(self):
        """Test optional fields have correct defaults."""
        request = ColorizeImageRequest(image_base64="base64data")
        assert request.filename is None
        assert request.description is None
        assert request.output_format == "PNG"

    def test_all_fields(self):
        """Test setting all fields."""
        request = ColorizeImageRequest(
            image_base64="base64data",
            filename="test.png",
            description="Test image",
            output_format="JPEG"
        )
        assert request.image_base64 == "base64data"
        assert request.filename == "test.png"
        assert request.description == "Test image"
        assert request.output_format == "JPEG"


class TestColorizeVideoRequest:
    """Tests for ColorizeVideoRequest model."""

    def test_required_fields(self):
        """Test that required fields are validated."""
        request = ColorizeVideoRequest(
            video_base64="base64data",
            filename="test.mp4"
        )
        assert request.video_base64 == "base64data"
        assert request.filename == "test.mp4"

    def test_optional_description(self):
        """Test optional description field."""
        request = ColorizeVideoRequest(
            video_base64="base64data",
            filename="test.mp4",
            description="Test video"
        )
        assert request.description == "Test video"


class TestColorizeImageResponse:
    """Tests for ColorizeImageResponse model."""

    def test_create_response(self):
        """Test creating an image response."""
        now = datetime.utcnow()
        response = ColorizeImageResponse(
            id="test-id",
            original_filename="test.png",
            description="Test",
            original_width=640,
            original_height=480,
            colorized_width=640,
            colorized_height=480,
            status="completed",
            processing_time_ms=1000,
            gpu_used=True,
            created_at=now,
            completed_at=now
        )
        assert response.id == "test-id"
        assert response.original_width == 640
        assert response.colorized_width == 640
        assert response.status == "completed"


class TestColorizeImageDetailResponse:
    """Tests for ColorizeImageDetailResponse model."""

    def test_detail_response_with_base64(self):
        """Test detail response includes base64 fields."""
        now = datetime.utcnow()
        response = ColorizeImageDetailResponse(
            id="test-id",
            original_filename="test.png",
            description="Test",
            original_width=640,
            original_height=480,
            colorized_width=640,
            colorized_height=480,
            status="completed",
            processing_time_ms=1000,
            gpu_used=True,
            created_at=now,
            completed_at=now,
            original_base64="original_data",
            colorized_base64="colorized_data",
            error_message=None
        )
        assert response.original_base64 == "original_data"
        assert response.colorized_base64 == "colorized_data"
        assert response.error_message is None


class TestColorizeVideoResponse:
    """Tests for ColorizeVideoResponse model."""

    def test_create_video_response(self):
        """Test creating a video response."""
        now = datetime.utcnow()
        response = ColorizeVideoResponse(
            id="test-id",
            original_filename="test.mp4",
            description="Test",
            original_width=1920,
            original_height=1080,
            colorized_width=1920,
            colorized_height=1080,
            duration_seconds=10.5,
            fps=30.0,
            frame_count=315,
            status="in_progress",
            error_message=None,
            processing_time_ms=None,
            gpu_used=None,
            frames_processed=100,
            created_at=now,
            completed_at=None
        )
        assert response.id == "test-id"
        assert response.frame_count == 315
        assert response.frames_processed == 100
        assert response.status == "in_progress"


class TestColorizeImageListResponse:
    """Tests for ColorizeImageListResponse model."""

    def test_list_response(self):
        """Test creating a list response."""
        response = ColorizeImageListResponse(
            total=100,
            page=1,
            per_page=10,
            images=[]
        )
        assert response.total == 100
        assert response.page == 1
        assert response.per_page == 10
        assert len(response.images) == 0


class TestColorizeVideoListResponse:
    """Tests for ColorizeVideoListResponse model."""

    def test_list_response(self):
        """Test creating a list response."""
        response = ColorizeVideoListResponse(
            total=50,
            page=2,
            per_page=20,
            videos=[]
        )
        assert response.total == 50
        assert response.page == 2
        assert response.per_page == 20


class TestColorizeInfoResponse:
    """Tests for ColorizeInfoResponse model."""

    def test_info_response(self):
        """Test creating an info response."""
        response = ColorizeInfoResponse(
            model_type="stable",
            render_factor=16,
            device="cuda",
            gpu_available=True,
            model_loaded=True
        )
        assert response.model_type == "stable"
        assert response.render_factor == 16
        assert response.device == "cuda"
        assert response.gpu_available is True
        assert response.model_loaded is True

    def test_info_response_cpu(self):
        """Test info response for CPU-only system."""
        response = ColorizeInfoResponse(
            model_type="stable",
            render_factor=16,
            device="cpu",
            gpu_available=False,
            model_loaded=True
        )
        assert response.device == "cpu"
        assert response.gpu_available is False
