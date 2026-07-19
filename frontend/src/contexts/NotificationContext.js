import React, { createContext, useState, useContext, useCallback } from 'react';

const NotificationContext = createContext(null);

export const NotificationProvider = ({ children }) => {
  const [showStuckWarning, setShowStuckWarning] = useState(false);
  const [notifications, setNotifications] = useState([]);

  const addNotification = useCallback((message, type = 'info', category = 'system') => {
    const newNotif = {
      id: Date.now() + Math.random().toString(36).substr(2, 9),
      message,
      type, // 'success', 'warning', 'danger', 'info'
      category, // 'system', 'pipeline', 'worker'
      timestamp: new Date(),
      read: false
    };
    setNotifications(prev => [newNotif, ...prev]);
  }, []);

  const markAsRead = useCallback((id) => {
    setNotifications(prev =>
      prev.map(n => (n.id === id ? { ...n, read: true } : n))
    );
  }, []);

  const clearAll = useCallback(() => {
    setNotifications([]);
  }, []);

  return (
    <NotificationContext.Provider value={{
      showStuckWarning,
      setShowStuckWarning,
      notifications,
      addNotification,
      markAsRead,
      clearAll
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
