/**
 * Infinite scroll container component with intersection observer
 * Provides infinite scroll functionality with loading states, error boundaries,
 * and accessibility support for screen readers
 */

import { useEffect, useRef, useCallback, type ReactNode } from 'react';

/**
 * Props for the InfiniteScroll component
 */
export interface InfiniteScrollProps {
  /** Child elements to render */
  children: ReactNode;
  /** Callback to load more items */
  onLoadMore: () => void | Promise<void>;
  /** Whether more items are available to load */
  hasMore: boolean;
  /** Whether items are currently loading */
  isLoading: boolean;
  /** Error that occurred during loading */
  error?: Error | null;
  /** Custom loading component */
  loadingComponent?: ReactNode;
  /** Custom error component */
  errorComponent?: ReactNode;
  /** Custom end of list component */
  endComponent?: ReactNode;
  /** Root margin for intersection observer (default: '100px') */
  rootMargin?: string;
  /** Intersection threshold (default: 0.1) */
  threshold?: number;
  /** Additional CSS classes */
  className?: string;
  /** ARIA label for the scroll container */
  ariaLabel?: string;
  /** Callback when scroll position changes */
  onScrollPositionChange?: (position: number) => void;
  /** Whether to enable scroll restoration */
  enableScrollRestoration?: boolean;
  /** Unique identifier for scroll restoration */
  scrollRestorationKey?: string;
}

/**
 * Default loading skeleton component
 */
function DefaultLoadingComponent(): JSX.Element {
  return (
    <div
      className="flex items-center justify-center py-8"
      role="status"
      aria-live="polite"
      aria-label="Loading more items"
    >
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-300 border-t-blue-600" />
        <span className="text-sm text-gray-600">Loading more vehicles...</span>
      </div>
    </div>
  );
}

/**
 * Default error component
 */
function DefaultErrorComponent({ error }: { error: Error }): JSX.Element {
  return (
    <div
      className="flex items-center justify-center py-8"
      role="alert"
      aria-live="assertive"
    >
      <div className="flex flex-col items-center gap-4 text-center">
        <div className="rounded-full bg-red-100 p-3">
          <svg
            className="h-6 w-6 text-red-600"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900">
            Failed to load more items
          </h3>
          <p className="mt-1 text-sm text-gray-600">{error.message}</p>
        </div>
      </div>
    </div>
  );
}

/**
 * Default end of list component
 */
function DefaultEndComponent(): JSX.Element {
  return (
    <div
      className="flex items-center justify-center py-8"
      role="status"
      aria-live="polite"
    >
      <div className="text-center">
        <p className="text-sm text-gray-600">You've reached the end of the list</p>
      </div>
    </div>
  );
}

/**
 * InfiniteScroll component
 * Implements infinite scroll with intersection observer API
 */
