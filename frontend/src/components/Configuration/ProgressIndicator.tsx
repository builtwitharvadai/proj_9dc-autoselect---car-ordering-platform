/**
 * Progress indicator component for vehicle configuration wizard
 * Displays step-by-step progress with completion status and navigation
 * Supports responsive design for mobile and desktop views
 */

import { memo, useCallback, useMemo } from 'react';
import type {
  ConfigurationStep,
  ConfigurationStepMetadata,
} from '../../types/configuration';
import { CONFIGURATION_STEP_ORDER, CONFIGURATION_STEP_TITLES } from '../../types/configuration';

/**
 * Props for the ProgressIndicator component
 */
export interface ProgressIndicatorProps {
  /** Current active step in the configuration flow */
  readonly currentStep: ConfigurationStep;
  /** Array of completed steps */
  readonly completedSteps: readonly ConfigurationStep[];
  /** Callback when user clicks on a step */
  readonly onStepClick?: (step: ConfigurationStep) => void;
  /** Whether navigation is disabled */
  readonly disabled?: boolean;
  /** Additional CSS classes */
  readonly className?: string;
  /** Whether to show step descriptions */
  readonly showDescriptions?: boolean;
  /** Compact mode for mobile */
  readonly compact?: boolean;
}

/**
 * Step descriptions for each configuration step
 */
const STEP_DESCRIPTIONS: Record<ConfigurationStep, string> = {
  'select-trim': 'Choose your preferred trim level',
  'choose-color': 'Select exterior color',
  'select-packages': 'Add optional packages',
  'add-features': 'Customize with additional features',
  'review': 'Review your configuration',
} as const;

/**
 * Generate step metadata with completion and accessibility status
 */
function generateStepMetadata(
  step: ConfigurationStep,
  currentStep: ConfigurationStep,
  completedSteps: readonly ConfigurationStep[],
): ConfigurationStepMetadata {
  const order = CONFIGURATION_STEP_ORDER[step];
  const currentOrder = CONFIGURATION_STEP_ORDER[currentStep];
  const isComplete = completedSteps.includes(step);
  const isAccessible = isComplete || order <= currentOrder;

  return {
    step,
    title: CONFIGURATION_STEP_TITLES[step],
    description: STEP_DESCRIPTIONS[step],
    isComplete,
    isAccessible,
    order,
  };
}

/**
 * Get step status for styling
 */
function getStepStatus(
  step: ConfigurationStep,
  currentStep: ConfigurationStep,
  completedSteps: readonly ConfigurationStep[],
): 'complete' | 'current' | 'upcoming' | 'inaccessible' {
  if (completedSteps.includes(step)) {
    return 'complete';
  }
  if (step === currentStep) {
    return 'current';
  }
  const stepOrder = CONFIGURATION_STEP_ORDER[step];
  const currentOrder = CONFIGURATION_STEP_ORDER[currentStep];
  return stepOrder <= currentOrder ? 'upcoming' : 'inaccessible';
}

/**
 * Calculate overall progress percentage
 */
function calculateProgress(
  currentStep: ConfigurationStep,
  completedSteps: readonly ConfigurationStep[],
): number {
  const totalSteps = Object.keys(CONFIGURATION_STEP_ORDER).length;
  const currentOrder = CONFIGURATION_STEP_ORDER[currentStep];
  const completedCount = completedSteps.length;
  
  // Progress is based on completed steps plus partial credit for current step
  const progress = (completedCount + (currentOrder > completedCount ? 0.5 : 0)) / totalSteps;
  return Math.min(Math.max(progress * 100, 0), 100);
}

/**
 * Step indicator component
 */
