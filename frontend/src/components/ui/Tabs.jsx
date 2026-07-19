import React from 'react';

/**
 * Reusable Tabs component.
 * 
 * @param {Object} props
 * @param {Array<{id: string, label: string}>} props.tabs - Tab config list
 * @param {string} props.activeTabId - Active key selection
 * @param {Function} props.onTabChange - Selection click action
 * @param {string} [props.className=''] - Custom overrides
 */
export const Tabs = ({
  tabs = [],
  activeTabId,
  onTabChange,
  className = '',
  ...rest
}) => {
  return (
    <div className={`tabs-bar-navigation ${className}`.trim()} {...rest}>
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        const activeClass = isActive ? 'tab-active' : '';
        
        return (
          <button
            key={tab.id}
            className={`tab-nav-btn ${activeClass}`}
            onClick={() => onTabChange(tab.id)}
            role="tab"
            aria-selected={isActive}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
};
export default Tabs;