export default function InfiniteScroll({
  children,
  onLoadMore,
  hasMore,
  isLoading,
  error = null,
  loadingComponent,
  errorComponent,
  endComponent,
  rootMargin = '100px',
  threshold = 0.1,
  className = '',
  ariaLabel = 'Scrollable content',
  onScrollPositionChange,
  enableScrollRestoration = false,
  scrollRestorationKey,
}: InfiniteScrollProps): JSX.Element {
  const observerTarget = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const isLoadingRef = useRef(false);
  const scrollPositionKey = scrollRestorationKey ?? 'infinite-scroll-position';

  /**
   * Save scroll position to session storage
   */
  const saveScrollPosition = useCallback(() => {
    if (!enableScrollRestoration || !containerRef.current) return;

    try {
      const position = containerRef.current.scrollTop;
      sessionStorage.setItem(scrollPositionKey, position.toString());
    } catch (err) {
      console.error('Failed to save scroll position:', err);
    }
  }, [enableScrollRestoration, scrollPositionKey]);

  /**
   * Restore scroll position from session storage
   */
  const restoreScrollPosition = useCallback(() => {
    if (!enableScrollRestoration || !containerRef.current) return;

    try {
      const savedPosition = sessionStorage.getItem(scrollPositionKey);
      if (savedPosition) {
        const position = parseInt(savedPosition, 10);
        if (!isNaN(position)) {
          containerRef.current.scrollTop = position;
        }
      }
    } catch (err) {
      console.error('Failed to restore scroll position:', err);
    }
  }, [enableScrollRestoration, scrollPositionKey]);

  /**
   * Handle scroll position changes
   */
  const handleScroll = useCallback(() => {
    if (!containerRef.current || !onScrollPositionChange) return;

    const position = containerRef.current.scrollTop;
    onScrollPositionChange(position);
    saveScrollPosition();
  }, [onScrollPositionChange, saveScrollPosition]);

  /**
   * Load more items with debouncing
   */
  const loadMore = useCallback(async () => {
    if (isLoadingRef.current || !hasMore || isLoading) {
      return;
    }

    isLoadingRef.current = true;

    try {
      await onLoadMore();
    } catch (err) {
      console.error('Error loading more items:', err);
    } finally {
      isLoadingRef.current = false;
    }
  }, [hasMore, isLoading, onLoadMore]);

  /**
   * Set up intersection observer
   */
  useEffect(() => {
    const target = observerTarget.current;
    if (!target) return;

    const options: IntersectionObserverInit = {
      root: null,
      rootMargin,
      threshold,
    };

    const observer = new IntersectionObserver((entries) => {
      const [entry] = entries;

      if (entry?.isIntersecting && hasMore && !isLoading && !error) {
        void loadMore();
      }
    }, options);

    observer.observe(target);

    return () => {
      observer.disconnect();
    };
  }, [hasMore, isLoading, error, loadMore, rootMargin, threshold]);

  /**
   * Restore scroll position on mount
   */
  useEffect(() => {
    restoreScrollPosition();
  }, [restoreScrollPosition]);

  /**
   * Add scroll event listener
   */
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    container.addEventListener('scroll', handleScroll, { passive: true });

    return () => {
      container.removeEventListener('scroll', handleScroll);
    };
  }, [handleScroll]);

  /**
   * Announce loading state to screen readers
   */
  useEffect(() => {
    if (isLoading) {
      const announcement = document.createElement('div');
      announcement.setAttribute('role', 'status');
      announcement.setAttribute('aria-live', 'polite');
      announcement.className = 'sr-only';
      announcement.textContent = 'Loading more items';
      document.body.appendChild(announcement);

      return () => {
        document.body.removeChild(announcement);
      };
    }
  }, [isLoading]);

  return (
    <div
      ref={containerRef}
      className={`relative overflow-y-auto ${className}`}
      role="region"
      aria-label={ariaLabel}
      aria-busy={isLoading}
    >
      {children}

      {/* Intersection observer target */}
      <div
        ref={observerTarget}
        className="h-px w-full"
        aria-hidden="true"
        data-testid="infinite-scroll-trigger"
      />

      {/* Loading state */}
      {isLoading && (
        <div data-testid="infinite-scroll-loading">
          {loadingComponent ?? <DefaultLoadingComponent />}
        </div>
      )}

      {/* Error state */}
      {error && !isLoading && (
        <div data-testid="infinite-scroll-error">
          {errorComponent ?? <DefaultErrorComponent error={error} />}
        </div>
      )}

      {/* End of list */}
      {!hasMore && !isLoading && !error && (
        <div data-testid="infinite-scroll-end">
          {endComponent ?? <DefaultEndComponent />}
        </div>
      )}

      {/* Screen reader announcements */}
      <div className="sr-only" role="status" aria-live="polite" aria-atomic="true">
        {isLoading && 'Loading more items'}
        {error && `Error: ${error.message}`}
        {!hasMore && !isLoading && 'End of list reached'}
      </div>
    </div>
  );
}