import { useEffect, useRef } from 'react';
import useFocusTrap from './useFocusTrap';
import useEscapeKey from './useEscapeKey';

/**
 * Composite hook to handle dialog focus trapping, escape key closures, and focus restoration.
 * 
 * @param {Object} config
 * @param {boolean} config.open - Active state selector
 * @param {Function} config.onClose - Action triggered when dialog closes
 * @returns {React.RefObject} - Element container ref
 */
export const useDialog = ({ open, onClose }) => {
  const containerRef = useFocusTrap(open);
  const previouslyFocusedElementRef = useRef(null);

  useEscapeKey(onClose, open);

  useEffect(() => {
    if (open) {
      // Store currently focused element
      previouslyFocusedElementRef.current = document.activeElement;
    } else {
      // Restore focus upon overlay closure
      if (previouslyFocusedElementRef.current && typeof previouslyFocusedElementRef.current.focus === 'function') {
        previouslyFocusedElementRef.current.focus();
      }
    }
  }, [open]);

  return containerRef;
};

export default useDialog;
