import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ConfigurationProvider } from '../contexts/ConfigurationContext';
import ConfigurationWizard from '../components/Configuration/ConfigurationWizard';

interface ConfigurationOption {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly category: 'exterior' | 'interior' | 'performance' | 'technology';
  readonly price: number;
  readonly imageUrl: string;
}

interface ConfigurationState {
  readonly selectedOptions: readonly string[];
  readonly totalPrice: number;
}

const MOCK_OPTIONS: readonly ConfigurationOption[] = [
  {
    id: '1',
    name: 'Premium Paint',
    description: 'Metallic finish with ceramic coating',
    category: 'exterior',
    price: 1500,
    imageUrl: 'https://via.placeholder.com/300x200?text=Premium+Paint',
  },
  {
    id: '2',
    name: 'Sport Wheels',
    description: '20-inch alloy wheels with performance tires',
    category: 'exterior',
    price: 2000,
    imageUrl: 'https://via.placeholder.com/300x200?text=Sport+Wheels',
  },
  {
    id: '3',
    name: 'Leather Interior',
    description: 'Premium leather seats with heating and ventilation',
    category: 'interior',
    price: 3000,
    imageUrl: 'https://via.placeholder.com/300x200?text=Leather+Interior',
  },
  {
    id: '4',
    name: 'Premium Sound System',
    description: '12-speaker surround sound system',
    category: 'technology',
    price: 1800,
    imageUrl: 'https://via.placeholder.com/300x200?text=Sound+System',
  },
  {
    id: '5',
    name: 'Performance Package',
    description: 'Enhanced suspension and braking system',
    category: 'performance',
    price: 4500,
    imageUrl: 'https://via.placeholder.com/300x200?text=Performance+Package',
  },
  {
    id: '6',
    name: 'Advanced Driver Assistance',
    description: 'Adaptive cruise control and lane keeping assist',
    category: 'technology',
    price: 2500,
    imageUrl: 'https://via.placeholder.com/300x200?text=Driver+Assistance',
  },
] as const;

const CATEGORIES: readonly { readonly id: string; readonly label: string }[] = [
  { id: 'all', label: 'All Options' },
  { id: 'exterior', label: 'Exterior' },
  { id: 'interior', label: 'Interior' },
  { id: 'performance', label: 'Performance' },
  { id: 'technology', label: 'Technology' },
] as const;

