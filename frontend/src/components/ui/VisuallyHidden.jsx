import React from 'react';

/**
 * Primitives helper to visually hide text for screen reader compliance.
 */
export const VisuallyHidden = ({ children, ...rest }) => {
  return (
    <span
      style={{
        position: 'absolute',
        width: '1px',
        height: '1px',
        padding: '0',
        margin: '-1px',
        overflow: 'hidden',
        clip: 'rect(0, 0, 0, 0)',
        border: '0',
        whiteSpace: 'nowrap'
      }}
      {...rest}
    >
      {children}
    </span>
  );
};

export default VisuallyHidden;
