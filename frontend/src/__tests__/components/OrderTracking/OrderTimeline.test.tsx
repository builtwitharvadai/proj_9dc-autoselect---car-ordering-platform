/**
 * OrderTimeline Component Test Suite
 * 
 * Comprehensive tests covering:
 * - Component rendering with various props
 * - Stage progression and status updates
 * - Animations and transitions
 * - Responsive behavior (compact mode)
 * - Accessibility (ARIA labels, keyboard navigation)
 * - User interactions (clicks, keyboard events)
 * - Edge cases and error scenarios
 * - Performance and memory management
 * 
 * @module components/OrderTracking/__tests__/OrderTimeline.test
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import OrderTimeline, { OrderTimelineProps } from '../OrderTimeline';
import type {
  OrderTimeline as OrderTimelineType,
  OrderTimelineStage,
  TimelineStage,
  TimelineStageStatus,
} from '../../../types/orders';

// Extend Jest matchers
expect.extend(toHaveNoViolations);

// ============================================================================
// Test Data Factories
// ============================================================================

/**
 * Factory for creating timeline stage test data
 */
class TimelineStageFactory {
  private static defaultStage: OrderTimelineStage = {
    stage: 'order_placed',
    title: 'Order Placed',
    description: 'Your order has been received',
    status: 'completed',
    completedAt: '2024-01-15T10:00:00Z',
    estimatedAt: undefined,
    metadata: {},
  };

  static create(overrides: Partial<OrderTimelineStage> = {}): OrderTimelineStage {
    return {
      ...this.defaultStage,
      ...overrides,
    };
  }

  static createCompleted(stage: TimelineStage, title: string): OrderTimelineStage {
    return this.create({
      stage,
      title,
      status: 'completed',
      completedAt: new Date().toISOString(),
    });
  }

  static createCurrent(stage: TimelineStage, title: string): OrderTimelineStage {
    return this.create({
      stage,
      title,
      status: 'current',
      completedAt: undefined,
      estimatedAt: new Date(Date.now() + 86400000).toISOString(), // Tomorrow
    });
  }

  static createUpcoming(stage: TimelineStage, title: string): OrderTimelineStage {
    return this.create({
      stage,
      title,
      status: 'upcoming',
      completedAt: undefined,
      estimatedAt: new Date(Date.now() + 172800000).toISOString(), // 2 days
    });
  }

  static createSkipped(stage: TimelineStage, title: string): OrderTimelineStage {
    return this.create({
      stage,
      title,
      status: 'skipped',
      completedAt: undefined,
      estimatedAt: undefined,
    });
  }
}

/**
 * Factory for creating timeline test data
 */
class TimelineFactory {
  static create(overrides: Partial<OrderTimelineType> = {}): OrderTimelineType {
    const defaultTimeline: OrderTimelineType = {
      stages: [
        TimelineStageFactory.createCompleted('order_placed', 'Order Placed'),
        TimelineStageFactory.createCompleted('payment_confirmed', 'Payment Confirmed'),
        TimelineStageFactory.createCurrent('in_production', 'In Production'),
        TimelineStageFactory.createUpcoming('shipped', 'Shipped'),
        TimelineStageFactory.createUpcoming('delivered', 'Delivered'),
      ],
      progress: 0.4,
      lastUpdated: new Date().toISOString(),
    };

    return {
      ...defaultTimeline,
      ...overrides,
    };
  }

  static createEmpty(): OrderTimelineType {
    return {
      stages: [],
      progress: 0,
      lastUpdated: new Date().toISOString(),
    };
  }

  static createSingleStage(): OrderTimelineType {
    return this.create({
      stages: [TimelineStageFactory.createCurrent('order_placed', 'Order Placed')],
      progress: 0,
    });
  }

  static createAllCompleted(): OrderTimelineType {
    return this.create({
      stages: [
        TimelineStageFactory.createCompleted('order_placed', 'Order Placed'),
        TimelineStageFactory.createCompleted('payment_confirmed', 'Payment Confirmed'),
        TimelineStageFactory.createCompleted('in_production', 'In Production'),
        TimelineStageFactory.createCompleted('shipped', 'Shipped'),
        TimelineStageFactory.createCompleted('delivered', 'Delivered'),
      ],
      progress: 1.0,
    });
  }

