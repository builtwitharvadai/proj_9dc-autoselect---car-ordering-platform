import { useState, useEffect } from 'react';

interface Vehicle {
  readonly id: string;
  readonly make: string;
  readonly model: string;
  readonly year: number;
  readonly price: number;
  readonly imageUrl: string;
  readonly type: 'sedan' | 'suv' | 'truck' | 'coupe';
}

interface FilterState {
  readonly searchQuery: string;
  readonly selectedType: string;
  readonly priceRange: readonly [number, number];
}

const MOCK_VEHICLES: readonly Vehicle[] = [
  {
    id: '1',
    make: 'Toyota',
    model: 'Camry',
    year: 2024,
    price: 28500,
    imageUrl: 'https://via.placeholder.com/400x300?text=Toyota+Camry',
    type: 'sedan',
  },
  {
    id: '2',
    make: 'Honda',
    model: 'CR-V',
    year: 2024,
    price: 32000,
    imageUrl: 'https://via.placeholder.com/400x300?text=Honda+CR-V',
    type: 'suv',
  },
  {
    id: '3',
    make: 'Ford',
    model: 'F-150',
    year: 2024,
    price: 45000,
    imageUrl: 'https://via.placeholder.com/400x300?text=Ford+F-150',
    type: 'truck',
  },
  {
    id: '4',
    make: 'BMW',
    model: '3 Series',
    year: 2024,
    price: 42000,
    imageUrl: 'https://via.placeholder.com/400x300?text=BMW+3+Series',
    type: 'sedan',
  },
  {
    id: '5',
    make: 'Tesla',
    model: 'Model Y',
    year: 2024,
    price: 52000,
    imageUrl: 'https://via.placeholder.com/400x300?text=Tesla+Model+Y',
    type: 'suv',
  },
  {
    id: '6',
    make: 'Chevrolet',
    model: 'Corvette',
    year: 2024,
    price: 68000,
    imageUrl: 'https://via.placeholder.com/400x300?text=Chevrolet+Corvette',
    type: 'coupe',
  },
] as const;

const VEHICLE_TYPES: readonly string[] = ['all', 'sedan', 'suv', 'truck', 'coupe'] as const;

