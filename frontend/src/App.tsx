import React from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import Browse from './pages/Browse';
import VehicleDetailPage from './components/VehicleDetail/VehicleDetailPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      gcTime: 10 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 3,
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
  },
});

const Configure: React.FC = () => {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-2xl font-bold text-gray-900">
        Configure Your Vehicle
      </h2>
      <p className="text-gray-600">
        Customize your vehicle with available options and packages.
      </p>
    </div>
  );
};

const Cart: React.FC = () => {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-2xl font-bold text-gray-900">Shopping Cart</h2>
      <p className="text-gray-600">
        Review your selections and proceed to checkout.
      </p>
    </div>
  );
};

const Track: React.FC = () => {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-2xl font-bold text-gray-900">Track Order</h2>
      <p className="text-gray-600">
        Monitor the status of your vehicle order and delivery.
      </p>
    </div>
  );
};

const Home: React.FC = () => {
  return (
    <div className="rounded-lg bg-white p-6 shadow">
      <h2 className="mb-4 text-xl font-semibold text-gray-800">
        Welcome to AutoSelect
      </h2>
      <p className="text-gray-600">
        Your modern car ordering platform is ready for development.
      </p>
    </div>
  );
};

interface NavLinkProps {
  to: string;
  children: React.ReactNode;
  mobile?: boolean;
}

const NavLink: React.FC<NavLinkProps> = ({ to, children, mobile = false }) => {
  const location = useLocation();
  const isActive = location.pathname === to;

  const baseClasses = mobile
    ? 'block px-3 py-2 text-base font-medium'
    : 'inline-flex items-center px-3 py-2 text-sm font-medium';

  const activeClasses = isActive
    ? 'border-b-2 border-blue-600 text-blue-600'
    : 'border-b-2 border-transparent text-gray-700 hover:border-gray-300 hover:text-gray-900';

  return (
    <Link to={to} className={`${baseClasses} ${activeClasses}`}>
      {children}
    </Link>
  );
};

const App: React.FC = () => {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  const toggleMobileMenu = (): void => {
    setMobileMenuOpen((prev) => !prev);
  };

  const closeMobileMenu = (): void => {
    setMobileMenuOpen(false);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <div className="min-h-screen bg-gray-50">
        <header className="bg-white shadow-sm">
          <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
            <div className="flex h-16 items-center justify-between">
              <div className="flex items-center">
                <Link
                  to="/"
                  className="text-2xl font-bold text-gray-900"
                  onClick={closeMobileMenu}
                >
                  AutoSelect
                </Link>
              </div>

              <nav className="hidden md:flex md:space-x-8" aria-label="Main">
                <NavLink to="/browse">Browse</NavLink>
                <NavLink to="/configure">Configure</NavLink>
                <NavLink to="/cart">Cart</NavLink>
                <NavLink to="/track">Track</NavLink>
              </nav>

              <button
                type="button"
                className="inline-flex items-center justify-center rounded-md p-2 text-gray-700 hover:bg-gray-100 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-600 md:hidden"
                onClick={toggleMobileMenu}
                aria-expanded={mobileMenuOpen}
                aria-label="Toggle navigation menu"
              >
                <svg
                  className="h-6 w-6"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth="1.5"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  {mobileMenuOpen ? (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M6 18L18 6M6 6l12 12"
                    />
                  ) : (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
                    />
                  )}
                </svg>
              </button>
            </div>
          </div>

          {mobileMenuOpen && (
            <div className="md:hidden" role="navigation" aria-label="Mobile">
              <div className="space-y-1 px-2 pb-3 pt-2">
                <NavLink to="/browse" mobile>
                  Browse
                </NavLink>
                <NavLink to="/configure" mobile>
                  Configure
                </NavLink>
                <NavLink to="/cart" mobile>
                  Cart
                </NavLink>
                <NavLink to="/track" mobile>
                  Track
                </NavLink>
              </div>
            </div>
          )}
        </header>

        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/browse" element={<Browse />} />
            <Route path="/vehicles/:id" element={<VehicleDetailPage />} />
            <Route path="/configure" element={<Configure />} />
            <Route path="/cart" element={<Cart />} />
            <Route path="/track" element={<Track />} />
          </Routes>
        </main>

        <footer className="mt-auto border-t border-gray-200 bg-white">
          <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
            <p className="text-center text-sm text-gray-600">
              &copy; {new Date().getFullYear()} AutoSelect. All rights reserved.
            </p>
          </div>
        </footer>
      </div>
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  );
};

export default App;