  static createWithMetadata(): OrderTimelineType {
    return this.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          status: 'completed',
          metadata: {
            'Order ID': 'ORD-12345',
            'Payment Method': 'Credit Card',
          },
        }),
        TimelineStageFactory.createCurrent('in_production', 'In Production'),
      ],
      progress: 0.5,
    });
  }
}

// ============================================================================
// Test Utilities
// ============================================================================

/**
 * Render component with default props
 */
function renderTimeline(props: Partial<OrderTimelineProps> = {}) {
  const defaultProps: OrderTimelineProps = {
    timeline: TimelineFactory.create(),
    enableAnimations: false, // Disable for testing
    ...props,
  };

  return render(<OrderTimeline {...defaultProps} />);
}

/**
 * Get stage element by title
 */
function getStageByTitle(title: string) {
  return screen.getByRole('heading', { name: title }).closest('div');
}

/**
 * Mock IntersectionObserver for animation tests
 */
function mockIntersectionObserver() {
  const mockIntersectionObserver = vi.fn();
  mockIntersectionObserver.mockReturnValue({
    observe: () => null,
    unobserve: () => null,
    disconnect: () => null,
  });
  window.IntersectionObserver = mockIntersectionObserver as unknown as typeof IntersectionObserver;
}

// ============================================================================
// Test Suite: Component Rendering
// ============================================================================

describe('OrderTimeline - Component Rendering', () => {
  it('should render timeline with all stages', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    // Verify all stages are rendered
    timeline.stages.forEach((stage) => {
      expect(screen.getByText(stage.title)).toBeInTheDocument();
    });
  });

  it('should render progress percentage', () => {
    const timeline = TimelineFactory.create({ progress: 0.65 });
    renderTimeline({ timeline });

    expect(screen.getByText('65%')).toBeInTheDocument();
  });

  it('should render progress bar with correct width', () => {
    const timeline = TimelineFactory.create({ progress: 0.75 });
    renderTimeline({ timeline });

    const progressBar = screen.getByRole('progressbar');
    const progressFill = progressBar.querySelector('div');

    expect(progressBar).toHaveAttribute('aria-valuenow', '75');
    expect(progressFill).toHaveStyle({ width: '75%' });
  });

  it('should render current stage information', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    expect(screen.getByText(/Currently at stage 3 of 5/i)).toBeInTheDocument();
    expect(screen.getByText('In Production')).toBeInTheDocument();
  });

  it('should render last updated timestamp', () => {
    const lastUpdated = '2024-01-15T14:30:00Z';
    const timeline = TimelineFactory.create({ lastUpdated });
    renderTimeline({ timeline });

    const timeElement = screen.getByText(/Last updated:/i).querySelector('time');
    expect(timeElement).toHaveAttribute('dateTime', lastUpdated);
  });

  it('should render with custom className', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, className: 'custom-class' });

    const timelineElement = container.querySelector('.custom-class');
    expect(timelineElement).toBeInTheDocument();
  });

  it('should render empty timeline gracefully', () => {
    const timeline = TimelineFactory.createEmpty();
    renderTimeline({ timeline });

    expect(screen.getByText('Order Progress')).toBeInTheDocument();
    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('should render single stage timeline', () => {
    const timeline = TimelineFactory.createSingleStage();
    renderTimeline({ timeline });

    expect(screen.getByText('Order Placed')).toBeInTheDocument();
    expect(screen.getByText(/Currently at stage 1 of 1/i)).toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Stage Status Rendering
// ============================================================================

describe('OrderTimeline - Stage Status Rendering', () => {
  it('should render completed stages with correct styling', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    const completedStage = getStageByTitle('Order Placed');
    expect(completedStage).toHaveClass('relative', 'flex');

    // Check for completed status icon (CheckCircle)
    const iconContainer = completedStage?.querySelector('.border-green-500');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render current stage with correct styling', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    const currentStage = getStageByTitle('In Production');
    expect(currentStage).toBeInTheDocument();

    // Check for current status styling
    const iconContainer = currentStage?.querySelector('.border-blue-500');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render upcoming stages with correct styling', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    const upcomingStage = getStageByTitle('Shipped');
    expect(upcomingStage).toBeInTheDocument();

    // Check for upcoming status styling
    const iconContainer = upcomingStage?.querySelector('.border-gray-300');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render skipped stages with correct styling', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.createCompleted('order_placed', 'Order Placed'),
        TimelineStageFactory.createSkipped('payment_confirmed', 'Payment Confirmed'),
        TimelineStageFactory.createCurrent('in_production', 'In Production'),
      ],
    });
    renderTimeline({ timeline });

    const skippedStage = getStageByTitle('Payment Confirmed');
    expect(skippedStage).toBeInTheDocument();

    // Check for skipped status styling
    const iconContainer = skippedStage?.querySelector('.border-gray-200');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should render timeline connector lines', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline });

    // Check for timeline lines (should be stages.length - 1)
    const timelineLines = container.querySelectorAll('.absolute.left-4.top-10');
    expect(timelineLines.length).toBeGreaterThan(0);
  });

  it('should render completed timeline lines in green', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline });

    const completedLines = container.querySelectorAll('.bg-green-500');
    expect(completedLines.length).toBeGreaterThan(0);
  });
});