const StepIndicator = memo(function StepIndicator({
  metadata,
  status,
  onClick,
  disabled,
  compact,
}: {
  readonly metadata: ConfigurationStepMetadata;
  readonly status: 'complete' | 'current' | 'upcoming' | 'inaccessible';
  readonly onClick?: () => void;
  readonly disabled?: boolean;
  readonly compact?: boolean;
}): JSX.Element {
  const isClickable = metadata.isAccessible && !disabled && onClick !== undefined;

  const handleClick = useCallback(() => {
    if (isClickable && onClick) {
      onClick();
    }
  }, [isClickable, onClick]);

  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent) => {
      if (isClickable && (event.key === 'Enter' || event.key === ' ')) {
        event.preventDefault();
        onClick?.();
      }
    },
    [isClickable, onClick],
  );

  // Status-based styling
  const statusStyles = useMemo(() => {
    const baseStyles = 'transition-all duration-200';
    switch (status) {
      case 'complete':
        return `${baseStyles} bg-green-600 text-white border-green-600`;
      case 'current':
        return `${baseStyles} bg-blue-600 text-white border-blue-600 ring-4 ring-blue-200`;
      case 'upcoming':
        return `${baseStyles} bg-white text-gray-700 border-gray-300`;
      case 'inaccessible':
        return `${baseStyles} bg-gray-100 text-gray-400 border-gray-200`;
      default:
        return baseStyles;
    }
  }, [status]);

  const iconSize = compact ? 'w-8 h-8' : 'w-10 h-10 md:w-12 md:h-12';
  const textSize = compact ? 'text-xs' : 'text-sm md:text-base';

  return (
    <div className="flex flex-col items-center">
      <button
        type="button"
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        disabled={!isClickable}
        className={`
          ${iconSize}
          rounded-full
          border-2
          flex
          items-center
          justify-center
          font-semibold
          ${statusStyles}
          ${isClickable ? 'cursor-pointer hover:scale-110 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500' : 'cursor-default'}
          ${disabled ? 'opacity-50' : ''}
        `}
        aria-label={`${metadata.title} - ${status}`}
        aria-current={status === 'current' ? 'step' : undefined}
        aria-disabled={!isClickable}
      >
        {status === 'complete' ? (
          <svg
            className="w-5 h-5 md:w-6 md:h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 13l4 4L19 7"
            />
          </svg>
        ) : (
          <span className={compact ? 'text-sm' : 'text-base md:text-lg'}>
            {metadata.order}
          </span>
        )}
      </button>
      <div className={`mt-2 text-center ${compact ? 'max-w-[80px]' : 'max-w-[120px]'}`}>
        <p
          className={`
            ${textSize}
            font-medium
            ${status === 'current' ? 'text-blue-600' : status === 'complete' ? 'text-green-600' : 'text-gray-600'}
            ${status === 'inaccessible' ? 'text-gray-400' : ''}
          `}
        >
          {metadata.title}
        </p>
      </div>
    </div>
  );
});

/**
 * Progress bar connector between steps
 */
const ProgressConnector = memo(function ProgressConnector({
  isComplete,
  compact,
}: {
  readonly isComplete: boolean;
  readonly compact?: boolean;
}): JSX.Element {
  return (
    <div
      className={`
        flex-1
        ${compact ? 'h-0.5 mx-1' : 'h-1 mx-2 md:mx-4'}
        ${isComplete ? 'bg-green-600' : 'bg-gray-300'}
        transition-colors
        duration-300
      `}
      aria-hidden="true"
    />
  );
});

/**
 * ProgressIndicator component
 * Displays step-by-step progress with navigation capabilities
 */
export default function ProgressIndicator({
  currentStep,
  completedSteps,
  onStepClick,
  disabled = false,
  className = '',
  showDescriptions = false,
  compact = false,
}: ProgressIndicatorProps): JSX.Element {
  // Generate metadata for all steps
  const stepsMetadata = useMemo(
    () =>
      (Object.keys(CONFIGURATION_STEP_ORDER) as ConfigurationStep[])
        .sort((a, b) => CONFIGURATION_STEP_ORDER[a] - CONFIGURATION_STEP_ORDER[b])
        .map((step) => generateStepMetadata(step, currentStep, completedSteps)),
    [currentStep, completedSteps],
  );

  // Calculate progress percentage
  const progressPercentage = useMemo(
    () => calculateProgress(currentStep, completedSteps),
    [currentStep, completedSteps],
  );

  // Handle step click
  const handleStepClick = useCallback(
    (step: ConfigurationStep) => {
      if (!disabled && onStepClick) {
        onStepClick(step);
      }
    },
    [disabled, onStepClick],
  );

  return (
    <nav
      className={`w-full ${className}`}
      aria-label="Configuration progress"
      role="navigation"
    >
      {/* Progress bar */}
      <div className="mb-6 md:mb-8">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">
            Progress: {Math.round(progressPercentage)}%
          </span>
          <span className="text-sm text-gray-500">
            Step {CONFIGURATION_STEP_ORDER[currentStep]} of {stepsMetadata.length}
          </span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
          <div
            className="bg-blue-600 h-full transition-all duration-500 ease-out rounded-full"
            style={{ width: `${progressPercentage}%` }}
            role="progressbar"
            aria-valuenow={Math.round(progressPercentage)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Configuration ${Math.round(progressPercentage)}% complete`}
          />
        </div>
      </div>

      {/* Step indicators */}
      <div className="flex items-start justify-between">
        {stepsMetadata.map((metadata, index) => {
          const status = getStepStatus(metadata.step, currentStep, completedSteps);
          const isLastStep = index === stepsMetadata.length - 1;
          const isConnectorComplete =
            index < stepsMetadata.length - 1 &&
            completedSteps.includes(stepsMetadata[index + 1]?.step ?? metadata.step);

          return (
            <div key={metadata.step} className="flex items-center flex-1">
              <StepIndicator
                metadata={metadata}
                status={status}
                onClick={() => handleStepClick(metadata.step)}
                disabled={disabled}
                compact={compact}
              />
              {!isLastStep && (
                <ProgressConnector isComplete={isConnectorComplete} compact={compact} />
              )}
            </div>
          );
        })}
      </div>

      {/* Step descriptions (optional) */}
      {showDescriptions && !compact && (
        <div className="mt-6 text-center">
          <p className="text-sm text-gray-600">
            {STEP_DESCRIPTIONS[currentStep]}
          </p>
        </div>
      )}
    </nav>
  );
}