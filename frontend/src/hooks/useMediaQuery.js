import { useState, useEffect } from 'react';

/**
 * Returns whether a CSS media query matches the screen viewport width.
 * 
 * @param {string} query - CSS Media query string (e.g. '(max-width: 768px)')
 * @returns {boolean} - Matches state indicator
 */
export const useMediaQuery = (query) => {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return;
    }

    const media = window.matchMedia(query);
    if (media.matches !== matches) {
      setMatches(media.matches);
    }

    const listener = () => setMatches(media.matches);
    media.addEventListener('change', listener);
    return () => media.removeEventListener('change', listener);
  }, [matches, query]);

  return matches;
};
export default useMediaQuery;