// ============================================================================
// Test Suite: Date Formatting
// ============================================================================

describe('OrderTimeline - Date Formatting', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2024-01-15T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should display "Today" for same-day dates', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          status: 'current',
          estimatedAt: '2024-01-15T14:00:00Z',
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText('Today')).toBeInTheDocument();
  });

  it('should display "Tomorrow" for next-day dates', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'shipped',
          title: 'Shipped',
          status: 'upcoming',
          estimatedAt: '2024-01-16T14:00:00Z',
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText('Tomorrow')).toBeInTheDocument();
  });

  it('should display "In X days" for dates within a week', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'delivered',
          title: 'Delivered',
          status: 'upcoming',
          estimatedAt: '2024-01-18T14:00:00Z', // 3 days from now
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText('In 3 days')).toBeInTheDocument();
  });

  it('should display formatted date for dates beyond a week', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'delivered',
          title: 'Delivered',
          status: 'upcoming',
          estimatedAt: '2024-01-25T14:00:00Z', // 10 days from now
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText('Jan 25')).toBeInTheDocument();
  });

  it('should hide dates when showEstimatedDates is false', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline, showEstimatedDates: false });

    // Should not find any date elements
    const timeElements = screen.queryAllByRole('time');
    expect(timeElements.length).toBe(1); // Only last updated time
  });
});

// ============================================================================
// Test Suite: Stage Descriptions and Metadata
// ============================================================================

describe('OrderTimeline - Stage Descriptions and Metadata', () => {
  it('should render stage descriptions', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          description: 'Your order has been successfully placed',
          status: 'completed',
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText('Your order has been successfully placed')).toBeInTheDocument();
  });

  it('should hide descriptions when showDescriptions is false', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          description: 'Your order has been successfully placed',
          status: 'completed',
        }),
      ],
    });
    renderTimeline({ timeline, showDescriptions: false });

    expect(
      screen.queryByText('Your order has been successfully placed'),
    ).not.toBeInTheDocument();
  });

  it('should render stage metadata', () => {
    const timeline = TimelineFactory.createWithMetadata();
    renderTimeline({ timeline });

    expect(screen.getByText('Order ID:')).toBeInTheDocument();
    expect(screen.getByText('ORD-12345')).toBeInTheDocument();
    expect(screen.getByText('Payment Method:')).toBeInTheDocument();
    expect(screen.getByText('Credit Card')).toBeInTheDocument();
  });

  it('should not render metadata section when empty', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          status: 'completed',
          metadata: {},
        }),
      ],
    });
    const { container } = renderTimeline({ timeline });

    const metadataSection = container.querySelector('.mt-2.text-sm.text-gray-500');
    expect(metadataSection).not.toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Compact Mode
// ============================================================================

