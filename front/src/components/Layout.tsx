import React, { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import { useAuth } from '../context/AuthContext';
import '../styles/layout.css';

const Layout: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { user } = useAuth();

  const getInitial = (username: string | undefined): string => {
    return username ? username.charAt(0).toUpperCase() : '?';
  };

  return (
    <div className="layout">
      <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Mobile Header */}
      <header className="mobile-header">
        <button className="menu-toggle" onClick={() => setSidebarOpen(true)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
        <div className="mobile-logo">
          <div className="mobile-logo-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 8h.01M12 3l9 4.5v9L12 21l-9-4.5v-9L12 3z" />
              <path d="M12 12l4.5-2.5" />
              <path d="M12 12v5" />
              <path d="M12 12L7.5 9.5" />
            </svg>
          </div>
          <span className="mobile-logo-text">Image Enhancer</span>
        </div>
        <div className="mobile-avatar">
          {getInitial(user?.username)}
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  );
};

export default Layout;
