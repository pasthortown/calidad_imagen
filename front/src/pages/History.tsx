import React, { useState, useEffect, useCallback } from 'react';
import { ImageHistoryItem, VideoHistoryItem, JobStatus } from '../types/media';
import mediaService from '../services/mediaService';
import '../styles/history.css';

type TabType = 'all' | 'images' | 'videos';

interface HistoryItem {
  id: string;
  type: 'image' | 'video';
  original_filename: string;
  model_type: string;
  original_width: number;
  original_height: number;
  enhanced_width: number | null;
  enhanced_height: number | null;
  status: JobStatus;
  created_at: string;
  completed_at: string | null;
  processing_time_ms: number | null;
  // Video specific
  duration_seconds?: number;
  frames_processed?: number;
  frame_count?: number;
}

const History: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('all');
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(true);
  const [totalItems, setTotalItems] = useState(0);
  const perPage = 20;

  const fetchHistory = useCallback(async (resetPage = false) => {
    setLoading(true);
    setError(null);
    const currentPage = resetPage ? 1 : page;

    try {
      const allItems: HistoryItem[] = [];
      let totalCount = 0;

      if (activeTab === 'all' || activeTab === 'images') {
        const imageResponse = await mediaService.getImageHistory(currentPage, perPage);
        const imageItems: HistoryItem[] = imageResponse.images.map((img: ImageHistoryItem) => ({
          id: img.id,
          type: 'image' as const,
          original_filename: img.original_filename,
          model_type: img.model_type,
          original_width: img.original_width,
          original_height: img.original_height,
          enhanced_width: img.enhanced_width,
          enhanced_height: img.enhanced_height,
          status: img.status,
          created_at: img.created_at,
          completed_at: img.completed_at,
          processing_time_ms: img.processing_time_ms,
        }));
        allItems.push(...imageItems);
        totalCount += imageResponse.total;
      }

      if (activeTab === 'all' || activeTab === 'videos') {
        const videoResponse = await mediaService.getVideoHistory(currentPage, perPage);
        const videoItems: HistoryItem[] = videoResponse.videos.map((vid: VideoHistoryItem) => ({
          id: vid.id,
          type: 'video' as const,
          original_filename: vid.original_filename,
          model_type: vid.model_type,
          original_width: vid.original_width,
          original_height: vid.original_height,
          enhanced_width: vid.enhanced_width,
          enhanced_height: vid.enhanced_height,
          status: vid.status,
          created_at: vid.created_at,
          completed_at: vid.completed_at,
          processing_time_ms: vid.processing_time_ms,
          duration_seconds: vid.duration_seconds,
          frames_processed: vid.frames_processed,
          frame_count: vid.frame_count,
        }));
        allItems.push(...videoItems);
        totalCount += videoResponse.total;
      }

      // Sort by created_at descending
      allItems.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());

      setItems(allItems);
      setTotalItems(totalCount);
      setHasMore(allItems.length < totalCount);
      if (resetPage) setPage(1);
    } catch (err) {
      setError('Error al cargar el historial. Intenta de nuevo.');
      console.error('Error fetching history:', err);
    } finally {
      setLoading(false);
    }
  }, [activeTab, page]);

  useEffect(() => {
    fetchHistory(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  useEffect(() => {
    if (page > 1) {
      fetchHistory();
    }
  }, [page, fetchHistory]);

  // Auto-refresh for in-progress items
  useEffect(() => {
    const hasInProgress = items.some(
      item => item.status === 'pending' || item.status === 'in_progress' || item.status === 'processing'
    );

    if (hasInProgress) {
      const interval = setInterval(() => {
        fetchHistory();
      }, 5000); // Refresh every 5 seconds

      return () => clearInterval(interval);
    }
  }, [items, fetchHistory]);

  const handleDownload = async (item: HistoryItem, type: 'original' | 'enhanced') => {
    if (item.status !== 'completed') return;

    setDownloading(`${item.id}-${type}`);

    try {
      let base64: string | null = null;
      let filename: string;

      if (item.type === 'image') {
        const detail = await mediaService.getImageDetail(item.id);
        base64 = type === 'original' ? detail.image.original_base64 : detail.image.enhanced_base64;
        filename = type === 'original'
          ? item.original_filename
          : mediaService.getEnhancedFilename(item.original_filename);
      } else {
        const detail = await mediaService.getVideoDetail(item.id);
        base64 = type === 'original' ? detail.video.original_base64 : detail.video.enhanced_base64;
        filename = type === 'original'
          ? item.original_filename
          : mediaService.getEnhancedFilename(item.original_filename);
      }

      if (base64) {
        const mimeType = mediaService.getMimeType(filename);
        mediaService.downloadBase64File(base64, filename, mimeType);
      } else {
        setError('No se pudo obtener el archivo para descargar.');
      }
    } catch (err) {
      setError('Error al descargar el archivo. Intenta de nuevo.');
      console.error('Error downloading:', err);
    } finally {
      setDownloading(null);
    }
  };

  const getStatusBadge = (status: JobStatus) => {
    const statusConfig: Record<JobStatus, { label: string; className: string }> = {
      pending: { label: 'Pendiente', className: 'status-pending' },
      processing: { label: 'Procesando', className: 'status-processing' },
      in_progress: { label: 'En progreso', className: 'status-processing' },
      completed: { label: 'Completado', className: 'status-completed' },
      failed: { label: 'Error', className: 'status-error' },
      error: { label: 'Error', className: 'status-error' },
    };

    const config = statusConfig[status] || { label: status, className: 'status-pending' };
    return <span className={`status-badge ${config.className}`}>{config.label}</span>;
  };

  const getModelName = (modelType: string) => {
    const modelNames: Record<string, string> = {
      general_x4: 'General 4x',
      general_x2: 'General 2x',
      anime: 'Anime',
      anime_video: 'Anime Video',
      general_v3: 'General V3',
    };
    return modelNames[modelType] || modelType;
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const formatDimensions = (width: number | null, height: number | null) => {
    if (width === null || height === null) return '-';
    return `${width} x ${height}`;
  };

  const formatDuration = (seconds: number | undefined) => {
    if (!seconds) return '-';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const getProgress = (item: HistoryItem) => {
    if (item.type !== 'video') return null;
    if (item.status === 'completed') return 100;
    if (!item.frame_count || !item.frames_processed) return 0;
    return Math.round((item.frames_processed / item.frame_count) * 100);
  };

  return (
    <div className="page-content">
      <div className="history-page">
        <div className="history-header">
          <h1 className="history-title">Historial</h1>
          <p className="history-subtitle">
            Revisa y descarga tus archivos procesados
          </p>
        </div>

        {/* Tabs */}
        <div className="history-tabs">
          <button
            className={`history-tab ${activeTab === 'all' ? 'active' : ''}`}
            onClick={() => setActiveTab('all')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
            </svg>
            Todos
          </button>
          <button
            className={`history-tab ${activeTab === 'images' ? 'active' : ''}`}
            onClick={() => setActiveTab('images')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
              <circle cx="8.5" cy="8.5" r="1.5" />
              <polyline points="21 15 16 10 5 21" />
            </svg>
            Imagenes
          </button>
          <button
            className={`history-tab ${activeTab === 'videos' ? 'active' : ''}`}
            onClick={() => setActiveTab('videos')}
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="23 7 16 12 23 17 23 7" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
            Videos
          </button>
        </div>

        {/* Error message */}
        {error && (
          <div className="history-error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{error}</span>
            <button onClick={() => { setError(null); fetchHistory(); }}>Reintentar</button>
          </div>
        )}

        {/* Loading state */}
        {loading && items.length === 0 && (
          <div className="history-loading">
            <div className="spinner-large"></div>
            <p>Cargando historial...</p>
          </div>
        )}

        {/* Empty state */}
        {!loading && items.length === 0 && !error && (
          <div className="history-empty">
            <div className="history-empty-icon">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <polyline points="12 6 12 12 16 14" />
              </svg>
            </div>
            <h2>Historial vacio</h2>
            <p>
              {activeTab === 'all' && 'Aun no has procesado ninguna imagen o video.'}
              {activeTab === 'images' && 'Aun no has procesado ninguna imagen.'}
              {activeTab === 'videos' && 'Aun no has procesado ningun video.'}
            </p>
          </div>
        )}

        {/* History list */}
        {items.length > 0 && (
          <div className="history-list">
            <div className="history-list-header">
              <span className="col-type">Tipo</span>
              <span className="col-name">Archivo</span>
              <span className="col-filter">Filtro</span>
              <span className="col-dimensions">Original</span>
              <span className="col-dimensions">Mejorado</span>
              <span className="col-status">Estado</span>
              <span className="col-actions">Acciones</span>
            </div>

            {items.map((item) => (
              <div key={`${item.type}-${item.id}`} className="history-item">
                <div className="col-type">
                  <div className={`type-icon ${item.type}`}>
                    {item.type === 'image' ? (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                        <circle cx="8.5" cy="8.5" r="1.5" />
                        <polyline points="21 15 16 10 5 21" />
                      </svg>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <polygon points="23 7 16 12 23 17 23 7" />
                        <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
                      </svg>
                    )}
                  </div>
                </div>

                <div className="col-name">
                  <span className="filename" title={item.original_filename}>
                    {item.original_filename}
                  </span>
                  <span className="date">{formatDate(item.created_at)}</span>
                  {item.type === 'video' && item.duration_seconds && (
                    <span className="duration">Duracion: {formatDuration(item.duration_seconds)}</span>
                  )}
                </div>

                <div className="col-filter">
                  <span className="filter-badge">{getModelName(item.model_type)}</span>
                </div>

                <div className="col-dimensions">
                  <span>{formatDimensions(item.original_width, item.original_height)}</span>
                </div>

                <div className="col-dimensions">
                  <span>{formatDimensions(item.enhanced_width, item.enhanced_height)}</span>
                </div>

                <div className="col-status">
                  {getStatusBadge(item.status)}
                  {item.type === 'video' && (item.status === 'in_progress' || item.status === 'processing') && (
                    <div className="progress-bar">
                      <div
                        className="progress-fill"
                        style={{ width: `${getProgress(item)}%` }}
                      ></div>
                      <span className="progress-text">{getProgress(item)}%</span>
                    </div>
                  )}
                </div>

                <div className="col-actions">
                  <button
                    className="action-btn download-original"
                    onClick={() => handleDownload(item, 'original')}
                    disabled={item.status !== 'completed' || downloading === `${item.id}-original`}
                    title="Descargar original"
                  >
                    {downloading === `${item.id}-original` ? (
                      <span className="spinner-small"></span>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                      </svg>
                    )}
                    <span>Original</span>
                  </button>
                  <button
                    className="action-btn download-enhanced"
                    onClick={() => handleDownload(item, 'enhanced')}
                    disabled={item.status !== 'completed' || downloading === `${item.id}-enhanced`}
                    title="Descargar mejorado"
                  >
                    {downloading === `${item.id}-enhanced` ? (
                      <span className="spinner-small"></span>
                    ) : (
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4" />
                        <polyline points="7 10 12 15 17 10" />
                        <line x1="12" y1="15" x2="12" y2="3" />
                      </svg>
                    )}
                    <span>Mejorado</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Load more */}
        {hasMore && items.length > 0 && (
          <div className="history-load-more">
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={loading}
            >
              {loading ? (
                <>
                  <span className="spinner-small"></span>
                  Cargando...
                </>
              ) : (
                `Cargar mas (${items.length} de ${totalItems})`
              )}
            </button>
          </div>
        )}

        {/* Refresh hint for in-progress items */}
        {items.some(item => item.status === 'in_progress' || item.status === 'processing' || item.status === 'pending') && (
          <div className="history-refresh-hint">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="23 4 23 10 17 10" />
              <polyline points="1 20 1 14 7 14" />
              <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
            </svg>
            <span>La pagina se actualiza automaticamente mientras hay tareas en progreso</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default History;
