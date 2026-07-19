import React, { createContext, useState, useContext, useCallback } from 'react';

const WorkspaceContext = createContext(null);

export const WorkspaceProvider = ({ children }) => {
  const [selectedDocId, setSelectedDocId] = useState(null);
  const [activeTab, setActiveTab] = useState('overview');
  const [expandedPanelId, setExpandedPanelId] = useState(null);
  const [layoutPreference, setLayoutPreference] = useState('grid');

  const selectDocument = useCallback((docId) => {
    setSelectedDocId(docId);
  }, []);

  const changeTab = useCallback((tabId) => {
    setActiveTab(tabId);
  }, []);

  const togglePanel = useCallback((panelId) => {
    setExpandedPanelId(prev => (prev === panelId ? null : panelId));
  }, []);

  return (
    <WorkspaceContext.Provider value={{
      selectedDocId,
      selectDocument,
      activeTab,
      changeTab,
      expandedPanelId,
      togglePanel,
      layoutPreference,
      setLayoutPreference
    }}>
      {children}
    </WorkspaceContext.Provider>
  );
};

export const useWorkspace = () => {
  const context = useContext(WorkspaceContext);
  if (!context) {
    throw new Error('useWorkspace must be used within a WorkspaceProvider');
  }
  return context;
};
export default WorkspaceContext;