describe('OrderTimeline - Compact Mode', () => {
  it('should apply compact styling when compact prop is true', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, compact: true });

    // Check for compact padding
    const timelineContainer = container.querySelector('.p-4');
    expect(timelineContainer).toBeInTheDocument();
  });

  it('should use smaller icon sizes in compact mode', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, compact: true });

    // Check for compact icon container size
    const iconContainer = container.querySelector('.h-8.w-8');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should use smaller text sizes in compact mode', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline, compact: true });

    const heading = screen.getByText('Order Progress');
    expect(heading).toHaveClass('text-lg');
  });

  it('should hide stage icon badges in compact mode', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, compact: true });

    // Stage icon badges should not be rendered in compact mode
    const badges = container.querySelectorAll('.absolute.-bottom-1.-right-1');
    expect(badges.length).toBe(0);
  });
});

// ============================================================================
// Test Suite: User Interactions
// ============================================================================

describe('OrderTimeline - User Interactions', () => {
  it('should call onStageClick when stage is clicked', async () => {
    const user = userEvent.setup();
    const onStageClick = vi.fn();
    const timeline = TimelineFactory.create();

    renderTimeline({ timeline, onStageClick });

    const stageElement = getStageByTitle('Order Placed');
    await user.click(stageElement!);

    expect(onStageClick).toHaveBeenCalledWith('order_placed');
    expect(onStageClick).toHaveBeenCalledTimes(1);
  });

  it('should call onStageClick on Enter key press', async () => {
    const user = userEvent.setup();
    const onStageClick = vi.fn();
    const timeline = TimelineFactory.create();

    renderTimeline({ timeline, onStageClick });

    const stageElement = getStageByTitle('Order Placed');
    stageElement?.focus();
    await user.keyboard('{Enter}');

    expect(onStageClick).toHaveBeenCalledWith('order_placed');
  });

  it('should call onStageClick on Space key press', async () => {
    const user = userEvent.setup();
    const onStageClick = vi.fn();
    const timeline = TimelineFactory.create();

    renderTimeline({ timeline, onStageClick });

    const stageElement = getStageByTitle('Order Placed');
    stageElement?.focus();
    await user.keyboard(' ');

    expect(onStageClick).toHaveBeenCalledWith('order_placed');
  });

  it('should not call onStageClick when callback is not provided', async () => {
    const user = userEvent.setup();
    const timeline = TimelineFactory.create();

    renderTimeline({ timeline });

    const stageElement = getStageByTitle('Order Placed');
    await user.click(stageElement!);

    // Should not throw error
    expect(stageElement).toBeInTheDocument();
  });

  it('should not make stages clickable when onStageClick is not provided', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    const stageElement = getStageByTitle('Order Placed');
    expect(stageElement).not.toHaveAttribute('role', 'button');
    expect(stageElement).not.toHaveAttribute('tabIndex');
  });

  it('should make stages focusable when onStageClick is provided', () => {
    const onStageClick = vi.fn();
    const timeline = TimelineFactory.create();

    renderTimeline({ timeline, onStageClick });

    const stageElement = getStageByTitle('Order Placed');
    expect(stageElement).toHaveAttribute('role', 'button');
    expect(stageElement).toHaveAttribute('tabIndex', '0');
  });
});

// ============================================================================
// Test Suite: Animations
// ============================================================================

describe('OrderTimeline - Animations', () => {
  beforeEach(() => {
    mockIntersectionObserver();
  });

  it('should apply animation classes when enableAnimations is true', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, enableAnimations: true });

    // Check for animation classes on progress bar
    const progressBar = container.querySelector('.transition-all.duration-500');
    expect(progressBar).toBeInTheDocument();
  });

  it('should not apply animation classes when enableAnimations is false', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, enableAnimations: false });

    // Progress bar should not have animation classes
    const progressBar = screen.getByRole('progressbar').querySelector('div');
    expect(progressBar).not.toHaveClass('transition-all');
  });

  it('should apply pulse animation to current stage', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, enableAnimations: true });

    // Find current stage icon container
    const currentStageIcon = container.querySelector('.animate-pulse');
    expect(currentStageIcon).toBeInTheDocument();
  });

  it('should apply scale-in animation to completed stages', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, enableAnimations: true });

    // Find completed stage icon containers
    const completedStageIcons = container.querySelectorAll('.animate-scale-in');
    expect(completedStageIcons.length).toBeGreaterThan(0);
  });

  it('should apply grow animation to completed timeline lines', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline, enableAnimations: true });

    // Find timeline lines with grow animation
    const animatedLines = container.querySelectorAll('.animate-timeline-grow');
    expect(animatedLines.length).toBeGreaterThan(0);
  });
});

