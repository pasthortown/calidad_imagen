import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { MediaType, ModelType, MODELS } from '../types/media';
import mediaService from '../services/mediaService';
import { AxiosError } from 'axios';
import '../styles/home.css';

const Home: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // State
  const [mediaType, setMediaType] = useState<MediaType>('image');
  const [file, setFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [modelType, setModelType] = useState<ModelType>('general_x4');
  const [faceEnhance, setFaceEnhance] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // File handling
  const handleFileSelect = useCallback((selectedFile: File) => {
    setError(null);
    setSuccess(null);

    const isImage = mediaService.isValidImageFile(selectedFile);
    const isVideo = mediaService.isValidVideoFile(selectedFile);

    if (mediaType === 'image' && !isImage) {
      setError('Por favor selecciona una imagen válida (JPG, PNG, WEBP)');
      return;
    }

    if (mediaType === 'video' && !isVideo) {
      setError('Por favor selecciona un video válido (MP4, MKV, AVI, MOV, WEBM)');
      return;
    }

    setFile(selectedFile);

    // Create preview for images
    if (isImage) {
      const reader = new FileReader();
      reader.onload = (e) => {
        setFilePreview(e.target?.result as string);
      };
      reader.readAsDataURL(selectedFile);
    } else {
      setFilePreview(null);
    }
  }, [mediaType]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      handleFileSelect(droppedFile);
    }
  }, [handleFileSelect]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      handleFileSelect(selectedFile);
    }
  };

  const handleZoneClick = () => {
    fileInputRef.current?.click();
  };

  const handleRemoveFile = () => {
    setFile(null);
    setFilePreview(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleMediaTypeChange = (type: MediaType) => {
    setMediaType(type);
    setFile(null);
    setFilePreview(null);
    setError(null);
    setSuccess(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Process
  const handleProcess = async () => {
    if (!file) {
      setError('Por favor selecciona un archivo');
      return;
    }

    setIsProcessing(true);
    setError(null);
    setSuccess(null);

    try {
      const base64 = await mediaService.fileToBase64(file);
      const selectedModel = MODELS.find(m => m.id === modelType);

      if (mediaType === 'image') {
        const response = await mediaService.enhanceImage({
          image_base64: base64,
          filename: file.name,
          model_type: modelType,
          scale: selectedModel?.scale,
          face_enhance: faceEnhance,
        });

        if (response.image.status === 'completed' && response.image.enhanced_base64) {
          const enhancedFilename = mediaService.getEnhancedFilename(file.name);
          const mimeType = mediaService.getMimeType(file.name);
          mediaService.downloadBase64File(
            response.image.enhanced_base64,
            enhancedFilename,
            mimeType
          );

          setSuccess(`Imagen procesada exitosamente en ${(response.image.processing_time_ms / 1000).toFixed(2)}s. La descarga comenzará automáticamente.`);

          // Reset form
          setFile(null);
          setFilePreview(null);
          if (fileInputRef.current) {
            fileInputRef.current.value = '';
          }
        } else {
          setError(response.image.error_message || 'Error al procesar la imagen');
        }
      } else {
        // Video processing
        await mediaService.enhanceVideo({
          video_base64: base64,
          filename: file.name,
          model_type: modelType,
          scale: selectedModel?.scale,
          face_enhance: faceEnhance,
        });

        setSuccess('Video enviado para procesamiento. Puedes ver el progreso y descargar el resultado en la sección de Historial.');

        // Reset form
        setFile(null);
        setFilePreview(null);
        if (fileInputRef.current) {
          fileInputRef.current.value = '';
        }

        // Redirect to history after a delay
        setTimeout(() => {
          navigate('/history');
        }, 3000);
      }
    } catch (err) {
      const axiosError = err as AxiosError<{ error?: string; detail?: string }>;
      const message =
        axiosError.response?.data?.error ||
        axiosError.response?.data?.detail ||
        'Error al procesar el archivo. Intenta de nuevo.';
      setError(message);
    } finally {
      setIsProcessing(false);
    }
  };

  const getAcceptedFormats = () => {
    return mediaType === 'image'
      ? 'image/jpeg,image/jpg,image/png,image/webp'
      : 'video/mp4,video/x-matroska,video/avi,video/quicktime,video/webm,.mkv';
  };

  const getFormatText = () => {
    return mediaType === 'image'
      ? 'Formatos: JPG, PNG, WEBP'
      : 'Formatos: MP4, MKV, AVI, MOV, WEBM';
  };

  // Model icon renderer
  const renderModelIcon = (iconType: string) => {
    switch (iconType) {
      case 'photo':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <polyline points="21 15 16 10 5 21" />
          </svg>
        );
      case 'photo-2x':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
            <circle cx="8.5" cy="8.5" r="1.5" />
            <path d="M14 14l3-3 4 4" />
          </svg>
        );
      case 'anime':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M12 2L2 7l10 5 10-5-10-5z" />
            <path d="M2 17l10 5 10-5" />
            <path d="M2 12l10 5 10-5" />
          </svg>
        );
      case 'video':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="23 7 16 12 23 17 23 7" />
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
          </svg>
        );
      case 'fast':
        return (
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
          </svg>
        );
      default:
        return null;
    }
  };

  return (
    <div className="page-content">
      <div className="home-page">
        <div className="home-header">
          <h1 className="home-title">Hola, {user?.username || 'Usuario'}</h1>
          <p className="home-subtitle">Mejora tus imágenes y videos con inteligencia artificial</p>
        </div>

        <div className="process-steps">
          {/* Step 1: Media Type */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-number">1</span>
              <h3 className="step-title">Tipo de archivo</h3>
            </div>
            <div className="media-type-selector">
              <button
                className={`media-type-btn ${mediaType === 'image' ? 'selected' : ''}`}
                onClick={() => handleMediaTypeChange('image')}
              >
                <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                  <circle cx="8.5" cy="8.5" r="1.5" />
                  <polyline points="21 15 16 10 5 21" />
                </svg>
                <span className="label">Imagen</span>
              </button>
              <button
                className={`media-type-btn ${mediaType === 'video' ? 'selected' : ''}`}
                onClick={() => handleMediaTypeChange('video')}
              >
                <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <polygon points="23 7 16 12 23 17 23 7" />
                  <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                </svg>
                <span className="label">Video</span>
              </button>
            </div>
          </div>

          {/* Step 2: File Upload */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-number">2</span>
              <h3 className="step-title">Cargar archivo</h3>
            </div>
            <div
              className={`upload-zone ${isDragOver ? 'drag-over' : ''} ${file ? 'has-file' : ''}`}
              onClick={handleZoneClick}
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept={getAcceptedFormats()}
                onChange={handleFileInputChange}
              />
              <svg className="upload-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                {file ? (
                  <>
                    <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </>
                ) : (
                  <>
                    <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </>
                )}
              </svg>
              <p className="upload-title">
                {file ? file.name : 'Arrastra y suelta tu archivo aquí'}
              </p>
              <p className="upload-subtitle">
                {file
                  ? mediaService.formatFileSize(file.size)
                  : 'o haz clic para seleccionar'}
              </p>
              <p className="upload-formats">{getFormatText()}</p>
            </div>

            {file && filePreview && (
              <div className="file-preview">
                <img
                  src={filePreview}
                  alt="Preview"
                  className="file-preview-thumbnail"
                />
                <div className="file-preview-info">
                  <p className="file-preview-name">{file.name}</p>
                  <p className="file-preview-size">{mediaService.formatFileSize(file.size)}</p>
                </div>
                <button
                  className="file-preview-remove"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveFile();
                  }}
                >
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <line x1="18" y1="6" x2="6" y2="18" />
                    <line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
            )}
          </div>

          {/* Step 3: Model Selection */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-number">3</span>
              <h3 className="step-title">Filtro a aplicar</h3>
            </div>
            <div className="model-selector">
              {MODELS.map((model) => (
                <button
                  key={model.id}
                  className={`model-btn ${modelType === model.id ? 'selected' : ''}`}
                  onClick={() => setModelType(model.id)}
                >
                  <span className="model-icon">{renderModelIcon(model.icon)}</span>
                  <span className="model-name">{model.name}</span>
                  <span className="model-desc">{model.description}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Step 4: Face Enhancement */}
          <div className="step-card">
            <div className="step-header">
              <span className="step-number">4</span>
              <h3 className="step-title">Opciones adicionales</h3>
            </div>
            <div className="toggle-container">
              <div className="toggle-info">
                <div className="toggle-icon">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                    <circle cx="12" cy="7" r="4" />
                  </svg>
                </div>
                <div className="toggle-text">
                  <h4>Mejora de rostros</h4>
                  <p>Aplica GFPGAN para mejorar rostros en la imagen</p>
                </div>
              </div>
              <label className={`toggle-switch ${faceEnhance ? 'active' : ''}`}>
                <input
                  type="checkbox"
                  checked={faceEnhance}
                  onChange={(e) => setFaceEnhance(e.target.checked)}
                />
                <span className="toggle-slider" />
              </label>
            </div>
          </div>
        </div>

        {/* Process Button */}
        <div className="process-section">
          <button
            className={`process-btn ${isProcessing ? 'processing' : ''}`}
            onClick={handleProcess}
            disabled={!file || isProcessing}
          >
            {isProcessing ? (
              <>
                <span className="spinner" />
                Procesando...
              </>
            ) : (
              <>
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
                </svg>
                Iniciar proceso
              </>
            )}
          </button>

          {error && (
            <div className="process-alert error">
              <svg className="process-alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
              <div className="process-alert-content">
                <p className="process-alert-title">Error</p>
                <p className="process-alert-message">{error}</p>
              </div>
            </div>
          )}

          {success && (
            <div className={`process-alert ${mediaType === 'video' ? 'info' : 'success'}`}>
              <svg className="process-alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                {mediaType === 'video' ? (
                  <>
                    <circle cx="12" cy="12" r="10" />
                    <line x1="12" y1="16" x2="12" y2="12" />
                    <line x1="12" y1="8" x2="12.01" y2="8" />
                  </>
                ) : (
                  <>
                    <path d="M22 11.08V12a10 10 0 11-5.93-9.14" />
                    <polyline points="22 4 12 14.01 9 11.01" />
                  </>
                )}
              </svg>
              <div className="process-alert-content">
                <p className="process-alert-title">
                  {mediaType === 'video' ? 'Video enviado' : 'Completado'}
                </p>
                <p className="process-alert-message">{success}</p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Home;
