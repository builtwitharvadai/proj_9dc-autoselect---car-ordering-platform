import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ConfigurationWizard from '../../../components/Configuration/ConfigurationWizard';
import { ConfigurationProvider } from '../../../contexts/ConfigurationContext';
import type {
  ConfigurationStep,
  ConfigurationState,
  ConfigurationActions,
} from '../../../types/configuration';

// ============================================================================
// 🎭 Test Utilities and Mocks
// ============================================================================

/**
 * Mock configuration context state factory
 */
const createMockState = (overrides?: Partial<ConfigurationState>): ConfigurationState => ({
  currentStep: 'select-trim',
  completedSteps: [],
  selectedTrim: null,
  selectedColor: null,
  selectedPackages: [],
  selectedFeatures: [],
  validation: {
    isValid: true,
    errors: [],
  },
  totalPrice: 0,
  ...overrides,
});

/**
 * Mock configuration context actions factory
 */
const createMockActions = (overrides?: Partial<ConfigurationActions>): ConfigurationActions => ({
  nextStep: vi.fn(),
  previousStep: vi.fn(),
  goToStep: vi.fn(),
  canProceedToNextStep: vi.fn(() => true),
  canGoToPreviousStep: vi.fn(() => true),
  isStepAccessible: vi.fn(() => true),
  selectTrim: vi.fn(),
  selectColor: vi.fn(),
  togglePackage: vi.fn(),
  toggleFeature: vi.fn(),
  validateConfiguration: vi.fn(),
  resetConfiguration: vi.fn(),
  ...overrides,
});

/**
 * Mock useConfiguration hook
 */
const mockUseConfiguration = vi.fn();

vi.mock('../../../contexts/ConfigurationContext', async () => {
  const actual = await vi.importActual<typeof import('../../../contexts/ConfigurationContext')>(
    '../../../contexts/ConfigurationContext',
  );
  return {
    ...actual,
    useConfiguration: () => mockUseConfiguration(),
  };
});

/**
 * Render component with configuration context
 */
const renderWithContext = (
  props: Partial<React.ComponentProps<typeof ConfigurationWizard>> = {},
  state?: Partial<ConfigurationState>,
  actions?: Partial<ConfigurationActions>,
) => {
  const mockState = createMockState(state);
  const mockActions = createMockActions(actions);

  mockUseConfiguration.mockReturnValue({
    state: mockState,
    actions: mockActions,
  });

  const defaultProps = {
    vehicleId: 'test-vehicle-123',
    ...props,
  };

  return {
    ...render(<ConfigurationWizard {...defaultProps} />),
    mockState,
    mockActions,
  };
};

// ============================================================================
// 🧪 Test Suite
// ============================================================================