export default function Browse(): JSX.Element {
  const [filters, setFilters] = useState<FilterState>({
    searchQuery: '',
    selectedType: 'all',
    priceRange: [0, 100000],
  });

  const [filteredVehicles, setFilteredVehicles] = useState<readonly Vehicle[]>(MOCK_VEHICLES);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 500);

    return () => {
      clearTimeout(timer);
    };
  }, []);

  useEffect(() => {
    const filtered = MOCK_VEHICLES.filter((vehicle) => {
      const matchesSearch =
        filters.searchQuery === '' ||
        vehicle.make.toLowerCase().includes(filters.searchQuery.toLowerCase()) ||
        vehicle.model.toLowerCase().includes(filters.searchQuery.toLowerCase());

      const matchesType =
        filters.selectedType === 'all' || vehicle.type === filters.selectedType;

      const matchesPrice =
        vehicle.price >= filters.priceRange[0] && vehicle.price <= filters.priceRange[1];

      return matchesSearch && matchesType && matchesPrice;
    });

    setFilteredVehicles(filtered);
  }, [filters]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    setFilters((prev) => ({
      ...prev,
      searchQuery: event.target.value,
    }));
  };

  const handleTypeChange = (event: React.ChangeEvent<HTMLSelectElement>): void => {
    setFilters((prev) => ({
      ...prev,
      selectedType: event.target.value,
    }));
  };

  const handlePriceRangeChange = (event: React.ChangeEvent<HTMLInputElement>): void => {
    const maxPrice = Number(event.target.value);
    setFilters((prev) => ({
      ...prev,
      priceRange: [prev.priceRange[0], maxPrice],
    }));
  };

  const formatPrice = (price: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  };

  const capitalizeFirstLetter = (text: string): string => {
    return text.charAt(0).toUpperCase() + text.slice(1);
  };

  return (
    <div className="min-h-screen bg-[rgb(var(--color-gray-50))] pt-16">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[rgb(var(--color-gray-900))] sm:text-4xl">
            Browse Vehicles
          </h1>
          <p className="mt-2 text-base text-[rgb(var(--color-gray-600))] sm:text-lg">
            Discover your perfect vehicle from our extensive collection
          </p>
        </div>

        <div className="mb-8 rounded-[var(--radius-lg)] bg-white p-6 shadow-[var(--shadow-sm)]">
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            <div>
              <label
                htmlFor="search"
                className="mb-2 block text-sm font-medium text-[rgb(var(--color-gray-700))]"
              >
                Search
              </label>
              <input
                type="text"
                id="search"
                value={filters.searchQuery}
                onChange={handleSearchChange}
                placeholder="Search by make or model..."
                className="w-full rounded-[var(--radius-md)] border border-[rgb(var(--color-gray-300))] px-4 py-2 text-sm text-[rgb(var(--color-gray-900))] placeholder-[rgb(var(--color-gray-400))] transition-colors duration-[var(--transition-fast)] focus:border-[rgb(var(--color-primary-500))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary-500))] focus:ring-opacity-20"
                aria-label="Search vehicles by make or model"
              />
            </div>

            <div>
              <label
                htmlFor="type"
                className="mb-2 block text-sm font-medium text-[rgb(var(--color-gray-700))]"
              >
                Vehicle Type
              </label>
              <select
                id="type"
                value={filters.selectedType}
                onChange={handleTypeChange}
                className="w-full rounded-[var(--radius-md)] border border-[rgb(var(--color-gray-300))] px-4 py-2 text-sm text-[rgb(var(--color-gray-900))] transition-colors duration-[var(--transition-fast)] focus:border-[rgb(var(--color-primary-500))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary-500))] focus:ring-opacity-20"
                aria-label="Filter by vehicle type"
              >
                {VEHICLE_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {capitalizeFirstLetter(type)}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label
                htmlFor="price"
                className="mb-2 block text-sm font-medium text-[rgb(var(--color-gray-700))]"
              >
                Max Price: {formatPrice(filters.priceRange[1])}
              </label>
              <input
                type="range"
                id="price"
                min="0"
                max="100000"
                step="5000"
                value={filters.priceRange[1]}
                onChange={handlePriceRangeChange}
                className="w-full"
                aria-label="Set maximum price filter"
              />
            </div>
          </div>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-[rgb(var(--color-gray-200))] border-t-[rgb(var(--color-primary-600))]" />
          </div>
        ) : (
          <>
            <div className="mb-6 flex items-center justify-between">
              <p className="text-sm text-[rgb(var(--color-gray-600))]">
                Showing {filteredVehicles.length} of {MOCK_VEHICLES.length} vehicles
              </p>
            </div>

            {filteredVehicles.length === 0 ? (
              <div className="rounded-[var(--radius-lg)] bg-white p-12 text-center shadow-[var(--shadow-sm)]">
                <svg
                  className="mx-auto h-12 w-12 text-[rgb(var(--color-gray-400))]"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                <h3 className="mt-4 text-lg font-medium text-[rgb(var(--color-gray-900))]">
                  No vehicles found
                </h3>
                <p className="mt-2 text-sm text-[rgb(var(--color-gray-600))]">
                  Try adjusting your filters to see more results
                </p>
              </div>
            ) : (
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
                {filteredVehicles.map((vehicle) => (
                  <article
                    key={vehicle.id}
                    className="group overflow-hidden rounded-[var(--radius-lg)] bg-white shadow-[var(--shadow-sm)] transition-shadow duration-[var(--transition-base)] hover:shadow-[var(--shadow-md)]"
                  >
                    <div className="aspect-[4/3] overflow-hidden bg-[rgb(var(--color-gray-200))]">
                      <img
                        src={vehicle.imageUrl}
                        alt={`${vehicle.year} ${vehicle.make} ${vehicle.model}`}
                        className="h-full w-full object-cover transition-transform duration-[var(--transition-base)] group-hover:scale-105"
                        loading="lazy"
                      />
                    </div>
                    <div className="p-6">
                      <div className="mb-2 flex items-center justify-between">
                        <span className="inline-flex items-center rounded-[var(--radius-full)] bg-[rgb(var(--color-primary-50))] px-3 py-1 text-xs font-medium text-[rgb(var(--color-primary-700))]">
                          {capitalizeFirstLetter(vehicle.type)}
                        </span>
                        <span className="text-sm text-[rgb(var(--color-gray-600))]">
                          {vehicle.year}
                        </span>
                      </div>
                      <h3 className="text-lg font-semibold text-[rgb(var(--color-gray-900))]">
                        {vehicle.make} {vehicle.model}
                      </h3>
                      <p className="mt-2 text-2xl font-bold text-[rgb(var(--color-primary-600))]">
                        {formatPrice(vehicle.price)}
                      </p>
                      <button
                        type="button"
                        className="mt-4 w-full rounded-[var(--radius-md)] bg-[rgb(var(--color-primary-600))] px-4 py-2 text-sm font-medium text-white transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-primary-700))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
                        aria-label={`View details for ${vehicle.year} ${vehicle.make} ${vehicle.model}`}
                      >
                        View Details
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}