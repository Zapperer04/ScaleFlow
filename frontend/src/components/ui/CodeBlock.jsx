import React from 'react';

/**
 * Reusable CodeBlock component.
 * 
 * @param {Object} props
 * @param {string} props.code - The code string text or logs
 * @param {string} [props.language] - Text syntax highlighting type (e.g. json, python)
 * @param {string} [props.className=''] - Custom overrides
 */
export const CodeBlock = ({
  code,
  language,
  className = '',
  ...rest
}) => {
  return (
    <pre className={`code-block-container text-code ${className}`.trim()} {...rest}>
      <code>{code}</code>
    </pre>
  );
};
export default CodeBlock;