function ConfigureContent(): JSX.Element {
  const { vehicleId } = useParams<{ vehicleId: string }>();
  const navigate = useNavigate();
  const [configuration, setConfiguration] = useState<ConfigurationState>({
    selectedOptions: [],
    totalPrice: 0,
  });

  const [selectedCategory, setSelectedCategory] = useState<string>('all');

  if (!vehicleId) {
    return (
      <div className="min-h-screen bg-[rgb(var(--color-gray-50))] pt-16">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
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
                d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-[rgb(var(--color-gray-900))]">
              Vehicle ID Required
            </h3>
            <p className="mt-2 text-sm text-[rgb(var(--color-gray-600))]">
              Please select a vehicle to configure
            </p>
            <button
              type="button"
              onClick={() => navigate('/browse')}
              className="mt-6 inline-flex items-center rounded-[var(--radius-md)] bg-[rgb(var(--color-primary-600))] px-4 py-2 text-sm font-medium text-white transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-primary-700))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
            >
              Browse Vehicles
            </button>
          </div>
        </div>
      </div>
    );
  }

  const handleOptionToggle = (optionId: string, price: number): void => {
    setConfiguration((prev) => {
      const isSelected = prev.selectedOptions.includes(optionId);
      
      if (isSelected) {
        return {
          selectedOptions: prev.selectedOptions.filter((id) => id !== optionId),
          totalPrice: prev.totalPrice - price,
        };
      }

      return {
        selectedOptions: [...prev.selectedOptions, optionId],
        totalPrice: prev.totalPrice + price,
      };
    });
  };

  const handleCategoryChange = (event: React.ChangeEvent<HTMLSelectElement>): void => {
    setSelectedCategory(event.target.value);
  };

  const handleResetConfiguration = (): void => {
    setConfiguration({
      selectedOptions: [],
      totalPrice: 0,
    });
  };

  const handleComplete = (): void => {
    navigate('/cart');
  };

  const handleCancel = (): void => {
    navigate('/browse');
  };

  const filteredOptions =
    selectedCategory === 'all'
      ? MOCK_OPTIONS
      : MOCK_OPTIONS.filter((option) => option.category === selectedCategory);

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
        <ConfigurationWizard
          vehicleId={vehicleId}
          onComplete={handleComplete}
          onCancel={handleCancel}
          enablePersistence={true}
        />

        <div className="mt-8 mb-8 rounded-[var(--radius-lg)] bg-white p-6 shadow-[var(--shadow-sm)]">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex-1">
              <label
                htmlFor="category"
                className="mb-2 block text-sm font-medium text-[rgb(var(--color-gray-700))]"
              >
                Filter by Category
              </label>
              <select
                id="category"
                value={selectedCategory}
                onChange={handleCategoryChange}
                className="w-full rounded-[var(--radius-md)] border border-[rgb(var(--color-gray-300))] px-4 py-2 text-sm text-[rgb(var(--color-gray-900))] transition-colors duration-[var(--transition-fast)] focus:border-[rgb(var(--color-primary-500))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary-500))] focus:ring-opacity-20 sm:max-w-xs"
                aria-label="Filter options by category"
              >
                {CATEGORIES.map((category) => (
                  <option key={category.id} value={category.id}>
                    {category.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="flex flex-col gap-2 sm:items-end">
              <div className="text-sm text-[rgb(var(--color-gray-600))]">
                Selected Options: {configuration.selectedOptions.length}
              </div>
              <div className="text-2xl font-bold text-[rgb(var(--color-primary-600))]">
                Total: {formatPrice(configuration.totalPrice)}
              </div>
              {configuration.selectedOptions.length > 0 && (
                <button
                  type="button"
                  onClick={handleResetConfiguration}
                  className="text-sm text-[rgb(var(--color-gray-600))] underline transition-colors duration-[var(--transition-fast)] hover:text-[rgb(var(--color-gray-900))]"
                  aria-label="Reset all configuration options"
                >
                  Reset Configuration
                </button>
              )}
            </div>
          </div>
        </div>

        {filteredOptions.length === 0 ? (
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
              No options available
            </h3>
            <p className="mt-2 text-sm text-[rgb(var(--color-gray-600))]">
              Try selecting a different category
            </p>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {filteredOptions.map((option) => {
              const isSelected = configuration.selectedOptions.includes(option.id);

              return (
                <article
                  key={option.id}
                  className={`overflow-hidden rounded-[var(--radius-lg)] bg-white shadow-[var(--shadow-sm)] transition-all duration-[var(--transition-base)] ${
                    isSelected
                      ? 'ring-2 ring-[rgb(var(--color-primary-500))] ring-offset-2'
                      : 'hover:shadow-[var(--shadow-md)]'
                  }`}
                >
                  <div className="aspect-[3/2] overflow-hidden bg-[rgb(var(--color-gray-200))]">
                    <img
                      src={option.imageUrl}
                      alt={option.name}
                      className="h-full w-full object-cover"
                      loading="lazy"
                    />
                  </div>
                  <div className="p-6">
                    <div className="mb-2 flex items-center justify-between">
                      <span className="inline-flex items-center rounded-[var(--radius-full)] bg-[rgb(var(--color-primary-50))] px-3 py-1 text-xs font-medium text-[rgb(var(--color-primary-700))]">
                        {capitalizeFirstLetter(option.category)}
                      </span>
                      {isSelected && (
                        <svg
                          className="h-5 w-5 text-[rgb(var(--color-primary-600))]"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                          aria-hidden="true"
                        >
                          <path
                            fillRule="evenodd"
                            d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                            clipRule="evenodd"
                          />
                        </svg>
                      )}
                    </div>
                    <h3 className="text-lg font-semibold text-[rgb(var(--color-gray-900))]">
                      {option.name}
                    </h3>
                    <p className="mt-2 text-sm text-[rgb(var(--color-gray-600))]">
                      {option.description}
                    </p>
                    <p className="mt-3 text-xl font-bold text-[rgb(var(--color-primary-600))]">
                      {formatPrice(option.price)}
                    </p>
                    <button
                      type="button"
                      onClick={() => handleOptionToggle(option.id, option.price)}
                      className={`mt-4 w-full rounded-[var(--radius-md)] px-4 py-2 text-sm font-medium transition-colors duration-[var(--transition-fast)] focus-visible:outline-2 focus-visible:outline-offset-2 ${
                        isSelected
                          ? 'bg-[rgb(var(--color-gray-200))] text-[rgb(var(--color-gray-700))] hover:bg-[rgb(var(--color-gray-300))] focus-visible:outline-[rgb(var(--color-gray-500))]'
                          : 'bg-[rgb(var(--color-primary-600))] text-white hover:bg-[rgb(var(--color-primary-700))] focus-visible:outline-[rgb(var(--color-primary-600))]'
                      }`}
                      aria-label={
                        isSelected
                          ? `Remove ${option.name} from configuration`
                          : `Add ${option.name} to configuration`
                      }
                      aria-pressed={isSelected}
                    >
                      {isSelected ? 'Remove Option' : 'Add Option'}
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}

        {configuration.selectedOptions.length > 0 && (
          <div className="mt-8 rounded-[var(--radius-lg)] bg-white p-6 shadow-[var(--shadow-sm)]">
            <h2 className="mb-4 text-xl font-semibold text-[rgb(var(--color-gray-900))]">
              Configuration Summary
            </h2>
            <div className="space-y-3">
              {configuration.selectedOptions.map((optionId) => {
                const option = MOCK_OPTIONS.find((opt) => opt.id === optionId);
                if (!option) return null;

                return (
                  <div
                    key={option.id}
                    className="flex items-center justify-between border-b border-[rgb(var(--color-gray-200))] pb-3 last:border-b-0"
                  >
                    <div>
                      <div className="font-medium text-[rgb(var(--color-gray-900))]">
                        {option.name}
                      </div>
                      <div className="text-sm text-[rgb(var(--color-gray-600))]">
                        {capitalizeFirstLetter(option.category)}
                      </div>
                    </div>
                    <div className="font-semibold text-[rgb(var(--color-gray-900))]">
                      {formatPrice(option.price)}
                    </div>
                  </div>
                );
              })}
              <div className="flex items-center justify-between pt-3">
                <div className="text-lg font-bold text-[rgb(var(--color-gray-900))]">
                  Total Price
                </div>
                <div className="text-2xl font-bold text-[rgb(var(--color-primary-600))]">
                  {formatPrice(configuration.totalPrice)}
                </div>
              </div>
            </div>
            <button
              type="button"
              className="mt-6 w-full rounded-[var(--radius-md)] bg-[rgb(var(--color-primary-600))] px-6 py-3 text-base font-medium text-white transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-primary-700))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
              aria-label="Proceed to checkout with selected configuration"
            >
              Continue to Checkout
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

export default function Configure(): JSX.Element {
  const { vehicleId } = useParams<{ vehicleId: string }>();

  if (!vehicleId) {
    return <ConfigureContent />;
  }

  return (
    <ConfigurationProvider vehicleId={vehicleId} enablePersistence={true}>
      <ConfigureContent />
    </ConfigurationProvider>
  );
}