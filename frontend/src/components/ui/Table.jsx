import React from 'react';

/**
 * Reusable Table component.
 * 
 * @param {Object} props
 * @param {Array<string | {label: string, key: string}>} props.headers - Column definitions
 * @param {string} [props.className=''] - Custom overrides
 * @param {React.ReactNode} props.children - Table body rows contents
 */
export const Table = ({
  headers = [],
  className = '',
  children,
  ...rest
}) => {
  return (
    <div className={`table-container ${className}`.trim()} {...rest}>
      <table className="table-custom">
        <thead>
          <tr>
            {headers.map((header, idx) => {
              const label = typeof header === 'string' ? header : header.label;
              return <th key={idx}>{label}</th>;
            })}
          </tr>
        </thead>
        <tbody>
          {children}
        </tbody>
      </table>
    </div>
  );
};
export default Table;
