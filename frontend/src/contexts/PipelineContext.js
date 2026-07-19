import React, { createContext, useState, useContext } from 'react';

const PipelineContext = createContext(null);

export const PipelineProvider = ({ children }) => {
  const [selectedPipelineId, setSelectedPipelineId] = useState(null);
  const [pipelines, setPipelines] = useState([]);
  const [selectedTaskId, setSelectedTaskId] = useState(null);
  const [testing, setTesting] = useState(false);
  const [showTestModal, setShowTestModal] = useState(false);
  const [testResults, setTestResults] = useState(null);

  return (
    <PipelineContext.Provider value={{
      selectedPipelineId,
      setSelectedPipelineId,
      pipelines,
      setPipelines,
      selectedTaskId,
      setSelectedTaskId,
      testing,
      setTesting,
      showTestModal,
      setShowTestModal,
      testResults,
      setTestResults
    }}>
      {children}
    </PipelineContext.Provider>
  );
};

export const usePipeline = () => {
  const context = useContext(PipelineContext);
  if (!context) {
    throw new Error('usePipeline must be used within a PipelineProvider');
  }
  return context;
};
