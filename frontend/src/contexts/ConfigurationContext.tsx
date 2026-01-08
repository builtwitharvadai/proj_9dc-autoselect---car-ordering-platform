import React, { createContext, useContext, useCallback, useMemo, useReducer, useEffect } from 'react';
import {
  ConfigurationState,
  ConfigurationStep,
  PricingBreakdown,
  ConfigurationValidationResult,
  ConfigurationValidationError,
  PartialConfigurationState,
  CONFIGURATION_STEP_ORDER,
} from '../types/configuration';

/**
 * Configuration context state with actions
 */
interface ConfigurationContextState extends ConfigurationState {
  readonly isLoading: boolean;
  readonly error: string | null;
}

/**
 * Configuration context actions
 */
interface ConfigurationContextActions {
  readonly setTrim: (trimId: string) => void;
  readonly setColor: (colorId: string) => void;
  readonly addPackage: (packageId: string) => void;
  readonly removePackage: (packageId: string) => void;
  readonly togglePackage: (packageId: string) => void;
  readonly addOption: (optionId: string) => void;
  readonly removeOption: (optionId: string) => void;
  readonly toggleOption: (optionId: string) => void;
  readonly setCurrentStep: (step: ConfigurationStep) => void;
  readonly nextStep: () => void;
  readonly previousStep: () => void;
  readonly goToStep: (step: ConfigurationStep) => void;
  readonly updatePricing: (pricing: PricingBreakdown) => void;
  readonly updateValidation: (validation: ConfigurationValidationResult) => void;
  readonly addValidationError: (error: ConfigurationValidationError) => void;
  readonly clearValidationErrors: () => void;
  readonly setNotes: (notes: string) => void;
  readonly resetConfiguration: () => void;
  readonly updateConfiguration: (updates: PartialConfigurationState) => void;
  readonly markStepComplete: (step: ConfigurationStep) => void;
  readonly canProceedToNextStep: () => boolean;
  readonly canGoToPreviousStep: () => boolean;
  readonly isStepAccessible: (step: ConfigurationStep) => boolean;
}

/**
 * Combined context value
 */
interface ConfigurationContextValue {
  readonly state: ConfigurationContextState;
  readonly actions: ConfigurationContextActions;
}

/**
 * Configuration action types
 */
type ConfigurationAction =
  | { readonly type: 'SET_TRIM'; readonly payload: string }
  | { readonly type: 'SET_COLOR'; readonly payload: string }
  | { readonly type: 'ADD_PACKAGE'; readonly payload: string }
  | { readonly type: 'REMOVE_PACKAGE'; readonly payload: string }
  | { readonly type: 'ADD_OPTION'; readonly payload: string }
  | { readonly type: 'REMOVE_OPTION'; readonly payload: string }
  | { readonly type: 'SET_CURRENT_STEP'; readonly payload: ConfigurationStep }
  | { readonly type: 'MARK_STEP_COMPLETE'; readonly payload: ConfigurationStep }
  | { readonly type: 'UPDATE_PRICING'; readonly payload: PricingBreakdown }
  | { readonly type: 'UPDATE_VALIDATION'; readonly payload: ConfigurationValidationResult }
  | { readonly type: 'ADD_VALIDATION_ERROR'; readonly payload: ConfigurationValidationError }
  | { readonly type: 'CLEAR_VALIDATION_ERRORS' }
  | { readonly type: 'SET_NOTES'; readonly payload: string }
  | { readonly type: 'RESET_CONFIGURATION' }
  | { readonly type: 'UPDATE_CONFIGURATION'; readonly payload: PartialConfigurationState }
  | { readonly type: 'SET_LOADING'; readonly payload: boolean }
  | { readonly type: 'SET_ERROR'; readonly payload: string | null };

/**
 * Configuration provider props
 */
interface ConfigurationProviderProps {
  readonly children: React.ReactNode;
  readonly vehicleId: string;
  readonly initialState?: Partial<ConfigurationState>;
  readonly onStateChange?: (state: ConfigurationState) => void;
  readonly enablePersistence?: boolean;
}

/**
 * Create configuration context
 */
const ConfigurationContext = createContext<ConfigurationContextValue | undefined>(undefined);

/**
 * Get initial configuration state
 */
