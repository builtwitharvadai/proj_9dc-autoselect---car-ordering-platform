import { useState, useEffect } from 'react';
import { Link, useLocation } from 'react-router-dom';

interface NavigationLink {
  readonly label: string;
  readonly path: string;
  readonly ariaLabel: string;
}

const NAVIGATION_LINKS: readonly NavigationLink[] = [
  { label: 'Home', path: '/', ariaLabel: 'Navigate to home page' },
  { label: 'Browse', path: '/browse', ariaLabel: 'Browse available vehicles' },
  { label: 'About', path: '/about', ariaLabel: 'Learn about AutoSelect' },
  { label: 'Contact', path: '/contact', ariaLabel: 'Contact us' },
] as const;

interface HeaderProps {
  readonly className?: string;
}

export default function Header({ className = '' }: HeaderProps): JSX.Element {
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState<boolean>(false);
  const [isScrolled, setIsScrolled] = useState<boolean>(false);
  const location = useLocation();

  useEffect(() => {
    const handleScroll = (): void => {
      const scrollPosition = window.scrollY;
      setIsScrolled(scrollPosition > 10);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (isMobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }

    return () => {
      document.body.style.overflow = '';
    };
  }, [isMobileMenuOpen]);

  const toggleMobileMenu = (): void => {
    setIsMobileMenuOpen((prev) => !prev);
  };

  const handleKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>): void => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      toggleMobileMenu();
    }
  };

  const isActivePath = (path: string): boolean => {
    return location.pathname === path;
  };

  return (
    <header
      className={`fixed top-0 left-0 right-0 z-[var(--z-fixed)] transition-all duration-[var(--transition-base)] ${
        isScrolled
          ? 'bg-white/95 backdrop-blur-sm shadow-[var(--shadow-md)]'
          : 'bg-white'
      } ${className}`}
      role="banner"
    >
      <nav
        className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8"
        role="navigation"
        aria-label="Main navigation"
      >
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center">
            <Link
              to="/"
              className="flex items-center space-x-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))] rounded-[var(--radius-md)]"
              aria-label="AutoSelect home"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-[var(--radius-lg)] bg-[rgb(var(--color-primary-600))]">
                <span className="text-xl font-bold text-white" aria-hidden="true">
                  A
                </span>
              </div>
              <span className="text-xl font-bold text-[rgb(var(--color-gray-900))]">
                AutoSelect
              </span>
            </Link>
          </div>

          <div className="hidden md:block">
            <ul className="flex items-center space-x-1" role="list">
              {NAVIGATION_LINKS.map((link) => {
                const isActive = isActivePath(link.path);
                return (
                  <li key={link.path}>
                    <Link
                      to={link.path}
                      className={`inline-flex items-center px-4 py-2 text-sm font-medium rounded-[var(--radius-md)] transition-colors duration-[var(--transition-fast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))] ${
                        isActive
                          ? 'bg-[rgb(var(--color-primary-50))] text-[rgb(var(--color-primary-700))]'
                          : 'text-[rgb(var(--color-gray-700))] hover:bg-[rgb(var(--color-gray-100))] hover:text-[rgb(var(--color-gray-900))]'
                      }`}
                      aria-label={link.ariaLabel}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      {link.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </div>

          <div className="hidden md:flex md:items-center md:space-x-4">
            <Link
              to="/login"
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-[rgb(var(--color-gray-700))] hover:text-[rgb(var(--color-gray-900))] rounded-[var(--radius-md)] transition-colors duration-[var(--transition-fast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
              aria-label="Sign in to your account"
            >
              Sign In
            </Link>
            <Link
              to="/signup"
              className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-[rgb(var(--color-primary-600))] hover:bg-[rgb(var(--color-primary-700))] rounded-[var(--radius-md)] shadow-[var(--shadow-sm)] transition-colors duration-[var(--transition-fast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
              aria-label="Create a new account"
            >
              Get Started
            </Link>
          </div>

          <div className="flex md:hidden">
            <button
              type="button"
              className="inline-flex items-center justify-center p-2 rounded-[var(--radius-md)] text-[rgb(var(--color-gray-700))] hover:bg-[rgb(var(--color-gray-100))] hover:text-[rgb(var(--color-gray-900))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))] transition-colors duration-[var(--transition-fast)]"
              onClick={toggleMobileMenu}
              onKeyDown={handleKeyDown}
              aria-expanded={isMobileMenuOpen}
              aria-controls="mobile-menu"
              aria-label={isMobileMenuOpen ? 'Close menu' : 'Open menu'}
            >
              <span className="sr-only">
                {isMobileMenuOpen ? 'Close menu' : 'Open menu'}
              </span>
              {isMobileMenuOpen ? (
                <svg
                  className="h-6 w-6"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              ) : (
                <svg
                  className="h-6 w-6"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 6h16M4 12h16M4 18h16"
                  />
                </svg>
              )}
            </button>
          </div>
        </div>
      </nav>

      {isMobileMenuOpen && (
        <>
          <div
            className="fixed inset-0 z-[var(--z-modal-backdrop)] bg-black/50 backdrop-blur-sm md:hidden"
            onClick={toggleMobileMenu}
            aria-hidden="true"
          />
          <div
            id="mobile-menu"
            className="fixed inset-y-0 right-0 z-[var(--z-modal)] w-full max-w-sm bg-white shadow-[var(--shadow-xl)] md:hidden"
            role="dialog"
            aria-modal="true"
            aria-label="Mobile navigation menu"
          >
            <div className="flex h-16 items-center justify-between px-4 border-b border-[rgb(var(--color-gray-200))]">
              <span className="text-lg font-semibold text-[rgb(var(--color-gray-900))]">
                Menu
              </span>
              <button
                type="button"
                className="inline-flex items-center justify-center p-2 rounded-[var(--radius-md)] text-[rgb(var(--color-gray-700))] hover:bg-[rgb(var(--color-gray-100))] hover:text-[rgb(var(--color-gray-900))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))] transition-colors duration-[var(--transition-fast)]"
                onClick={toggleMobileMenu}
                aria-label="Close menu"
              >
                <svg
                  className="h-6 w-6"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            <div className="overflow-y-auto h-[calc(100vh-4rem)] pb-safe">
              <nav className="px-4 py-6 space-y-1" aria-label="Mobile navigation">
                {NAVIGATION_LINKS.map((link) => {
                  const isActive = isActivePath(link.path);
                  return (
                    <Link
                      key={link.path}
                      to={link.path}
                      className={`block px-4 py-3 text-base font-medium rounded-[var(--radius-md)] transition-colors duration-[var(--transition-fast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))] ${
                        isActive
                          ? 'bg-[rgb(var(--color-primary-50))] text-[rgb(var(--color-primary-700))]'
                          : 'text-[rgb(var(--color-gray-700))] hover:bg-[rgb(var(--color-gray-100))] hover:text-[rgb(var(--color-gray-900))]'
                      }`}
                      aria-label={link.ariaLabel}
                      aria-current={isActive ? 'page' : undefined}
                    >
                      {link.label}
                    </Link>
                  );
                })}
              </nav>

              <div className="border-t border-[rgb(var(--color-gray-200))] px-4 py-6 space-y-3">
                <Link
                  to="/login"
                  className="block w-full px-4 py-3 text-center text-base font-medium text-[rgb(var(--color-gray-700))] hover:text-[rgb(var(--color-gray-900))] border border-[rgb(var(--color-gray-300))] rounded-[var(--radius-md)] transition-colors duration-[var(--transition-fast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
                  aria-label="Sign in to your account"
                >
                  Sign In
                </Link>
                <Link
                  to="/signup"
                  className="block w-full px-4 py-3 text-center text-base font-medium text-white bg-[rgb(var(--color-primary-600))] hover:bg-[rgb(var(--color-primary-700))] rounded-[var(--radius-md)] shadow-[var(--shadow-sm)] transition-colors duration-[var(--transition-fast)] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
                  aria-label="Create a new account"
                >
                  Get Started
                </Link>
              </div>
            </div>
          </div>
        </>
      )}
    </header>
  );
}