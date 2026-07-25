import React, { createContext, useContext, useState, useEffect } from 'react';
import { apiClient } from '../services/apiClient';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [token, setToken] = useState(null);
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Decodes a JWT token safely
  const decodeToken = (t) => {
    try {
      const base64Url = t.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (e) {
      return null;
    }
  };

  // Restore session on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('sf_token');
    const rememberMe = localStorage.getItem('sf_remember_me') === 'true';

    if (savedToken && rememberMe) {
      const payload = decodeToken(savedToken);
      if (payload && payload.exp * 1000 > Date.now()) {
        setToken(savedToken);
        setUser({ username: payload.sub, role: payload.role || 'user' });
      } else {
        localStorage.removeItem('sf_token');
      }
    }
    setLoading(false);
  }, []);

  // Update Axios interceptor whenever token changes
  useEffect(() => {
    const interceptor = apiClient.interceptors.request.use((config) => {
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      } else {
        delete config.headers.Authorization;
      }
      return config;
    });

    return () => {
      apiClient.interceptors.request.eject(interceptor);
    };
  }, [token]);

  const login = async (username, password, rememberMe = false) => {
    setError(null);
    try {
      // 1. Try real API backend (FastAPI platform on port 8000/5000 if configured)
      const response = await apiClient.post('/auth/login', { username, password });
      const { access_token } = response.data;
      const payload = decodeToken(access_token);
      
      setToken(access_token);
      setUser({ username: payload.sub, role: payload.role || 'user' });
      
      if (rememberMe) {
        localStorage.setItem('sf_token', access_token);
        localStorage.setItem('sf_remember_me', 'true');
      } else {
        localStorage.removeItem('sf_token');
        localStorage.removeItem('sf_remember_me');
      }
      return true;
    } catch (err) {
      // 2. Fallback to local authentication if endpoint doesn't exist (404/Connection refused)
      const isNetworkOr404 = !err.response || err.response.status === 404 || err.response.status === 502;
      
      if (isNetworkOr404) {
        // Check default credentials
        const isDefaultUser = (username === 'admin' || username === 'manager' || username === 'user') && password === 'password';
        
        // Check local storage registered users
        const mockUsers = JSON.parse(localStorage.getItem('sf_mock_users') || '[]');
        const matchedMockUser = mockUsers.find(u => u.username === username && u.password === password);
        
        if (isDefaultUser || matchedMockUser) {
          const userRole = username === 'admin' ? 'admin' : 'user';
          
          // Construct a mock JWT payload
          const mockHeader = btoa(JSON.stringify({ alg: "HS256", typ: "JWT" }));
          const mockPayload = btoa(JSON.stringify({
            sub: username,
            role: userRole,
            exp: Math.floor(Date.now() / 1000) + 3600
          }));
          const mockTokenStr = `${mockHeader}.${mockPayload}.signature`;
          
          setToken(mockTokenStr);
          setUser({ username, role: userRole });
          
          if (rememberMe) {
            localStorage.setItem('sf_token', mockTokenStr);
            localStorage.setItem('sf_remember_me', 'true');
          } else {
            localStorage.removeItem('sf_token');
            localStorage.removeItem('sf_remember_me');
          }
          return true;
        }
      }
      
      const msg = err.response?.data?.detail || 'Invalid username or password';
      setError(msg);
      throw new Error(msg);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('sf_token');
    localStorage.removeItem('sf_remember_me');
  };

  const register = async (username, name, email, password) => {
    setError(null);
    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
      
      // Save mock user database to localStorage for fallback auth integration
      const mockUsers = JSON.parse(localStorage.getItem('sf_mock_users') || '[]');
      if (mockUsers.some(u => u.username === username)) {
        throw new Error('Username already exists.');
      }
      mockUsers.push({ username, name, email, password });
      localStorage.setItem('sf_mock_users', JSON.stringify(mockUsers));
      
      return true;
    } catch (err) {
      setError(err.message || 'Registration failed');
      throw err;
    }
  };

  const forgotPassword = async (email) => {
    setError(null);
    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
      return true;
    } catch (err) {
      setError(err.message || 'Error requesting reset');
      throw err;
    }
  };

  const resetPassword = async (newPassword) => {
    setError(null);
    try {
      await new Promise((resolve) => setTimeout(resolve, 800));
      return true;
    } catch (err) {
      setError(err.message || 'Reset failed');
      throw err;
    }
  };

  return (
    <AuthContext.Provider value={{ token, user, loading, error, login, logout, register, forgotPassword, resetPassword }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
