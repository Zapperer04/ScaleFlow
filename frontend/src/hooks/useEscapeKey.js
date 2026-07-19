import { useEffect } from 'react';

/**
 * Executes a callback when the Escape key is pressed.
 * 
 * @param {Function} callback - Callback trigger
 * @param {boolean} active - Active state selector
 */
export const useEscapeKey = (callback, active = true) => {
  useEffect(() => {
    if (!active || !callback) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        callback();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [callback, active]);
};
export default useEscapeKey;
