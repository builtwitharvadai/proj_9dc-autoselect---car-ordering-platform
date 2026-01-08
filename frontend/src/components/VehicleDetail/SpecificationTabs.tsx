import React, { useState, useCallback, useEffect, useRef } from 'react';
import type { Vehicle } from '../../types/vehicle';

/**
 * Tab identifier for specification sections
 */
type TabId = 'overview' | 'features' | 'specifications' | 'pricing';

/**
 * Tab configuration interface
 */
interface TabConfig {
  readonly id: TabId;
  readonly label: string;
  readonly ariaLabel: string;
}

/**
 * Props for SpecificationTabs component
 */
interface SpecificationTabsProps {
  readonly vehicle: Vehicle;
  readonly className?: string;
  readonly defaultTab?: TabId;
  readonly onTabChange?: (tabId: TabId) => void;
}

/**
 * Tab configuration array
 */
const TABS: readonly TabConfig[] = [
  {
    id: 'overview',
    label: 'Overview',
    ariaLabel: 'View vehicle overview',
  },
  {
    id: 'features',
    label: 'Features',
    ariaLabel: 'View vehicle features',
  },
  {
    id: 'specifications',
    label: 'Specifications',
    ariaLabel: 'View vehicle specifications',
  },
  {
    id: 'pricing',
    label: 'Pricing',
    ariaLabel: 'View vehicle pricing',
  },
] as const;

/**
 * Format currency value
 */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value);
}

/**
 * Format fuel economy value
 */
function formatFuelEconomy(value: number): string {
  return `${value} MPG`;
}

/**
 * Format dimension value
 */
function formatDimension(value: number): string {
  return `${value}"`;
}

/**
 * Format weight value
 */
function formatWeight(value: number): string {
  return `${value.toLocaleString()} lbs`;
}

/**
 * Format capacity value
 */
function formatCapacity(value: number): string {
  return `${value.toLocaleString()} lbs`;
}

/**
 * Tabbed interface component for organizing vehicle specifications and information
 * Implements accessible tabbed navigation with keyboard support and ARIA attributes
 */
