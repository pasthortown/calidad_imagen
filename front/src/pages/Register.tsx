import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { AxiosError } from 'axios';
import '../styles/auth.css';

interface FormErrors {
  username?: string;
  email?: string;
  password?: string;
  confirmPassword?: string;
}

const Register: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  const validatePassword = (pwd: string): string | null => {
    if (!pwd || pwd.trim() === '') {
      return 'La contraseña no puede estar vacía';
    }
    if (pwd.length < 8) {
      return 'La contraseña debe tener al menos 8 caracteres';
    }
    if (!/[a-z]/.test(pwd)) {
      return 'La contraseña debe contener al menos una letra minúscula';
    }
    if (!/[A-Z]/.test(pwd)) {
      return 'La contraseña debe contener al menos una letra mayúscula';
    }
    if (!/[0-9]/.test(pwd)) {
      return 'La contraseña debe contener al menos un número';
    }
    return null;
  };

  const validateEmail = (emailValue: string): string | null => {
    if (!emailValue) {
      return 'El email es requerido';
    }
    // Regex más completa para validar email
    const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!emailRegex.test(emailValue)) {
      return 'Ingresa un correo electrónico válido';
    }
    return null;
  };

  const validateForm = (): boolean => {
    const errors: FormErrors = {};

    // Validar username
    if (!username) {
      errors.username = 'El nombre de usuario es requerido';
    } else if (username.length < 3) {
      errors.username = 'Mínimo 3 caracteres';
    } else if (username.length > 30) {
      errors.username = 'Máximo 30 caracteres';
    } else if (!/^[a-zA-Z0-9_]+$/.test(username)) {
      errors.username = 'Solo letras, números y guión bajo';
    }

    // Validar email
    const emailError = validateEmail(email);
    if (emailError) {
      errors.email = emailError;
    }

    // Validar password
    const passwordError = validatePassword(password);
    if (passwordError) {
      errors.password = passwordError;
    }

    // Validar confirmación de contraseña
    if (!confirmPassword || confirmPassword.trim() === '') {
      errors.confirmPassword = 'Debes confirmar tu contraseña';
    } else if (password !== confirmPassword) {
      errors.confirmPassword = 'Las contraseñas no coinciden';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      return;
    }

    setIsLoading(true);

    try {
      await register({ username, email, password });
      navigate('/login', { state: { registered: true } });
    } catch (err) {
      const axiosError = err as AxiosError<{ error?: string; detail?: string }>;
      const message =
        axiosError.response?.data?.error ||
        axiosError.response?.data?.detail ||
        'Error al crear la cuenta. Intenta de nuevo.';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const clearFieldError = (field: keyof FormErrors) => {
    if (formErrors[field]) {
      setFormErrors((prev) => ({ ...prev, [field]: undefined }));
    }
  };

  return (
    <div className="auth-container">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M15 8h.01M12 3l9 4.5v9L12 21l-9-4.5v-9L12 3z" />
              <path d="M12 12l4.5-2.5" />
              <path d="M12 12v5" />
              <path d="M12 12L7.5 9.5" />
            </svg>
          </div>
          <h1 className="auth-title">Crear cuenta</h1>
          <p className="auth-subtitle">Regístrate para comenzar</p>
        </div>

        {error && (
          <div className="alert alert-error">
            <svg className="alert-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label" htmlFor="username">
              Nombre de usuario
            </label>
            <input
              id="username"
              type="text"
              className={`form-input ${formErrors.username ? 'error' : ''}`}
              placeholder="usuario123"
              value={username}
              onChange={(e) => {
                setUsername(e.target.value);
                clearFieldError('username');
              }}
              disabled={isLoading}
              autoComplete="username"
            />
            {formErrors.username && <span className="form-error">{formErrors.username}</span>}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="email">
              Correo electrónico
            </label>
            <input
              id="email"
              type="email"
              className={`form-input ${formErrors.email ? 'error' : ''}`}
              placeholder="tu@email.com"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                clearFieldError('email');
              }}
              disabled={isLoading}
              autoComplete="email"
            />
            {formErrors.email && <span className="form-error">{formErrors.email}</span>}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="password">
              Contraseña
            </label>
            <div className="input-wrapper">
              <input
                id="password"
                type={showPassword ? 'text' : 'password'}
                className={`form-input ${formErrors.password ? 'error' : ''}`}
                placeholder="••••••••"
                value={password}
                onChange={(e) => {
                  setPassword(e.target.value);
                  clearFieldError('password');
                }}
                disabled={isLoading}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowPassword(!showPassword)}
                tabIndex={-1}
              >
                {showPassword ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
            {formErrors.password && <span className="form-error">{formErrors.password}</span>}

            {/* Password requirements indicator */}
            {password.length > 0 && (
              <div className="password-requirements">
                <div className="password-requirements-title">La contraseña debe contener:</div>
                <div className={`password-requirement ${password.length >= 8 ? 'valid' : 'invalid'}`}>
                  <svg className={`requirement-icon ${password.length >= 8 ? 'valid' : 'invalid'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    {password.length >= 8 ? (
                      <polyline points="20 6 9 17 4 12" />
                    ) : (
                      <circle cx="12" cy="12" r="10" />
                    )}
                  </svg>
                  <span>Al menos 8 caracteres</span>
                </div>
                <div className={`password-requirement ${/[a-z]/.test(password) ? 'valid' : 'invalid'}`}>
                  <svg className={`requirement-icon ${/[a-z]/.test(password) ? 'valid' : 'invalid'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    {/[a-z]/.test(password) ? (
                      <polyline points="20 6 9 17 4 12" />
                    ) : (
                      <circle cx="12" cy="12" r="10" />
                    )}
                  </svg>
                  <span>Una letra minúscula</span>
                </div>
                <div className={`password-requirement ${/[A-Z]/.test(password) ? 'valid' : 'invalid'}`}>
                  <svg className={`requirement-icon ${/[A-Z]/.test(password) ? 'valid' : 'invalid'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    {/[A-Z]/.test(password) ? (
                      <polyline points="20 6 9 17 4 12" />
                    ) : (
                      <circle cx="12" cy="12" r="10" />
                    )}
                  </svg>
                  <span>Una letra mayúscula</span>
                </div>
                <div className={`password-requirement ${/[0-9]/.test(password) ? 'valid' : 'invalid'}`}>
                  <svg className={`requirement-icon ${/[0-9]/.test(password) ? 'valid' : 'invalid'}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    {/[0-9]/.test(password) ? (
                      <polyline points="20 6 9 17 4 12" />
                    ) : (
                      <circle cx="12" cy="12" r="10" />
                    )}
                  </svg>
                  <span>Un número</span>
                </div>
              </div>
            )}
          </div>

          <div className="form-group">
            <label className="form-label" htmlFor="confirmPassword">
              Confirmar contraseña
            </label>
            <div className="input-wrapper">
              <input
                id="confirmPassword"
                type={showConfirmPassword ? 'text' : 'password'}
                className={`form-input ${formErrors.confirmPassword ? 'error' : ''}`}
                placeholder="••••••••"
                value={confirmPassword}
                onChange={(e) => {
                  setConfirmPassword(e.target.value);
                  clearFieldError('confirmPassword');
                }}
                disabled={isLoading}
                autoComplete="new-password"
              />
              <button
                type="button"
                className="password-toggle"
                onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                tabIndex={-1}
              >
                {showConfirmPassword ? (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0112 20c-7 0-11-8-11-8a18.45 18.45 0 015.06-5.94M9.9 4.24A9.12 9.12 0 0112 4c7 0 11 8 11 8a18.5 18.5 0 01-2.16 3.19m-6.72-1.07a3 3 0 11-4.24-4.24" />
                    <line x1="1" y1="1" x2="23" y2="23" />
                  </svg>
                ) : (
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
                    <circle cx="12" cy="12" r="3" />
                  </svg>
                )}
              </button>
            </div>
            {formErrors.confirmPassword && <span className="form-error">{formErrors.confirmPassword}</span>}
          </div>

          <button type="submit" className={`auth-button ${isLoading ? 'loading' : ''}`} disabled={isLoading}>
            {isLoading ? <span className="spinner" /> : 'Crear cuenta'}
          </button>
        </form>

        <div className="auth-footer">
          <p className="auth-footer-text">
            ¿Ya tienes una cuenta?{' '}
            <Link to="/login" className="auth-link">
              Inicia sesión
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;