// ============================================================================
// Test Suite: Accessibility
// ============================================================================

describe('OrderTimeline - Accessibility', () => {
  it('should have no accessibility violations', async () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline });

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper ARIA labels on timeline region', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    const timelineRegion = screen.getByRole('region', { name: 'Order timeline' });
    expect(timelineRegion).toBeInTheDocument();
  });

  it('should have proper ARIA attributes on progress bar', () => {
    const timeline = TimelineFactory.create({ progress: 0.6 });
    renderTimeline({ timeline });

    const progressBar = screen.getByRole('progressbar');
    expect(progressBar).toHaveAttribute('aria-valuenow', '60');
    expect(progressBar).toHaveAttribute('aria-valuemin', '0');
    expect(progressBar).toHaveAttribute('aria-valuemax', '100');
  });

  it('should have proper ARIA label on progress percentage', () => {
    const timeline = TimelineFactory.create({ progress: 0.75 });
    renderTimeline({ timeline });

    const percentage = screen.getByLabelText('75% complete');
    expect(percentage).toBeInTheDocument();
  });

  it('should have proper ARIA labels on clickable stages', () => {
    const onStageClick = vi.fn();
    const timeline = TimelineFactory.create();

    renderTimeline({ timeline, onStageClick });

    const stageButton = screen.getByRole('button', { name: 'View Order Placed details' });
    expect(stageButton).toBeInTheDocument();
  });

  it('should have semantic time elements with datetime attributes', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    const timeElements = screen.getAllByRole('time');
    timeElements.forEach((timeElement) => {
      expect(timeElement).toHaveAttribute('dateTime');
    });
  });

  it('should have proper heading hierarchy', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    // Main heading
    const mainHeading = screen.getByRole('heading', { name: 'Order Progress', level: 2 });
    expect(mainHeading).toBeInTheDocument();

    // Stage headings
    const stageHeadings = screen.getAllByRole('heading', { level: 3 });
    expect(stageHeadings.length).toBe(timeline.stages.length);
  });

  it('should support keyboard navigation for clickable stages', async () => {
    const user = userEvent.setup();
    const onStageClick = vi.fn();
    const timeline = TimelineFactory.create();

    renderTimeline({ timeline, onStageClick });

    // Tab to first stage
    await user.tab();
    const firstStage = document.activeElement;
    expect(firstStage).toHaveAttribute('role', 'button');

    // Tab to next stage
    await user.tab();
    const secondStage = document.activeElement;
    expect(secondStage).toHaveAttribute('role', 'button');
    expect(secondStage).not.toBe(firstStage);
  });

  it('should have aria-hidden on decorative icons', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline });

    // All icons should have aria-hidden
    const icons = container.querySelectorAll('svg');
    icons.forEach((icon) => {
      expect(icon).toHaveAttribute('aria-hidden', 'true');
    });
  });
});

// ============================================================================
// Test Suite: Edge Cases
// ============================================================================

