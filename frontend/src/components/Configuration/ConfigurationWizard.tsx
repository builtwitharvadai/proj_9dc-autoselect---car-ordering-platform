import React, { useCallback, useMemo } from 'react';
import { useConfiguration } from '../../contexts/ConfigurationContext';
import {
  ConfigurationStep,
  CONFIGURATION_STEP_ORDER,
  CONFIGURATION_STEP_TITLES,
} from '../../types/configuration';

/**
 * Configuration wizard props
 */
interface ConfigurationWizardProps {
  readonly vehicleId: string;
  readonly className?: string;
  readonly onComplete?: () => void;
  readonly onCancel?: () => void;
  readonly enablePersistence?: boolean;
}

/**
 * Step component props
 */
interface StepComponentProps {
  readonly onNext: () => void;
  readonly onPrevious: () => void;
  readonly canProceed: boolean;
  readonly canGoBack: boolean;
}

/**
 * Progress indicator component
 */
function ProgressIndicator({
  currentStep,
  completedSteps,
  onStepClick,
}: {
  readonly currentStep: ConfigurationStep;
  readonly completedSteps: readonly ConfigurationStep[];
  readonly onStepClick: (step: ConfigurationStep) => void;
}): JSX.Element {
  const steps = useMemo(
    () =>
      (Object.keys(CONFIGURATION_STEP_ORDER) as ConfigurationStep[]).sort(
        (a, b) => CONFIGURATION_STEP_ORDER[a] - CONFIGURATION_STEP_ORDER[b],
      ),
    [],
  );

  const currentStepIndex = useMemo(
    () => steps.indexOf(currentStep),
    [steps, currentStep],
  );

  const getStepStatus = useCallback(
    (step: ConfigurationStep): 'completed' | 'current' | 'upcoming' => {
      if (completedSteps.includes(step)) {
        return 'completed';
      }
      if (step === currentStep) {
        return 'current';
      }
      return 'upcoming';
    },
    [completedSteps, currentStep],
  );

  const isStepClickable = useCallback(
    (step: ConfigurationStep): boolean => {
      const stepIndex = steps.indexOf(step);
      return stepIndex <= currentStepIndex || completedSteps.includes(step);
    },
    [steps, currentStepIndex, completedSteps],
  );

  return (
    <nav aria-label="Configuration progress" className="mb-8">
      <ol className="flex items-center justify-between">
        {steps.map((step, index) => {
          const status = getStepStatus(step);
          const isClickable = isStepClickable(step);
          const isLast = index === steps.length - 1;

          return (
            <li
              key={step}
              className={`flex items-center ${!isLast ? 'flex-1' : ''}`}
            >
              <button
                type="button"
                onClick={() => isClickable && onStepClick(step)}
                disabled={!isClickable}
                className={`flex items-center ${
                  isClickable ? 'cursor-pointer' : 'cursor-not-allowed'
                }`}
                aria-current={status === 'current' ? 'step' : undefined}
              >
                <span
                  className={`flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors ${
                    status === 'completed'
                      ? 'border-green-600 bg-green-600 text-white'
                      : status === 'current'
                        ? 'border-blue-600 bg-blue-600 text-white'
                        : 'border-gray-300 bg-white text-gray-500'
                  }`}
                >
                  {status === 'completed' ? (
                    <svg
                      className="h-6 w-6"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
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
                    <span className="text-sm font-semibold">
                      {CONFIGURATION_STEP_ORDER[step]}
                    </span>
                  )}
                </span>
                <span
                  className={`ml-3 text-sm font-medium ${
                    status === 'current'
                      ? 'text-blue-600'
                      : status === 'completed'
                        ? 'text-gray-900'
                        : 'text-gray-500'
                  }`}
                >
                  {CONFIGURATION_STEP_TITLES[step]}
                </span>
              </button>
              {!isLast && (
                <div
                  className={`mx-4 h-0.5 flex-1 transition-colors ${
                    completedSteps.includes(step)
                      ? 'bg-green-600'
                      : 'bg-gray-300'
                  }`}
                  aria-hidden="true"
                />
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

/**
 * Step navigation component
 */
function StepNavigation({
  onNext,
  onPrevious,
  onCancel,
  canProceed,
  canGoBack,
  isLastStep,
}: {
  readonly onNext: () => void;
  readonly onPrevious: () => void;
  readonly onCancel?: () => void;
  readonly canProceed: boolean;
  readonly canGoBack: boolean;
  readonly isLastStep: boolean;
}): JSX.Element {
  return (
    <div className="mt-8 flex items-center justify-between border-t border-gray-200 pt-6">
      <div>
        {canGoBack && (
          <button
            type="button"
            onClick={onPrevious}
            className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            <svg
              className="-ml-1 mr-2 h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 19l-7-7 7-7"
              />
            </svg>
            Previous
          </button>
        )}
      </div>
      <div className="flex items-center space-x-3">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="inline-flex items-center rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
          >
            Cancel
          </button>
        )}
        <button
          type="button"
          onClick={onNext}
          disabled={!canProceed}
          className={`inline-flex items-center rounded-md border border-transparent px-4 py-2 text-sm font-medium text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 ${
            canProceed
              ? 'bg-blue-600 hover:bg-blue-700'
              : 'cursor-not-allowed bg-gray-400'
          }`}
        >
          {isLastStep ? 'Complete' : 'Next'}
          {!isLastStep && (
            <svg
              className="-mr-1 ml-2 h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          )}
        </button>
      </div>
    </div>
  );
}

/**
 * Main configuration wizard component
 */
export default function ConfigurationWizard({
  vehicleId,
  className = '',
  onComplete,
  onCancel,
  enablePersistence = true,
}: ConfigurationWizardProps): JSX.Element {
  const { state, actions } = useConfiguration();

  const steps = useMemo(
    () =>
      (Object.keys(CONFIGURATION_STEP_ORDER) as ConfigurationStep[]).sort(
        (a, b) => CONFIGURATION_STEP_ORDER[a] - CONFIGURATION_STEP_ORDER[b],
      ),
    [],
  );

  const currentStepIndex = useMemo(
    () => steps.indexOf(state.currentStep),
    [steps, state.currentStep],
  );

  const isLastStep = useMemo(
    () => currentStepIndex === steps.length - 1,
    [currentStepIndex, steps.length],
  );

  const canProceed = useMemo(
    () => actions.canProceedToNextStep(),
    [actions],
  );

  const canGoBack = useMemo(
    () => actions.canGoToPreviousStep(),
    [actions],
  );

  const handleNext = useCallback(() => {
    if (isLastStep && onComplete) {
      onComplete();
    } else {
      actions.nextStep();
    }
  }, [isLastStep, onComplete, actions]);

  const handlePrevious = useCallback(() => {
    actions.previousStep();
  }, [actions]);

  const handleStepClick = useCallback(
    (step: ConfigurationStep) => {
      if (actions.isStepAccessible(step)) {
        actions.goToStep(step);
      }
    },
    [actions],
  );

  const renderStepContent = useCallback((): JSX.Element => {
    const stepProps: StepComponentProps = {
      onNext: handleNext,
      onPrevious: handlePrevious,
      canProceed,
      canGoBack,
    };

    switch (state.currentStep) {
      case 'select-trim':
        return (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Select Trim Level
            </h2>
            <p className="text-gray-600">
              Trim selection component will be rendered here
            </p>
          </div>
        );

      case 'choose-color':
        return (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Choose Color
            </h2>
            <p className="text-gray-600">
              Color selection component will be rendered here
            </p>
          </div>
        );

      case 'select-packages':
        return (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Select Packages
            </h2>
            <p className="text-gray-600">
              Package selection component will be rendered here
            </p>
          </div>
        );

      case 'add-features':
        return (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Add Features
            </h2>
            <p className="text-gray-600">
              Feature selection component will be rendered here
            </p>
          </div>
        );

      case 'review':
        return (
          <div className="rounded-lg border border-gray-200 bg-white p-6">
            <h2 className="mb-4 text-xl font-semibold text-gray-900">
              Review Configuration
            </h2>
            <p className="text-gray-600">
              Configuration review component will be rendered here
            </p>
          </div>
        );

      default:
        return (
          <div className="rounded-lg border border-red-200 bg-red-50 p-6">
            <p className="text-red-600">Unknown step: {state.currentStep}</p>
          </div>
        );
    }
  }, [state.currentStep, handleNext, handlePrevious, canProceed, canGoBack]);

  return (
    <div className={`mx-auto max-w-7xl ${className}`}>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">
          Configure Your Vehicle
        </h1>
        <p className="mt-2 text-gray-600">
          Customize your vehicle by following the steps below
        </p>
      </div>

      <ProgressIndicator
        currentStep={state.currentStep}
        completedSteps={state.completedSteps}
        onStepClick={handleStepClick}
      />

      <div className="mb-8">
        {state.validation && !state.validation.isValid && (
          <div
            className="mb-4 rounded-md border border-red-200 bg-red-50 p-4"
            role="alert"
          >
            <div className="flex">
              <div className="flex-shrink-0">
                <svg
                  className="h-5 w-5 text-red-400"
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
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Validation Errors
                </h3>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-red-700">
                  {state.validation.errors.map((error, index) => (
                    <li key={index}>{error.message}</li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        )}

        {renderStepContent()}
      </div>

      <StepNavigation
        onNext={handleNext}
        onPrevious={handlePrevious}
        onCancel={onCancel}
        canProceed={canProceed}
        canGoBack={canGoBack}
        isLastStep={isLastStep}
      />
    </div>
  );
}