describe('ConfigurationWizard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==========================================================================
  // 🎯 Unit Tests - Component Rendering
  // ==========================================================================

  describe('Component Rendering', () => {
    it('should render wizard with title and description', () => {
      renderWithContext();

      expect(screen.getByText('Configure Your Vehicle')).toBeInTheDocument();
      expect(
        screen.getByText('Customize your vehicle by following the steps below'),
      ).toBeInTheDocument();
    });

    it('should render progress indicator with all steps', () => {
      renderWithContext();

      const progressNav = screen.getByRole('navigation', { name: /configuration progress/i });
      expect(progressNav).toBeInTheDocument();

      // Verify all steps are rendered
      expect(within(progressNav).getByText('Select Trim')).toBeInTheDocument();
      expect(within(progressNav).getByText('Choose Color')).toBeInTheDocument();
      expect(within(progressNav).getByText('Select Packages')).toBeInTheDocument();
      expect(within(progressNav).getByText('Add Features')).toBeInTheDocument();
      expect(within(progressNav).getByText('Review')).toBeInTheDocument();
    });

    it('should render current step content', () => {
      renderWithContext();

      expect(screen.getByText('Select Trim Level')).toBeInTheDocument();
      expect(screen.getByText('Trim selection component will be rendered here')).toBeInTheDocument();
    });

    it('should render navigation buttons', () => {
      renderWithContext();

      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
    });

    it('should apply custom className', () => {
      const { container } = renderWithContext({ className: 'custom-class' });

      const wizardContainer = container.firstChild as HTMLElement;
      expect(wizardContainer).toHaveClass('custom-class');
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Progress Indicator
  // ==========================================================================

  describe('Progress Indicator', () => {
    it('should highlight current step', () => {
      renderWithContext({}, { currentStep: 'choose-color' });

      const colorStepButton = screen.getByRole('button', { name: /choose color/i });
      expect(colorStepButton).toHaveAttribute('aria-current', 'step');
    });

    it('should show completed steps with checkmark', () => {
      renderWithContext(
        {},
        {
          currentStep: 'select-packages',
          completedSteps: ['select-trim', 'choose-color'],
        },
      );

      const progressNav = screen.getByRole('navigation', { name: /configuration progress/i });
      const checkmarks = within(progressNav).getAllByRole('img', { hidden: true });

      // Should have checkmarks for completed steps
      expect(checkmarks.length).toBeGreaterThanOrEqual(2);
    });

    it('should show step numbers for incomplete steps', () => {
      renderWithContext();

      const progressNav = screen.getByRole('navigation', { name: /configuration progress/i });

      // Step numbers should be visible
      expect(within(progressNav).getByText('1')).toBeInTheDocument();
      expect(within(progressNav).getByText('2')).toBeInTheDocument();
    });

    it('should enable clicking on accessible steps', () => {
      const mockActions = createMockActions({
        isStepAccessible: vi.fn((step: ConfigurationStep) => step === 'select-trim'),
      });

      renderWithContext({}, { currentStep: 'choose-color' }, mockActions);

      const trimStepButton = screen.getByRole('button', { name: /select trim/i });
      expect(trimStepButton).not.toBeDisabled();
    });

    it('should disable clicking on inaccessible steps', () => {
      const mockActions = createMockActions({
        isStepAccessible: vi.fn(() => false),
      });

      renderWithContext({}, { currentStep: 'select-trim' }, mockActions);

      const colorStepButton = screen.getByRole('button', { name: /choose color/i });
      expect(colorStepButton).toBeDisabled();
    });

    it('should call goToStep when clicking accessible step', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        isStepAccessible: vi.fn(() => true),
      });

      renderWithContext({}, { currentStep: 'choose-color' }, mockActions);

      const trimStepButton = screen.getByRole('button', { name: /select trim/i });
      await user.click(trimStepButton);

      expect(mockActions.goToStep).toHaveBeenCalledWith('select-trim');
    });

    it('should not call goToStep when clicking inaccessible step', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        isStepAccessible: vi.fn(() => false),
      });

      renderWithContext({}, { currentStep: 'select-trim' }, mockActions);

      const reviewStepButton = screen.getByRole('button', { name: /review/i });
      await user.click(reviewStepButton);

      expect(mockActions.goToStep).not.toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Step Navigation
  // ==========================================================================

  describe('Step Navigation', () => {
    it('should show Next button on non-final steps', () => {
      renderWithContext({}, { currentStep: 'select-trim' });

      const nextButton = screen.getByRole('button', { name: /next/i });
      expect(nextButton).toBeInTheDocument();
      expect(nextButton).toHaveTextContent('Next');
    });

    it('should show Complete button on final step', () => {
      renderWithContext({}, { currentStep: 'review' });

      const completeButton = screen.getByRole('button', { name: /complete/i });
      expect(completeButton).toBeInTheDocument();
      expect(completeButton).toHaveTextContent('Complete');
    });

    it('should enable Next button when can proceed', () => {
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
      });

      renderWithContext({}, {}, mockActions);

      const nextButton = screen.getByRole('button', { name: /next/i });
      expect(nextButton).not.toBeDisabled();
    });

    it('should disable Next button when cannot proceed', () => {
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => false),
      });

      renderWithContext({}, {}, mockActions);

      const nextButton = screen.getByRole('button', { name: /next/i });
      expect(nextButton).toBeDisabled();
    });

    it('should call nextStep when clicking Next', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
      });

      renderWithContext({}, {}, mockActions);

      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      expect(mockActions.nextStep).toHaveBeenCalledTimes(1);
    });

    it('should call onComplete when clicking Complete on final step', async () => {
      const user = userEvent.setup();
      const onComplete = vi.fn();
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
      });

      renderWithContext({ onComplete }, { currentStep: 'review' }, mockActions);

      const completeButton = screen.getByRole('button', { name: /complete/i });
      await user.click(completeButton);

      expect(onComplete).toHaveBeenCalledTimes(1);
      expect(mockActions.nextStep).not.toHaveBeenCalled();
    });

    it('should show Previous button when can go back', () => {
      const mockActions = createMockActions({
        canGoToPreviousStep: vi.fn(() => true),
      });

      renderWithContext({}, { currentStep: 'choose-color' }, mockActions);

      expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument();
    });

    it('should hide Previous button when cannot go back', () => {
      const mockActions = createMockActions({
        canGoToPreviousStep: vi.fn(() => false),
      });

      renderWithContext({}, { currentStep: 'select-trim' }, mockActions);

      expect(screen.queryByRole('button', { name: /previous/i })).not.toBeInTheDocument();
    });

    it('should call previousStep when clicking Previous', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        canGoToPreviousStep: vi.fn(() => true),
      });

      renderWithContext({}, { currentStep: 'choose-color' }, mockActions);

      const previousButton = screen.getByRole('button', { name: /previous/i });
      await user.click(previousButton);

      expect(mockActions.previousStep).toHaveBeenCalledTimes(1);
    });

    it('should show Cancel button when onCancel provided', () => {
      const onCancel = vi.fn();

      renderWithContext({ onCancel });

      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('should hide Cancel button when onCancel not provided', () => {
      renderWithContext();

      expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    });

    it('should call onCancel when clicking Cancel', async () => {
      const user = userEvent.setup();
      const onCancel = vi.fn();

      renderWithContext({ onCancel });

      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      expect(onCancel).toHaveBeenCalledTimes(1);
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Step Content Rendering
  // ==========================================================================

  describe('Step Content Rendering', () => {
    it('should render select-trim step content', () => {
      renderWithContext({}, { currentStep: 'select-trim' });

      expect(screen.getByText('Select Trim Level')).toBeInTheDocument();
    });

    it('should render choose-color step content', () => {
      renderWithContext({}, { currentStep: 'choose-color' });

      expect(screen.getByText('Choose Color')).toBeInTheDocument();
    });

    it('should render select-packages step content', () => {
      renderWithContext({}, { currentStep: 'select-packages' });

      expect(screen.getByText('Select Packages')).toBeInTheDocument();
    });

    it('should render add-features step content', () => {
      renderWithContext({}, { currentStep: 'add-features' });

      expect(screen.getByText('Add Features')).toBeInTheDocument();
    });

    it('should render review step content', () => {
      renderWithContext({}, { currentStep: 'review' });

      expect(screen.getByText('Review Configuration')).toBeInTheDocument();
    });

    it('should render error for unknown step', () => {
      renderWithContext({}, { currentStep: 'invalid-step' as ConfigurationStep });

      expect(screen.getByText(/unknown step/i)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🎯 Unit Tests - Validation Display
  // ==========================================================================

  describe('Validation Display', () => {
    it('should not show validation errors when valid', () => {
      renderWithContext(
        {},
        {
          validation: {
            isValid: true,
            errors: [],
          },
        },
      );

      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('should show validation errors when invalid', () => {
      renderWithContext(
        {},
        {
          validation: {
            isValid: false,
            errors: [
              { field: 'trim', message: 'Please select a trim level' },
              { field: 'color', message: 'Please choose a color' },
            ],
          },
        },
      );

      const alert = screen.getByRole('alert');
      expect(alert).toBeInTheDocument();
      expect(within(alert).getByText('Validation Errors')).toBeInTheDocument();
    });

    it('should display all validation error messages', () => {
      const errors = [
        { field: 'trim', message: 'Please select a trim level' },
        { field: 'color', message: 'Please choose a color' },
        { field: 'packages', message: 'At least one package is required' },
      ];

      renderWithContext(
        {},
        {
          validation: {
            isValid: false,
            errors,
          },
        },
      );

      errors.forEach((error) => {
        expect(screen.getByText(error.message)).toBeInTheDocument();
      });
    });

    it('should show validation icon in error alert', () => {
      renderWithContext(
        {},
        {
          validation: {
            isValid: false,
            errors: [{ field: 'trim', message: 'Error message' }],
          },
        },
      );

      const alert = screen.getByRole('alert');
      const icon = within(alert).getByRole('img', { hidden: true });
      expect(icon).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🔗 Integration Tests - User Workflows
  // ==========================================================================

  describe('User Workflows', () => {
    it('should navigate through all steps sequentially', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
        canGoToPreviousStep: vi.fn(() => true),
      });

      const { rerender } = renderWithContext({}, { currentStep: 'select-trim' }, mockActions);

      // Step 1: Select Trim
      expect(screen.getByText('Select Trim Level')).toBeInTheDocument();
      await user.click(screen.getByRole('button', { name: /next/i }));
      expect(mockActions.nextStep).toHaveBeenCalled();

      // Simulate state change
      mockUseConfiguration.mockReturnValue({
        state: createMockState({ currentStep: 'choose-color' }),
        actions: mockActions,
      });
      rerender(<ConfigurationWizard vehicleId="test-vehicle-123" />);

      // Step 2: Choose Color
      expect(screen.getByText('Choose Color')).toBeInTheDocument();
    });

    it('should navigate backwards through steps', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        canGoToPreviousStep: vi.fn(() => true),
      });

      renderWithContext({}, { currentStep: 'choose-color' }, mockActions);

      await user.click(screen.getByRole('button', { name: /previous/i }));

      expect(mockActions.previousStep).toHaveBeenCalledTimes(1);
    });

    it('should complete configuration on final step', async () => {
      const user = userEvent.setup();
      const onComplete = vi.fn();
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
      });

      renderWithContext({ onComplete }, { currentStep: 'review' }, mockActions);

      await user.click(screen.getByRole('button', { name: /complete/i }));

      expect(onComplete).toHaveBeenCalledTimes(1);
    });

    it('should cancel configuration workflow', async () => {
      const user = userEvent.setup();
      const onCancel = vi.fn();

      renderWithContext({ onCancel });

      await user.click(screen.getByRole('button', { name: /cancel/i }));

      expect(onCancel).toHaveBeenCalledTimes(1);
    });

    it('should jump to accessible step via progress indicator', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        isStepAccessible: vi.fn(() => true),
      });

      renderWithContext(
        {},
        {
          currentStep: 'select-packages',
          completedSteps: ['select-trim', 'choose-color'],
        },
        mockActions,
      );

      const colorStepButton = screen.getByRole('button', { name: /choose color/i });
      await user.click(colorStepButton);

      expect(mockActions.goToStep).toHaveBeenCalledWith('choose-color');
    });
  });

  // ==========================================================================
  // 🛡️ Accessibility Tests
  // ==========================================================================

  describe('Accessibility', () => {
    it('should have proper ARIA labels for navigation', () => {
      renderWithContext();

      expect(screen.getByRole('navigation', { name: /configuration progress/i })).toBeInTheDocument();
    });

    it('should mark current step with aria-current', () => {
      renderWithContext({}, { currentStep: 'choose-color' });

      const currentStepButton = screen.getByRole('button', { name: /choose color/i });
      expect(currentStepButton).toHaveAttribute('aria-current', 'step');
    });

    it('should have proper role for validation alerts', () => {
      renderWithContext(
        {},
        {
          validation: {
            isValid: false,
            errors: [{ field: 'trim', message: 'Error' }],
          },
        },
      );

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('should have accessible button labels', () => {
      const mockActions = createMockActions({
        canGoToPreviousStep: vi.fn(() => true),
      });

      renderWithContext({ onCancel: vi.fn() }, {}, mockActions);

      expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });

    it('should hide decorative icons from screen readers', () => {
      renderWithContext();

      const icons = screen.getAllByRole('img', { hidden: true });
      icons.forEach((icon) => {
        expect(icon).toHaveAttribute('aria-hidden', 'true');
      });
    });

    it('should support keyboard navigation', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
      });

      renderWithContext({}, {}, mockActions);

      const nextButton = screen.getByRole('button', { name: /next/i });

      // Tab to button and press Enter
      await user.tab();
      await user.keyboard('{Enter}');

      expect(mockActions.nextStep).toHaveBeenCalled();
    });
  });

  // ==========================================================================
  // ⚡ Performance Tests
  // ==========================================================================

  describe('Performance', () => {
    it('should render within acceptable time', () => {
      const startTime = performance.now();

      renderWithContext();

      const endTime = performance.now();
      const renderTime = endTime - startTime;

      // Should render in less than 100ms
      expect(renderTime).toBeLessThan(100);
    });

    it('should not re-render unnecessarily on prop changes', () => {
      const { rerender } = renderWithContext({ vehicleId: 'vehicle-1' });

      const initialRenderCount = mockUseConfiguration.mock.calls.length;

      // Re-render with same props
      rerender(<ConfigurationWizard vehicleId="vehicle-1" />);

      // Should use memoization to prevent unnecessary re-renders
      expect(mockUseConfiguration.mock.calls.length).toBe(initialRenderCount);
    });

    it('should memoize step calculations', () => {
      const mockActions = createMockActions();

      const { rerender } = renderWithContext({}, {}, mockActions);

      const initialCallCount = mockActions.canProceedToNextStep.mock.calls.length;

      // Re-render without state changes
      rerender(<ConfigurationWizard vehicleId="test-vehicle-123" />);

      // Memoized values should not trigger recalculation
      expect(mockActions.canProceedToNextStep.mock.calls.length).toBe(initialCallCount);
    });
  });

  // ==========================================================================
  // 🎨 Visual Regression Tests
  // ==========================================================================

  describe('Visual States', () => {
    it('should apply correct styles to completed steps', () => {
      renderWithContext(
        {},
        {
          currentStep: 'select-packages',
          completedSteps: ['select-trim', 'choose-color'],
        },
      );

      const trimStepButton = screen.getByRole('button', { name: /select trim/i });
      const stepIndicator = trimStepButton.querySelector('span');

      expect(stepIndicator).toHaveClass('border-green-600', 'bg-green-600', 'text-white');
    });

    it('should apply correct styles to current step', () => {
      renderWithContext({}, { currentStep: 'choose-color' });

      const colorStepButton = screen.getByRole('button', { name: /choose color/i });
      const stepIndicator = colorStepButton.querySelector('span');

      expect(stepIndicator).toHaveClass('border-blue-600', 'bg-blue-600', 'text-white');
    });

    it('should apply correct styles to upcoming steps', () => {
      renderWithContext({}, { currentStep: 'select-trim' });

      const packagesStepButton = screen.getByRole('button', { name: /select packages/i });
      const stepIndicator = packagesStepButton.querySelector('span');

      expect(stepIndicator).toHaveClass('border-gray-300', 'bg-white', 'text-gray-500');
    });

    it('should apply disabled styles to Next button when cannot proceed', () => {
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => false),
      });

      renderWithContext({}, {}, mockActions);

      const nextButton = screen.getByRole('button', { name: /next/i });

      expect(nextButton).toHaveClass('cursor-not-allowed', 'bg-gray-400');
    });

    it('should apply enabled styles to Next button when can proceed', () => {
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
      });

      renderWithContext({}, {}, mockActions);

      const nextButton = screen.getByRole('button', { name: /next/i });

      expect(nextButton).toHaveClass('bg-blue-600', 'hover:bg-blue-700');
    });
  });

  // ==========================================================================
  // 🔍 Edge Cases and Error Scenarios
  // ==========================================================================

  describe('Edge Cases', () => {
    it('should handle empty completed steps array', () => {
      renderWithContext({}, { completedSteps: [] });

      expect(screen.getByText('Select Trim Level')).toBeInTheDocument();
    });

    it('should handle all steps completed', () => {
      renderWithContext(
        {},
        {
          currentStep: 'review',
          completedSteps: ['select-trim', 'choose-color', 'select-packages', 'add-features'],
        },
      );

      expect(screen.getByText('Review Configuration')).toBeInTheDocument();
    });

    it('should handle missing onComplete callback', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
      });

      renderWithContext({}, { currentStep: 'review' }, mockActions);

      const completeButton = screen.getByRole('button', { name: /complete/i });

      // Should not throw error
      await expect(user.click(completeButton)).resolves.not.toThrow();
    });

    it('should handle missing onCancel callback', () => {
      renderWithContext();

      // Cancel button should not be rendered
      expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    });

    it('should handle rapid navigation clicks', async () => {
      const user = userEvent.setup();
      const mockActions = createMockActions({
        canProceedToNextStep: vi.fn(() => true),
      });

      renderWithContext({}, {}, mockActions);

      const nextButton = screen.getByRole('button', { name: /next/i });

      // Click multiple times rapidly
      await user.click(nextButton);
      await user.click(nextButton);
      await user.click(nextButton);

      // Should handle gracefully without errors
      expect(mockActions.nextStep).toHaveBeenCalled();
    });

    it('should handle validation errors with empty message', () => {
      renderWithContext(
        {},
        {
          validation: {
            isValid: false,
            errors: [{ field: 'trim', message: '' }],
          },
        },
      );

      const alert = screen.getByRole('alert');
      expect(alert).toBeInTheDocument();
    });

    it('should handle very long validation error messages', () => {
      const longMessage = 'A'.repeat(500);

      renderWithContext(
        {},
        {
          validation: {
            isValid: false,
            errors: [{ field: 'trim', message: longMessage }],
          },
        },
      );

      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🔄 State Management Tests
  // ==========================================================================

  describe('State Management', () => {
    it('should reflect state changes from context', () => {
      const { rerender } = renderWithContext({}, { currentStep: 'select-trim' });

      expect(screen.getByText('Select Trim Level')).toBeInTheDocument();

      // Update state
      mockUseConfiguration.mockReturnValue({
        state: createMockState({ currentStep: 'choose-color' }),
        actions: createMockActions(),
      });

      rerender(<ConfigurationWizard vehicleId="test-vehicle-123" />);

      expect(screen.getByText('Choose Color')).toBeInTheDocument();
    });

    it('should update progress indicator when steps completed', () => {
      const { rerender } = renderWithContext({}, { completedSteps: [] });

      // Initially no completed steps
      let progressNav = screen.getByRole('navigation', { name: /configuration progress/i });
      expect(within(progressNav).queryByRole('img', { hidden: true })).not.toBeInTheDocument();

      // Update with completed steps
      mockUseConfiguration.mockReturnValue({
        state: createMockState({
          currentStep: 'choose-color',
          completedSteps: ['select-trim'],
        }),
        actions: createMockActions(),
      });

      rerender(<ConfigurationWizard vehicleId="test-vehicle-123" />);

      progressNav = screen.getByRole('navigation', { name: /configuration progress/i });
      expect(within(progressNav).getByRole('img', { hidden: true })).toBeInTheDocument();
    });

    it('should update navigation buttons based on state', () => {
      const mockActions = createMockActions({
        canGoToPreviousStep: vi.fn(() => false),
      });

      const { rerender } = renderWithContext({}, { currentStep: 'select-trim' }, mockActions);

      expect(screen.queryByRole('button', { name: /previous/i })).not.toBeInTheDocument();

      // Update to allow going back
      mockActions.canGoToPreviousStep = vi.fn(() => true);
      mockUseConfiguration.mockReturnValue({
        state: createMockState({ currentStep: 'choose-color' }),
        actions: mockActions,
      });

      rerender(<ConfigurationWizard vehicleId="test-vehicle-123" />);

      expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument();
    });
  });

  // ==========================================================================
  // 🎯 Props Validation Tests
  // ==========================================================================

  describe('Props Validation', () => {
    it('should accept valid vehicleId', () => {
      expect(() => renderWithContext({ vehicleId: 'valid-id-123' })).not.toThrow();
    });

    it('should accept optional className', () => {
      const { container } = renderWithContext({ className: 'test-class' });

      expect(container.firstChild).toHaveClass('test-class');
    });

    it('should accept optional onComplete callback', () => {
      const onComplete = vi.fn();

      expect(() => renderWithContext({ onComplete })).not.toThrow();
    });

    it('should accept optional onCancel callback', () => {
      const onCancel = vi.fn();

      expect(() => renderWithContext({ onCancel })).not.toThrow();
    });

    it('should accept optional enablePersistence flag', () => {
      expect(() => renderWithContext({ enablePersistence: true })).not.toThrow();
      expect(() => renderWithContext({ enablePersistence: false })).not.toThrow();
    });

    it('should use default values for optional props', () => {
      const { container } = renderWithContext();

      expect(container.firstChild).toHaveClass('mx-auto', 'max-w-7xl');
      expect(screen.queryByRole('button', { name: /cancel/i })).not.toBeInTheDocument();
    });
  });
});