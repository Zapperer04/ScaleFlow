import { useEffect, useRef } from 'react';

/**
 * Traps focus within a DOM element when active.
 * 
 * @param {boolean} active - Active state selector
 * @returns {React.RefObject} - Element container ref
 */
export const useFocusTrap = (active) => {
  const containerRef = useRef(null);

  useEffect(() => {
    if (!active) return;

    const container = containerRef.current;
    if (!container) return;

    // Get all focusable elements
    const focusableSelector = 'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';
    
    const handleKeyDown = (e) => {
      if (e.key !== 'Tab') return;

      const focusables = Array.from(container.querySelectorAll(focusableSelector));
      if (focusables.length === 0) return;

      const firstElement = focusables[0];
      const lastElement = focusables[focusables.length - 1];

      if (e.shiftKey) {
        // Shift + Tab: loop back to end
        if (document.activeElement === firstElement) {
          lastElement.focus();
          e.preventDefault();
        }
      } else {
        // Tab: loop to start
        if (document.activeElement === lastElement) {
          firstElement.focus();
          e.preventDefault();
        }
      }
    };

    // Auto-focus the first element inside the trap
    const focusables = Array.from(container.querySelectorAll(focusableSelector));
    if (focusables.length > 0) {
      focusables[0].focus();
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [active]);

  return containerRef;
};
export default useFocusTrap;
