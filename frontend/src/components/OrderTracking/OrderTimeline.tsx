/**
 * Order Timeline Component
 * 
 * Visual timeline component showing order progress with animations.
 * Displays completed/current/upcoming stages with status descriptions,
 * timestamps, and smooth animations. Includes mobile-responsive design.
 * 
 * @module components/OrderTracking/OrderTimeline
 */

import { memo, useMemo } from 'react';
import {
  CheckCircle,
  Circle,
  Clock,
  Package,
  Truck,
  Home,
  AlertCircle,
} from 'lucide-react';
import type {
  OrderTimeline as OrderTimelineType,
  OrderTimelineStage,
  TimelineStageStatus,
  TimelineStage,
} from '../../types/orders';

/**
 * Props for OrderTimeline component
 */
export interface OrderTimelineProps {
  /** Timeline data with stages and progress */
  readonly timeline: OrderTimelineType;
  /** Optional CSS class name */
  readonly className?: string;
  /** Enable animations (default: true) */
  readonly enableAnimations?: boolean;
  /** Compact mode for mobile (default: false) */
  readonly compact?: boolean;
  /** Show estimated dates (default: true) */
  readonly showEstimatedDates?: boolean;
  /** Show stage descriptions (default: true) */
  readonly showDescriptions?: boolean;
  /** Callback when stage is clicked */
  readonly onStageClick?: (stage: TimelineStage) => void;
}

/**
 * Stage icon mapping
 */
const STAGE_ICONS: Record<TimelineStage, typeof Package> = {
  order_placed: Package,
  payment_confirmed: CheckCircle,
  in_production: Package,
  quality_check: CheckCircle,
  shipped: Truck,
  in_transit: Truck,
  out_for_delivery: Truck,
  delivered: Home,
} as const;

/**
 * Stage color mapping based on status
 */
const STATUS_COLORS: Record<TimelineStageStatus, {
  readonly bg: string;
  readonly border: string;
  readonly text: string;
  readonly icon: string;
}> = {
  completed: {
    bg: 'bg-green-50',
    border: 'border-green-500',
    text: 'text-green-900',
    icon: 'text-green-600',
  },
  current: {
    bg: 'bg-blue-50',
    border: 'border-blue-500',
    text: 'text-blue-900',
    icon: 'text-blue-600',
  },
  upcoming: {
    bg: 'bg-gray-50',
    border: 'border-gray-300',
    text: 'text-gray-600',
    icon: 'text-gray-400',
  },
  skipped: {
    bg: 'bg-gray-50',
    border: 'border-gray-200',
    text: 'text-gray-400',
    icon: 'text-gray-300',
  },
} as const;

/**
 * Format date for display
 */
function formatStageDate(date: string | undefined): string {
  if (!date) return '';
  
  const dateObj = new Date(date);
  const now = new Date();
  const diffMs = dateObj.getTime() - now.getTime();
  const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) {
    return 'Today';
  } else if (diffDays === 1) {
    return 'Tomorrow';
  } else if (diffDays > 1 && diffDays <= 7) {
    return `In ${diffDays} days`;
  }
  
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: dateObj.getFullYear() !== now.getFullYear() ? 'numeric' : undefined,
  }).format(dateObj);
}

/**
 * Get status icon component
 */
function getStatusIcon(status: TimelineStageStatus): typeof Circle {
  switch (status) {
    case 'completed':
      return CheckCircle;
    case 'current':
      return Clock;
    case 'upcoming':
      return Circle;
    case 'skipped':
      return AlertCircle;
  }
}

/**
 * Timeline stage component
 */
interface TimelineStageItemProps {
  readonly stage: OrderTimelineStage;
  readonly isFirst: boolean;
  readonly isLast: boolean;
  readonly compact: boolean;
  readonly showEstimatedDates: boolean;
  readonly showDescriptions: boolean;
  readonly enableAnimations: boolean;
  readonly onClick?: (stage: TimelineStage) => void;
}

