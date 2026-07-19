import React from 'react';
import Input from './Input';

/**
 * Reusable SearchInput component for filters and search queries.
 * 
 * @param {Object} props
 * @param {string} [props.placeholder='Search...'] - Field placeholder
 * @param {string} [props.className=''] - Custom class overrides
 * @param {Function} [props.onChange] - Change handler
 */
export const SearchInput = ({
  placeholder = 'Search...',
  className = '',
  onChange,
  ...rest
}) => {
  return (
    <div className={`search-input-wrapper ${className}`.trim()}>
      <span className="search-icon-adornment" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ width: '14px', height: '14px' }}>
          <circle cx="11" cy="11" r="8" />
          <path d="M21 21l-4.35-4.35" />
        </svg>
      </span>
      <Input
        type="search"
        placeholder={placeholder}
        onChange={onChange}
        className="search-input-field"
        {...rest}
      />
    </div>
  );
};
export default SearchInput;