function getInitialState(
  vehicleId: string,
  initialState?: Partial<ConfigurationState>,
): ConfigurationContextState {
  const now = new Date().toISOString();

  return {
    vehicleId,
    trimId: initialState?.trimId,
    colorId: initialState?.colorId,
    selectedPackageIds: initialState?.selectedPackageIds ?? [],
    selectedOptionIds: initialState?.selectedOptionIds ?? [],
    currentStep: initialState?.currentStep ?? 'select-trim',
    completedSteps: initialState?.completedSteps ?? [],
    pricing: initialState?.pricing,
    validation: initialState?.validation,
    notes: initialState?.notes,
    createdAt: initialState?.createdAt ?? now,
    updatedAt: now,
    isLoading: false,
    error: null,
  };
}

/**
 * Configuration reducer
 */
function configurationReducer(
  state: ConfigurationContextState,
  action: ConfigurationAction,
): ConfigurationContextState {
  const now = new Date().toISOString();

  switch (action.type) {
    case 'SET_TRIM':
      return {
        ...state,
        trimId: action.payload,
        updatedAt: now,
      };

    case 'SET_COLOR':
      return {
        ...state,
        colorId: action.payload,
        updatedAt: now,
      };

    case 'ADD_PACKAGE':
      if (state.selectedPackageIds.includes(action.payload)) {
        return state;
      }
      return {
        ...state,
        selectedPackageIds: [...state.selectedPackageIds, action.payload],
        updatedAt: now,
      };

    case 'REMOVE_PACKAGE':
      return {
        ...state,
        selectedPackageIds: state.selectedPackageIds.filter((id) => id !== action.payload),
        updatedAt: now,
      };

    case 'ADD_OPTION':
      if (state.selectedOptionIds.includes(action.payload)) {
        return state;
      }
      return {
        ...state,
        selectedOptionIds: [...state.selectedOptionIds, action.payload],
        updatedAt: now,
      };

    case 'REMOVE_OPTION':
      return {
        ...state,
        selectedOptionIds: state.selectedOptionIds.filter((id) => id !== action.payload),
        updatedAt: now,
      };

    case 'SET_CURRENT_STEP':
      return {
        ...state,
        currentStep: action.payload,
        updatedAt: now,
      };

    case 'MARK_STEP_COMPLETE':
      if (state.completedSteps.includes(action.payload)) {
        return state;
      }
      return {
        ...state,
        completedSteps: [...state.completedSteps, action.payload],
        updatedAt: now,
      };

    case 'UPDATE_PRICING':
      return {
        ...state,
        pricing: action.payload,
        updatedAt: now,
      };

    case 'UPDATE_VALIDATION':
      return {
        ...state,
        validation: action.payload,
        updatedAt: now,
      };

    case 'ADD_VALIDATION_ERROR':
      return {
        ...state,
        validation: state.validation
          ? {
              ...state.validation,
              errors: [...state.validation.errors, action.payload],
              isValid: false,
            }
          : {
              isValid: false,
              errors: [action.payload],
              warnings: [],
              missingRequiredOptions: [],
              incompatibleSelections: [],
            },
        updatedAt: now,
      };

    case 'CLEAR_VALIDATION_ERRORS':
      return {
        ...state,
        validation: state.validation
          ? {
              ...state.validation,
              errors: [],
              warnings: [],
              isValid: true,
            }
          : undefined,
        updatedAt: now,
      };

    case 'SET_NOTES':
      return {
        ...state,
        notes: action.payload,
        updatedAt: now,
      };

    case 'RESET_CONFIGURATION':
      return getInitialState(state.vehicleId);

    case 'UPDATE_CONFIGURATION':
      return {
        ...state,
        ...action.payload,
        updatedAt: now,
      };

    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };

    case 'SET_ERROR':
      return {
        ...state,
        error: action.payload,
      };

    default:
      return state;
  }
}

/**
 * Get storage key for configuration persistence
 */
function getStorageKey(vehicleId: string): string {
  return `vehicle-configuration-${vehicleId}`;
}

/**
 * Load configuration from storage
 */
function loadFromStorage(vehicleId: string): Partial<ConfigurationState> | null {
  try {
    const stored = localStorage.getItem(getStorageKey(vehicleId));
    if (!stored) {
      return null;
    }
    return JSON.parse(stored) as Partial<ConfigurationState>;
  } catch (error) {
    console.error('Failed to load configuration from storage:', error);
    return null;
  }
}

/**
 * Save configuration to storage
 */