export default function SpecificationTabs({
  vehicle,
  className = '',
  defaultTab = 'overview',
  onTabChange,
}: SpecificationTabsProps): JSX.Element {
  const [activeTab, setActiveTab] = useState<TabId>(defaultTab);
  const tabListRef = useRef<HTMLDivElement>(null);
  const tabRefs = useRef<Map<TabId, HTMLButtonElement>>(new Map());

  /**
   * Handle tab change with callback notification
   */
  const handleTabChange = useCallback(
    (tabId: TabId) => {
      setActiveTab(tabId);
      onTabChange?.(tabId);
    },
    [onTabChange]
  );

  /**
   * Handle keyboard navigation
   */
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLButtonElement>, currentIndex: number) => {
      let newIndex = currentIndex;

      switch (event.key) {
        case 'ArrowLeft':
          event.preventDefault();
          newIndex = currentIndex > 0 ? currentIndex - 1 : TABS.length - 1;
          break;
        case 'ArrowRight':
          event.preventDefault();
          newIndex = currentIndex < TABS.length - 1 ? currentIndex + 1 : 0;
          break;
        case 'Home':
          event.preventDefault();
          newIndex = 0;
          break;
        case 'End':
          event.preventDefault();
          newIndex = TABS.length - 1;
          break;
        default:
          return;
      }

      const newTab = TABS[newIndex];
      if (newTab) {
        handleTabChange(newTab.id);
        tabRefs.current.get(newTab.id)?.focus();
      }
    },
    [handleTabChange]
  );

  /**
   * Set tab ref for keyboard navigation
   */
  const setTabRef = useCallback((tabId: TabId, element: HTMLButtonElement | null) => {
    if (element) {
      tabRefs.current.set(tabId, element);
    } else {
      tabRefs.current.delete(tabId);
    }
  }, []);

  /**
   * Focus active tab on mount
   */
  useEffect(() => {
    const activeTabElement = tabRefs.current.get(activeTab);
    if (activeTabElement && document.activeElement === document.body) {
      activeTabElement.focus();
    }
  }, [activeTab]);

  return (
    <div className={`specification-tabs ${className}`}>
      {/* Tab List */}
      <div
        ref={tabListRef}
        role="tablist"
        aria-label="Vehicle information sections"
        className="border-b border-gray-200"
      >
        <nav className="-mb-px flex space-x-8" aria-label="Tabs">
          {TABS.map((tab, index) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                ref={(el) => setTabRef(tab.id, el)}
                role="tab"
                aria-selected={isActive}
                aria-controls={`tabpanel-${tab.id}`}
                id={`tab-${tab.id}`}
                tabIndex={isActive ? 0 : -1}
                onClick={() => handleTabChange(tab.id)}
                onKeyDown={(e) => handleKeyDown(e, index)}
                className={`
                  whitespace-nowrap border-b-2 py-4 px-1 text-sm font-medium
                  transition-colors duration-200 focus:outline-none focus:ring-2
                  focus:ring-blue-500 focus:ring-offset-2
                  ${
                    isActive
                      ? 'border-blue-500 text-blue-600'
                      : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  }
                `}
                aria-label={tab.ariaLabel}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab Panels */}
      <div className="mt-6">
        {/* Overview Panel */}
        <div
          role="tabpanel"
          id="tabpanel-overview"
          aria-labelledby="tab-overview"
          hidden={activeTab !== 'overview'}
          className="space-y-6"
        >
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Vehicle Overview</h3>
            <p className="text-gray-700 leading-relaxed">{vehicle.description}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-500 mb-2">Engine</h4>
              <p className="text-base text-gray-900">{vehicle.specifications.engine}</p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-500 mb-2">Transmission</h4>
              <p className="text-base text-gray-900 capitalize">
                {vehicle.specifications.transmission}
              </p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-500 mb-2">Drivetrain</h4>
              <p className="text-base text-gray-900 uppercase">
                {vehicle.specifications.drivetrain}
              </p>
            </div>
            <div className="bg-gray-50 p-4 rounded-lg">
              <h4 className="text-sm font-medium text-gray-500 mb-2">Fuel Type</h4>
              <p className="text-base text-gray-900 capitalize">
                {vehicle.specifications.fuelType.replace('-', ' ')}
              </p>
            </div>
          </div>
        </div>

        {/* Features Panel */}
        <div
          role="tabpanel"
          id="tabpanel-features"
          aria-labelledby="tab-features"
          hidden={activeTab !== 'features'}
          className="space-y-6"
        >
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Safety Features</h3>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {vehicle.features.safety.map((feature, index) => (
                <li key={index} className="flex items-start">
                  <svg
                    className="h-5 w-5 text-green-500 mr-2 mt-0.5 flex-shrink-0"
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
                  <span className="text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Comfort Features</h3>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {vehicle.features.comfort.map((feature, index) => (
                <li key={index} className="flex items-start">
                  <svg
                    className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
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
                  <span className="text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Technology Features</h3>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {vehicle.features.technology.map((feature, index) => (
                <li key={index} className="flex items-start">
                  <svg
                    className="h-5 w-5 text-purple-500 mr-2 mt-0.5 flex-shrink-0"
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
                  <span className="text-gray-700">{feature}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Specifications Panel */}
        <div
          role="tabpanel"
          id="tabpanel-specifications"
          aria-labelledby="tab-specifications"
          hidden={activeTab !== 'specifications'}
          className="space-y-6"
        >
          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance</h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Horsepower</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {vehicle.specifications.horsepower} HP
                </dd>
              </div>
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Torque</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {vehicle.specifications.torque} lb-ft
                </dd>
              </div>
            </dl>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Fuel Economy</h3>
            <dl className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">City</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {formatFuelEconomy(vehicle.specifications.fuelEconomy.city)}
                </dd>
              </div>
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Highway</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {formatFuelEconomy(vehicle.specifications.fuelEconomy.highway)}
                </dd>
              </div>
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Combined</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {formatFuelEconomy(vehicle.specifications.fuelEconomy.combined)}
                </dd>
              </div>
            </dl>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Dimensions</h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Length</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {formatDimension(vehicle.specifications.dimensions.length)}
                </dd>
              </div>
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Width</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {formatDimension(vehicle.specifications.dimensions.width)}
                </dd>
              </div>
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Height</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {formatDimension(vehicle.specifications.dimensions.height)}
                </dd>
              </div>
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Wheelbase</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {formatDimension(vehicle.specifications.dimensions.wheelbase)}
                </dd>
              </div>
              {vehicle.specifications.dimensions.groundClearance && (
                <div className="border-b border-gray-200 pb-3">
                  <dt className="text-sm font-medium text-gray-500">Ground Clearance</dt>
                  <dd className="mt-1 text-base text-gray-900">
                    {formatDimension(vehicle.specifications.dimensions.groundClearance)}
                  </dd>
                </div>
              )}
              {vehicle.specifications.dimensions.cargoVolume && (
                <div className="border-b border-gray-200 pb-3">
                  <dt className="text-sm font-medium text-gray-500">Cargo Volume</dt>
                  <dd className="mt-1 text-base text-gray-900">
                    {vehicle.specifications.dimensions.cargoVolume} cu ft
                  </dd>
                </div>
              )}
            </dl>
          </div>

          <div>
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Capacity</h3>
            <dl className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border-b border-gray-200 pb-3">
                <dt className="text-sm font-medium text-gray-500">Seating Capacity</dt>
                <dd className="mt-1 text-base text-gray-900">
                  {vehicle.specifications.seatingCapacity} passengers
                </dd>
              </div>
              {vehicle.specifications.curbWeight && (
                <div className="border-b border-gray-200 pb-3">
                  <dt className="text-sm font-medium text-gray-500">Curb Weight</dt>
                  <dd className="mt-1 text-base text-gray-900">
                    {formatWeight(vehicle.specifications.curbWeight)}
                  </dd>
                </div>
              )}
              {vehicle.specifications.towingCapacity && (
                <div className="border-b border-gray-200 pb-3">
                  <dt className="text-sm font-medium text-gray-500">Towing Capacity</dt>
                  <dd className="mt-1 text-base text-gray-900">
                    {formatCapacity(vehicle.specifications.towingCapacity)}
                  </dd>
                </div>
              )}
            </dl>
          </div>
        </div>

        {/* Pricing Panel */}
        <div
          role="tabpanel"
          id="tabpanel-pricing"
          aria-labelledby="tab-pricing"
          hidden={activeTab !== 'pricing'}
          className="space-y-6"
        >
          <div className="bg-gradient-to-br from-blue-50 to-indigo-50 p-6 rounded-lg">
            <div className="flex items-baseline justify-between mb-4">
              <div>
                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">
                  Current Price
                </h3>
                <p className="text-4xl font-bold text-gray-900 mt-2">
                  {formatCurrency(vehicle.price)}
                </p>
              </div>
              {vehicle.msrp !== vehicle.price && (
                <div className="text-right">
                  <p className="text-sm text-gray-500 line-through">
                    MSRP: {formatCurrency(vehicle.msrp)}
                  </p>
                  <p className="text-sm font-medium text-green-600 mt-1">
                    Save {formatCurrency(vehicle.msrp - vehicle.price)}
                  </p>
                </div>
              )}
            </div>
            {vehicle.msrp === vehicle.price && (
              <p className="text-sm text-gray-600">
                MSRP: {formatCurrency(vehicle.msrp)}
              </p>
            )}
          </div>

          <div className="bg-gray-50 p-6 rounded-lg">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Pricing Information</h3>
            <ul className="space-y-3 text-sm text-gray-700">
              <li className="flex items-start">
                <svg
                  className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
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
                <span>Price includes destination charges and dealer fees</span>
              </li>
              <li className="flex items-start">
                <svg
                  className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
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
                <span>Financing options available with approved credit</span>
              </li>
              <li className="flex items-start">
                <svg
                  className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
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
                <span>Trade-in value assessment available</span>
              </li>
              <li className="flex items-start">
                <svg
                  className="h-5 w-5 text-blue-500 mr-2 mt-0.5 flex-shrink-0"
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
                <span>Extended warranty and protection plans available</span>
              </li>
            </ul>
          </div>

          <div className="border-t border-gray-200 pt-6">
            <p className="text-xs text-gray-500">
              * Prices and availability subject to change. Contact dealer for most current
              information. Additional fees may apply including taxes, registration, and
              documentation fees.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}