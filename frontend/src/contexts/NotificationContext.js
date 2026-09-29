import React, { createContext, useState, useContext, useCallback, useEffect } from 'react';
import { apiClient } from '../services/apiClient';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
  const [showStuckWarning, setShowStuckWarning] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [activeToasts, setActiveToasts] = useState([]);

  const fetchNotifications = useCallback(async () => {
    if (document.visibilityState === 'hidden') return;
    try {
      const res = await apiClient.get('/api/v1/notifications');
      const notificationsData = res.data.notifications || [];
      setNotifications(prev => {
        if (JSON.stringify(prev) === JSON.stringify(notificationsData)) return prev;
        return notificationsData;
      });
      setUnreadCount(res.data.unread_count || 0);
    } catch (err) {
      console.error("Error fetching notifications from backend", err);
    }
  }, []);

  useEffect(() => {
    fetchNotifications();
    const interval = setInterval(fetchNotifications, 2000);
    return () => clearInterval(interval);
  }, [fetchNotifications]);

  const addNotification = useCallback(async (message, type = 'info', category = 'system') => {
    const id = Date.now() + Math.random().toString(36).substr(2, 9);
    const newNotif = {
      id,
      message,
      type,
      category,
      timestamp: new Date(),
      read: false
    };
    setNotifications(prev => [newNotif, ...prev]);
    setUnreadCount(prev => prev + 1);

    // Add side incoming toast
    setActiveToasts(prev => [...prev, { id, message, type }]);

    // Auto dismiss toast after 4s
    setTimeout(() => {
      setActiveToasts(prev => prev.filter(t => t.id !== id));
    }, 4000);
  }, []);

  const markAsRead = useCallback(async (id) => {
    try {
      await apiClient.post('/api/v1/notifications/read', { ids: [id] });
      fetchNotifications();
    } catch (err) {
      console.error("Error marking notification read", err);
    }
  }, [fetchNotifications]);

  const clearAll = useCallback(async () => {
    try {
      await apiClient.delete('/api/v1/notifications');
      setNotifications([]);
      setUnreadCount(0);
    } catch (err) {
      console.error("Error clearing notifications", err);
    }
  }, []);

  return (
    <NotificationContext.Provider value={{
      showStuckWarning,
      setShowStuckWarning,
      notifications,
      unreadCount,
      addNotification,
      markAsRead,
      clearAll,
      refresh: fetchNotifications
    }}>
      {children}
      {/* Side incoming toast notifications container */}
      <div
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 10000,
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          maxWidth: '380px',
          pointerEvents: 'none',
        }}
      >
        {activeToasts.map(toast => (
          <div
            key={toast.id}
            style={{
              pointerEvents: 'auto',
              background: toast.type === 'danger' || toast.type === 'error'
                ? '#1e1b1b'
                : toast.type === 'success'
                ? '#11221b'
                : '#0f172a',
              border: `1px solid ${
                toast.type === 'danger' || toast.type === 'error'
                  ? 'rgba(239, 68, 68, 0.4)'
                  : toast.type === 'success'
                  ? 'rgba(16, 185, 129, 0.4)'
                  : 'rgba(59, 130, 246, 0.4)'
              }`,
              borderLeft: `4px solid ${
                toast.type === 'danger' || toast.type === 'error'
                  ? '#ef4444'
                  : toast.type === 'success'
                  ? '#10b981'
                  : '#3b82f6'
              }`,
              borderRadius: '8px',
              padding: '12px 16px',
              color: '#fff',
              fontSize: '0.85rem',
              boxShadow: '0 10px 30px rgba(0,0,0,0.5)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px',
              animation: 'slideInRight 0.25s cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', lineHeight: 1.4 }}>
              <span>
                {toast.type === 'danger' || toast.type === 'error' ? '🗑️' : toast.type === 'success' ? '✅' : 'ℹ️'}
              </span>
              <span>{toast.message}</span>
            </div>
            <button
              onClick={() => setActiveToasts(prev => prev.filter(t => t.id !== toast.id))}
              style={{
                background: 'none',
                border: 'none',
                color: 'rgba(255,255,255,0.4)',
                cursor: 'pointer',
                fontSize: '12px',
                padding: '2px',
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
    </NotificationContext.Provider>
  );
};

export const useNotification = () => {
  const context = useContext(NotificationContext);
  if (!context) {
    throw new Error('useNotification must be used within a NotificationProvider');
  }
  return context;
};