function saveToStorage(vehicleId: string, state: ConfigurationState): void {
  try {
    const toStore: ConfigurationState = {
      vehicleId: state.vehicleId,
      trimId: state.trimId,
      colorId: state.colorId,
      selectedPackageIds: state.selectedPackageIds,
      selectedOptionIds: state.selectedOptionIds,
      currentStep: state.currentStep,
      completedSteps: state.completedSteps,
      pricing: state.pricing,
      validation: state.validation,
      notes: state.notes,
      createdAt: state.createdAt,
      updatedAt: state.updatedAt,
    };
    localStorage.setItem(getStorageKey(vehicleId), JSON.stringify(toStore));
  } catch (error) {
    console.error('Failed to save configuration to storage:', error);
  }
}

/**
 * Configuration provider component
 */
export function ConfigurationProvider({
  children,
  vehicleId,
  initialState,
  onStateChange,
  enablePersistence = true,
}: ConfigurationProviderProps): JSX.Element {
  const [state, dispatch] = useReducer(
    configurationReducer,
    getInitialState(
      vehicleId,
      enablePersistence ? { ...loadFromStorage(vehicleId), ...initialState } : initialState,
    ),
  );

  useEffect(() => {
    if (enablePersistence) {
      saveToStorage(vehicleId, state);
    }
  }, [vehicleId, state, enablePersistence]);

  useEffect(() => {
    if (onStateChange) {
      const { isLoading: _isLoading, error: _error, ...configState } = state;
      onStateChange(configState);
    }
  }, [state, onStateChange]);

  const setTrim = useCallback((trimId: string) => {
    dispatch({ type: 'SET_TRIM', payload: trimId });
  }, []);

  const setColor = useCallback((colorId: string) => {
    dispatch({ type: 'SET_COLOR', payload: colorId });
  }, []);

  const addPackage = useCallback((packageId: string) => {
    dispatch({ type: 'ADD_PACKAGE', payload: packageId });
  }, []);

  const removePackage = useCallback((packageId: string) => {
    dispatch({ type: 'REMOVE_PACKAGE', payload: packageId });
  }, []);

  const togglePackage = useCallback((packageId: string) => {
    if (state.selectedPackageIds.includes(packageId)) {
      dispatch({ type: 'REMOVE_PACKAGE', payload: packageId });
    } else {
      dispatch({ type: 'ADD_PACKAGE', payload: packageId });
    }
  }, [state.selectedPackageIds]);

  const addOption = useCallback((optionId: string) => {
    dispatch({ type: 'ADD_OPTION', payload: optionId });
  }, []);

  const removeOption = useCallback((optionId: string) => {
    dispatch({ type: 'REMOVE_OPTION', payload: optionId });
  }, []);

  const toggleOption = useCallback((optionId: string) => {
    if (state.selectedOptionIds.includes(optionId)) {
      dispatch({ type: 'REMOVE_OPTION', payload: optionId });
    } else {
      dispatch({ type: 'ADD_OPTION', payload: optionId });
    }
  }, [state.selectedOptionIds]);

  const setCurrentStep = useCallback((step: ConfigurationStep) => {
    dispatch({ type: 'SET_CURRENT_STEP', payload: step });
  }, []);

  const markStepComplete = useCallback((step: ConfigurationStep) => {
    dispatch({ type: 'MARK_STEP_COMPLETE', payload: step });
  }, []);

  const isStepAccessible = useCallback((step: ConfigurationStep): boolean => {
    const currentOrder = CONFIGURATION_STEP_ORDER[state.currentStep];
    const targetOrder = CONFIGURATION_STEP_ORDER[step];
    
    if (targetOrder <= currentOrder) {
      return true;
    }

    const previousStep = Object.entries(CONFIGURATION_STEP_ORDER).find(
      ([_s, order]) => order === targetOrder - 1,
    )?.[0] as ConfigurationStep | undefined;

    return previousStep ? state.completedSteps.includes(previousStep) : false;
  }, [state.currentStep, state.completedSteps]);

  const canProceedToNextStep = useCallback((): boolean => {
    const currentOrder = CONFIGURATION_STEP_ORDER[state.currentStep];
    const nextStep = Object.entries(CONFIGURATION_STEP_ORDER).find(
      ([_s, order]) => order === currentOrder + 1,
    )?.[0] as ConfigurationStep | undefined;

    if (!nextStep) {
      return false;
    }

    switch (state.currentStep) {
      case 'select-trim':
        return !!state.trimId;
      case 'choose-color':
        return !!state.colorId;
      case 'select-packages':
        return true;
      case 'add-features':
        return true;
      case 'review':
        return state.validation?.isValid ?? false;
      default:
        return false;
    }
  }, [state.currentStep, state.trimId, state.colorId, state.validation]);

  const canGoToPreviousStep = useCallback((): boolean => {
    const currentOrder = CONFIGURATION_STEP_ORDER[state.currentStep];
    return currentOrder > 1;
  }, [state.currentStep]);

  const nextStep = useCallback(() => {
    if (!canProceedToNextStep()) {
      return;
    }

    const currentOrder = CONFIGURATION_STEP_ORDER[state.currentStep];
    const nextStep = Object.entries(CONFIGURATION_STEP_ORDER).find(
      ([_s, order]) => order === currentOrder + 1,
    )?.[0] as ConfigurationStep | undefined;

    if (nextStep) {
      dispatch({ type: 'MARK_STEP_COMPLETE', payload: state.currentStep });
      dispatch({ type: 'SET_CURRENT_STEP', payload: nextStep });
    }
  }, [state.currentStep, canProceedToNextStep]);

  const previousStep = useCallback(() => {
    if (!canGoToPreviousStep()) {
      return;
    }

    const currentOrder = CONFIGURATION_STEP_ORDER[state.currentStep];
    const prevStep = Object.entries(CONFIGURATION_STEP_ORDER).find(
      ([_s, order]) => order === currentOrder - 1,
    )?.[0] as ConfigurationStep | undefined;

    if (prevStep) {
      dispatch({ type: 'SET_CURRENT_STEP', payload: prevStep });
    }
  }, [state.currentStep, canGoToPreviousStep]);

  const goToStep = useCallback((step: ConfigurationStep) => {
    if (isStepAccessible(step)) {
      dispatch({ type: 'SET_CURRENT_STEP', payload: step });
    }
  }, [isStepAccessible]);

  const updatePricing = useCallback((pricing: PricingBreakdown) => {
    dispatch({ type: 'UPDATE_PRICING', payload: pricing });
  }, []);

  const updateValidation = useCallback((validation: ConfigurationValidationResult) => {
    dispatch({ type: 'UPDATE_VALIDATION', payload: validation });
  }, []);

  const addValidationError = useCallback((error: ConfigurationValidationError) => {
    dispatch({ type: 'ADD_VALIDATION_ERROR', payload: error });
  }, []);

  const clearValidationErrors = useCallback(() => {
    dispatch({ type: 'CLEAR_VALIDATION_ERRORS' });
  }, []);

  const setNotes = useCallback((notes: string) => {
    dispatch({ type: 'SET_NOTES', payload: notes });
  }, []);

  const resetConfiguration = useCallback(() => {
    dispatch({ type: 'RESET_CONFIGURATION' });
  }, []);

  const updateConfiguration = useCallback((updates: PartialConfigurationState) => {
    dispatch({ type: 'UPDATE_CONFIGURATION', payload: updates });
  }, []);

  const actions = useMemo<ConfigurationContextActions>(
    () => ({
      setTrim,
      setColor,
      addPackage,
      removePackage,
      togglePackage,
      addOption,
      removeOption,
      toggleOption,
      setCurrentStep,
      nextStep,
      previousStep,
      goToStep,
      updatePricing,
      updateValidation,
      addValidationError,
      clearValidationErrors,
      setNotes,
      resetConfiguration,
      updateConfiguration,
      markStepComplete,
      canProceedToNextStep,
      canGoToPreviousStep,
      isStepAccessible,
    }),
    [
      setTrim,
      setColor,
      addPackage,
      removePackage,
      togglePackage,
      addOption,
      removeOption,
      toggleOption,
      setCurrentStep,
      nextStep,
      previousStep,
      goToStep,
      updatePricing,
      updateValidation,
      addValidationError,
      clearValidationErrors,
      setNotes,
      resetConfiguration,
      updateConfiguration,
      markStepComplete,
      canProceedToNextStep,
      canGoToPreviousStep,
      isStepAccessible,
    ],
  );

  const value = useMemo<ConfigurationContextValue>(
    () => ({
      state,
      actions,
    }),
    [state, actions],
  );

  return <ConfigurationContext.Provider value={value}>{children}</ConfigurationContext.Provider>;
}

/**
 * Hook to use configuration context
 */
export function useConfiguration(): ConfigurationContextValue {
  const context = useContext(ConfigurationContext);
  if (!context) {
    throw new Error('useConfiguration must be used within ConfigurationProvider');
  }
  return context;
}

/**
 * Hook to use configuration state only
 */
export function useConfigurationState(): ConfigurationContextState {
  const { state } = useConfiguration();
  return state;
}

/**
 * Hook to use configuration actions only
 */
export function useConfigurationActions(): ConfigurationContextActions {
  const { actions } = useConfiguration();
  return actions;
}