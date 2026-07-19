import React, { useState } from 'react';
import ButtonsShowcase from './ButtonsShowcase';
import FormsShowcase from './FormsShowcase';
import FeedbackShowcase from './FeedbackShowcase';
import LayoutsShowcase from './LayoutsShowcase';
import TablesShowcase from './TablesShowcase';
import Tabs from '../Tabs';
import PageHeader from '../PageHeader';

export const DesignSystemShowcase = () => {
  const [activeTab, setActiveTab] = useState('buttons');

  const tabsConfig = [
    { id: 'buttons', label: 'Buttons' },
    { id: 'forms', label: 'Forms & Controls' },
    { id: 'feedback', label: 'Feedback & States' },
    { id: 'layouts', label: 'Layouts & Modal' },
    { id: 'tables', label: 'Data & Tables' }
  ];

  return (
    <div className="design-system-showcase-container" style={{ padding: '24px', flex: 1, overflowY: 'auto' }}>
      <PageHeader
        title="ScaleFlow UI Design System"
        subtitle="Reusable atomic components playground built on top of centralized CSS design tokens."
      />

      <Tabs
        tabs={tabsConfig}
        activeTabId={activeTab}
        onTabChange={setActiveTab}
        style={{ marginBottom: '24px' }}
      />

      <div className="showcase-content-wrapper" style={{ marginTop: '24px' }}>
        {activeTab === 'buttons' && <ButtonsShowcase />}
        {activeTab === 'forms' && <FormsShowcase />}
        {activeTab === 'feedback' && <FeedbackShowcase />}
        {activeTab === 'layouts' && <LayoutsShowcase />}
        {activeTab === 'tables' && <TablesShowcase />}
      </div>
    </div>
  );
};
export default DesignSystemShowcase;