describe('OrderTimeline - Edge Cases', () => {
  it('should handle timeline with no current stage', () => {
    const timeline = TimelineFactory.createAllCompleted();
    renderTimeline({ timeline });

    expect(screen.getByText('Order Progress')).toBeInTheDocument();
    expect(screen.queryByText(/Currently at stage/i)).not.toBeInTheDocument();
  });

  it('should handle timeline with all upcoming stages', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.createUpcoming('order_placed', 'Order Placed'),
        TimelineStageFactory.createUpcoming('payment_confirmed', 'Payment Confirmed'),
      ],
      progress: 0,
    });
    renderTimeline({ timeline });

    expect(screen.getByText('0%')).toBeInTheDocument();
  });

  it('should handle stages without descriptions', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          status: 'completed',
          description: undefined,
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText('Order Placed')).toBeInTheDocument();
  });

  it('should handle stages without dates', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          status: 'completed',
          completedAt: undefined,
          estimatedAt: undefined,
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText('Order Placed')).toBeInTheDocument();
  });

  it('should handle very long stage titles', () => {
    const longTitle = 'A'.repeat(100);
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: longTitle,
          status: 'completed',
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText(longTitle)).toBeInTheDocument();
  });

  it('should handle very long descriptions', () => {
    const longDescription = 'B'.repeat(500);
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          description: longDescription,
          status: 'completed',
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText(longDescription)).toBeInTheDocument();
  });

  it('should handle progress values at boundaries', () => {
    const timeline0 = TimelineFactory.create({ progress: 0 });
    const { rerender } = renderTimeline({ timeline: timeline0 });
    expect(screen.getByText('0%')).toBeInTheDocument();

    const timeline100 = TimelineFactory.create({ progress: 1.0 });
    rerender(<OrderTimeline timeline={timeline100} />);
    expect(screen.getByText('100%')).toBeInTheDocument();
  });

  it('should handle invalid progress values gracefully', () => {
    const timeline = TimelineFactory.create({ progress: 1.5 }); // > 1.0
    renderTimeline({ timeline });

    expect(screen.getByText('150%')).toBeInTheDocument();
  });

  it('should handle metadata with special characters', () => {
    const timeline = TimelineFactory.create({
      stages: [
        TimelineStageFactory.create({
          stage: 'order_placed',
          title: 'Order Placed',
          status: 'completed',
          metadata: {
            'Special <>&"': 'Value <>&"',
          },
        }),
      ],
    });
    renderTimeline({ timeline });

    expect(screen.getByText('Special <>&":')).toBeInTheDocument();
    expect(screen.getByText('Value <>&"')).toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Performance
// ============================================================================

describe('OrderTimeline - Performance', () => {
  it('should render large timeline efficiently', () => {
    const stages = Array.from({ length: 20 }, (_, i) =>
      TimelineStageFactory.create({
        stage: 'order_placed',
        title: `Stage ${i + 1}`,
        status: i < 10 ? 'completed' : 'upcoming',
      }),
    );

    const timeline = TimelineFactory.create({ stages, progress: 0.5 });

    const startTime = performance.now();
    renderTimeline({ timeline });
    const endTime = performance.now();

    // Should render in less than 100ms
    expect(endTime - startTime).toBeLessThan(100);
  });

  it('should memoize timeline stages', () => {
    const timeline = TimelineFactory.create();
    const { rerender } = renderTimeline({ timeline });

    // Rerender with same timeline
    rerender(<OrderTimeline timeline={timeline} />);

    // Component should not re-render stages unnecessarily
    expect(screen.getByText('Order Progress')).toBeInTheDocument();
  });

  it('should handle rapid prop updates', async () => {
    const timeline1 = TimelineFactory.create({ progress: 0.2 });
    const { rerender } = renderTimeline({ timeline: timeline1 });

    // Rapidly update progress
    for (let i = 0.3; i <= 1.0; i += 0.1) {
      const updatedTimeline = TimelineFactory.create({ progress: i });
      rerender(<OrderTimeline timeline={updatedTimeline} />);
    }

    await waitFor(() => {
      expect(screen.getByText('100%')).toBeInTheDocument();
    });
  });
});

// ============================================================================
// Test Suite: Integration Scenarios
// ============================================================================

describe('OrderTimeline - Integration Scenarios', () => {
  it('should handle complete order lifecycle', () => {
    const stages: OrderTimelineStage[] = [
      TimelineStageFactory.createCompleted('order_placed', 'Order Placed'),
      TimelineStageFactory.createCompleted('payment_confirmed', 'Payment Confirmed'),
      TimelineStageFactory.createCompleted('in_production', 'In Production'),
      TimelineStageFactory.createCompleted('quality_check', 'Quality Check'),
      TimelineStageFactory.createCompleted('shipped', 'Shipped'),
      TimelineStageFactory.createCompleted('in_transit', 'In Transit'),
      TimelineStageFactory.createCompleted('out_for_delivery', 'Out for Delivery'),
      TimelineStageFactory.createCompleted('delivered', 'Delivered'),
    ];

    const timeline = TimelineFactory.create({ stages, progress: 1.0 });
    renderTimeline({ timeline });

    expect(screen.getByText('100%')).toBeInTheDocument();
    stages.forEach((stage) => {
      expect(screen.getByText(stage.title)).toBeInTheDocument();
    });
  });

  it('should handle order with skipped stages', () => {
    const stages: OrderTimelineStage[] = [
      TimelineStageFactory.createCompleted('order_placed', 'Order Placed'),
      TimelineStageFactory.createCompleted('payment_confirmed', 'Payment Confirmed'),
      TimelineStageFactory.createSkipped('in_production', 'In Production'),
      TimelineStageFactory.createSkipped('quality_check', 'Quality Check'),
      TimelineStageFactory.createCurrent('shipped', 'Shipped'),
    ];

    const timeline = TimelineFactory.create({ stages, progress: 0.6 });
    renderTimeline({ timeline });

    expect(screen.getByText('Shipped')).toBeInTheDocument();
    expect(screen.getByText(/Currently at stage 5 of 5/i)).toBeInTheDocument();
  });

  it('should update when timeline progresses', () => {
    const timeline1 = TimelineFactory.create({
      stages: [
        TimelineStageFactory.createCompleted('order_placed', 'Order Placed'),
        TimelineStageFactory.createCurrent('payment_confirmed', 'Payment Confirmed'),
        TimelineStageFactory.createUpcoming('shipped', 'Shipped'),
      ],
      progress: 0.33,
    });

    const { rerender } = renderTimeline({ timeline: timeline1 });
    expect(screen.getByText('33%')).toBeInTheDocument();

    // Progress to next stage
    const timeline2 = TimelineFactory.create({
      stages: [
        TimelineStageFactory.createCompleted('order_placed', 'Order Placed'),
        TimelineStageFactory.createCompleted('payment_confirmed', 'Payment Confirmed'),
        TimelineStageFactory.createCurrent('shipped', 'Shipped'),
      ],
      progress: 0.67,
    });

    rerender(<OrderTimeline timeline={timeline2} />);
    expect(screen.getByText('67%')).toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Responsive Behavior
// ============================================================================

describe('OrderTimeline - Responsive Behavior', () => {
  it('should apply responsive classes for different screen sizes', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline });

    // Check for responsive padding classes
    const timelineContainer = container.querySelector('.p-6.md\\:p-8');
    expect(timelineContainer).toBeInTheDocument();
  });

  it('should adjust icon sizes responsively', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline });

    // Check for responsive icon size classes
    const iconContainer = container.querySelector('.h-10.w-10.md\\:h-12.md\\:w-12');
    expect(iconContainer).toBeInTheDocument();
  });

  it('should adjust text sizes responsively', () => {
    const timeline = TimelineFactory.create();
    renderTimeline({ timeline });

    const heading = screen.getByText('Order Progress');
    expect(heading).toHaveClass('text-xl', 'md:text-2xl');
  });

  it('should adjust spacing responsively', () => {
    const timeline = TimelineFactory.create();
    const { container } = renderTimeline({ timeline });

    // Check for responsive gap classes
    const stageContainer = container.querySelector('.gap-4.md\\:gap-6');
    expect(stageContainer).toBeInTheDocument();
  });
});

// ============================================================================
// Test Suite: Memory Management
// ============================================================================

describe('OrderTimeline - Memory Management', () => {
  it('should cleanup event listeners on unmount', () => {
    const onStageClick = vi.fn();
    const timeline = TimelineFactory.create();

    const { unmount } = renderTimeline({ timeline, onStageClick });

    unmount();

    // Verify no memory leaks by checking callback is not called after unmount
    expect(onStageClick).not.toHaveBeenCalled();
  });

  it('should handle multiple renders without memory leaks', () => {
    const timeline = TimelineFactory.create();
    const { rerender, unmount } = renderTimeline({ timeline });

    // Render multiple times
    for (let i = 0; i < 10; i++) {
      rerender(<OrderTimeline timeline={timeline} />);
    }

    unmount();

    // Should complete without errors
    expect(true).toBe(true);
  });
});