const TimelineStageItem = memo<TimelineStageItemProps>(({
  stage,
  isFirst,
  isLast,
  compact,
  showEstimatedDates,
  showDescriptions,
  enableAnimations,
  onClick,
}) => {
  const colors = STATUS_COLORS[stage.status];
  const StageIcon = STAGE_ICONS[stage.stage];
  const StatusIcon = getStatusIcon(stage.status);
  
  const isClickable = onClick !== undefined;
  const isCompleted = stage.status === 'completed';
  const isCurrent = stage.status === 'current';
  
  const handleClick = (): void => {
    if (isClickable) {
      onClick(stage.stage);
    }
  };
  
  const handleKeyDown = (event: React.KeyboardEvent): void => {
    if (isClickable && (event.key === 'Enter' || event.key === ' ')) {
      event.preventDefault();
      onClick(stage.stage);
    }
  };
  
  return (
    <div
      className={`
        relative flex
        ${compact ? 'gap-3' : 'gap-4 md:gap-6'}
        ${isClickable ? 'cursor-pointer' : ''}
      `}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      role={isClickable ? 'button' : undefined}
      tabIndex={isClickable ? 0 : undefined}
      aria-label={isClickable ? `View ${stage.title} details` : undefined}
    >
      {/* Timeline line */}
      {!isLast && (
        <div
          className={`
            absolute left-4 top-10 w-0.5 h-full
            ${isCompleted ? 'bg-green-500' : 'bg-gray-300'}
            ${enableAnimations && isCompleted ? 'animate-timeline-grow' : ''}
            ${compact ? 'left-3' : 'md:left-5'}
          `}
          aria-hidden="true"
        />
      )}
      
      {/* Icon container */}
      <div className="relative flex-shrink-0">
        <div
          className={`
            flex items-center justify-center rounded-full border-2
            ${colors.bg} ${colors.border}
            ${compact ? 'h-8 w-8' : 'h-10 w-10 md:h-12 md:w-12'}
            ${enableAnimations && isCurrent ? 'animate-pulse' : ''}
            ${enableAnimations && isCompleted ? 'animate-scale-in' : ''}
            transition-all duration-300
          `}
        >
          <StatusIcon
            className={`
              ${colors.icon}
              ${compact ? 'h-4 w-4' : 'h-5 w-5 md:h-6 md:w-6'}
            `}
            aria-hidden="true"
          />
        </div>
        
        {/* Stage icon badge */}
        {!compact && (
          <div
            className={`
              absolute -bottom-1 -right-1 flex items-center justify-center
              rounded-full bg-white border-2 ${colors.border}
              h-5 w-5 md:h-6 md:w-6
            `}
          >
            <StageIcon
              className={`${colors.icon} h-3 w-3 md:h-4 md:w-4`}
              aria-hidden="true"
            />
          </div>
        )}
      </div>
      
      {/* Content */}
      <div className={`flex-1 ${isLast ? 'pb-0' : compact ? 'pb-6' : 'pb-8 md:pb-10'}`}>
        {/* Title and date */}
        <div className="flex items-start justify-between gap-2 mb-1">
          <h3
            className={`
              font-semibold ${colors.text}
              ${compact ? 'text-sm' : 'text-base md:text-lg'}
            `}
          >
            {stage.title}
          </h3>
          
          {showEstimatedDates && (stage.completedAt ?? stage.estimatedAt) && (
            <time
              className={`
                text-xs ${colors.text} opacity-75 whitespace-nowrap
                ${compact ? 'text-xs' : 'md:text-sm'}
              `}
              dateTime={stage.completedAt ?? stage.estimatedAt}
            >
              {formatStageDate(stage.completedAt ?? stage.estimatedAt)}
            </time>
          )}
        </div>
        
        {/* Description */}
        {showDescriptions && stage.description && (
          <p
            className={`
              text-gray-600
              ${compact ? 'text-xs' : 'text-sm md:text-base'}
            `}
          >
            {stage.description}
          </p>
        )}
        
        {/* Metadata */}
        {stage.metadata && Object.keys(stage.metadata).length > 0 && (
          <div className={`mt-2 ${compact ? 'text-xs' : 'text-sm'} text-gray-500`}>
            {Object.entries(stage.metadata).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <span className="font-medium">{key}:</span>
                <span>{String(value)}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
});

TimelineStageItem.displayName = 'TimelineStageItem';

/**
 * Order Timeline Component
 * 
 * Displays visual timeline of order progress with animations.
 * Shows completed, current, and upcoming stages with status indicators.
 */
export const OrderTimeline = memo<OrderTimelineProps>(({
  timeline,
  className = '',
  enableAnimations = true,
  compact = false,
  showEstimatedDates = true,
  showDescriptions = true,
  onStageClick,
}) => {
  // Calculate progress percentage
  const progressPercentage = useMemo(() => {
    return Math.round(timeline.progress * 100);
  }, [timeline.progress]);
  
  // Get current stage info
  const currentStageInfo = useMemo(() => {
    const currentStage = timeline.stages.find(s => s.status === 'current');
    if (!currentStage) return null;
    
    const currentIndex = timeline.stages.indexOf(currentStage);
    const totalStages = timeline.stages.length;
    
    return {
      stage: currentStage,
      index: currentIndex,
      total: totalStages,
    };
  }, [timeline.stages]);
  
  return (
    <div
      className={`
        bg-white rounded-lg shadow-sm border border-gray-200
        ${compact ? 'p-4' : 'p-6 md:p-8'}
        ${className}
      `}
      role="region"
      aria-label="Order timeline"
    >
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2
            className={`
              font-bold text-gray-900
              ${compact ? 'text-lg' : 'text-xl md:text-2xl'}
            `}
          >
            Order Progress
          </h2>
          
          <span
            className={`
              font-semibold text-blue-600
              ${compact ? 'text-sm' : 'text-base md:text-lg'}
            `}
            aria-label={`${progressPercentage}% complete`}
          >
            {progressPercentage}%
          </span>
        </div>
        
        {/* Progress bar */}
        <div
          className="w-full bg-gray-200 rounded-full h-2 overflow-hidden"
          role="progressbar"
          aria-valuenow={progressPercentage}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className={`
              h-full bg-gradient-to-r from-blue-500 to-blue-600 rounded-full
              ${enableAnimations ? 'transition-all duration-500 ease-out' : ''}
            `}
            style={{ width: `${progressPercentage}%` }}
          />
        </div>
        
        {/* Current stage info */}
        {currentStageInfo && (
          <p className="mt-2 text-sm text-gray-600">
            Currently at stage {currentStageInfo.index + 1} of {currentStageInfo.total}:{' '}
            <span className="font-medium text-gray-900">
              {currentStageInfo.stage.title}
            </span>
          </p>
        )}
      </div>
      
      {/* Timeline stages */}
      <div className="space-y-0">
        {timeline.stages.map((stage, index) => (
          <TimelineStageItem
            key={stage.stage}
            stage={stage}
            isFirst={index === 0}
            isLast={index === timeline.stages.length - 1}
            compact={compact}
            showEstimatedDates={showEstimatedDates}
            showDescriptions={showDescriptions}
            enableAnimations={enableAnimations}
            onClick={onStageClick}
          />
        ))}
      </div>
      
      {/* Last updated */}
      <div className="mt-6 pt-4 border-t border-gray-200">
        <p className="text-xs text-gray-500 text-center">
          Last updated:{' '}
          <time dateTime={timeline.lastUpdated}>
            {new Intl.DateTimeFormat('en-US', {
              month: 'short',
              day: 'numeric',
              hour: 'numeric',
              minute: 'numeric',
            }).format(new Date(timeline.lastUpdated))}
          </time>
        </p>
      </div>
    </div>
  );
});

OrderTimeline.displayName = 'OrderTimeline';

export default OrderTimeline;