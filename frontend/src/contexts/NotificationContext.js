import React, { createContext, useState, useContext, useCallback, useEffect } from 'react';
import { apiClient } from '../services/apiClient';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
  const [showStuckWarning, setShowStuckWarning] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);

  const fetchNotifications = useCallback(async () => {
    if (document.visibilityState === 'hidden') return;
    try {
      const res = await apiClient.get('/api/v1/notifications');
      setNotifications(res.data.notifications || []);
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
    // Add locally and post to mock backend insert if needed, or rely on backend events
    const newNotif = {
      id: Date.now() + Math.random().toString(36).substr(2, 9),
      message,
      type,
      category,
      timestamp: new Date(),
      read: false
    };
    setNotifications(prev => [newNotif, ...prev]);
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
