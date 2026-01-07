/**
 * Core TypeScript type definitions for AutoSelect frontend application
 * Provides type-safe interfaces for navigation, responsive design, and component props
 */

/**
 * Responsive breakpoint definitions matching Tailwind CSS configuration
 */
export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';

export interface BreakpointConfig {
  readonly xs: number;
  readonly sm: number;
  readonly md: number;
  readonly lg: number;
  readonly xl: number;
  readonly '2xl': number;
}

export const BREAKPOINTS: BreakpointConfig = {
  xs: 320,
  sm: 640,
  md: 768,
  lg: 1024,
  xl: 1280,
  '2xl': 1536,
} as const;

/**
 * Navigation route configuration
 */
export interface RouteConfig {
  readonly path: string;
  readonly label: string;
  readonly icon?: string;
  readonly requiresAuth?: boolean;
}

export type NavigationRoutes = readonly RouteConfig[];

/**
 * Common component prop types
 */
export interface BaseComponentProps {
  readonly className?: string;
  readonly testId?: string;
}

export interface ChildrenProps {
  readonly children: React.ReactNode;
}

export interface LoadingProps {
  readonly isLoading?: boolean;
  readonly loadingText?: string;
}

export interface ErrorProps {
  readonly error?: Error | string | null;
  readonly onErrorDismiss?: () => void;
}

/**
 * Layout component props
 */
export interface LayoutProps extends BaseComponentProps, ChildrenProps {
  readonly showHeader?: boolean;
  readonly showFooter?: boolean;
}

export interface HeaderProps extends BaseComponentProps {
  readonly title?: string;
  readonly showNavigation?: boolean;
}

/**
 * Responsive utility types
 */
export type ResponsiveValue<T> = T | Partial<Record<Breakpoint, T>>;

export interface ViewportSize {
  readonly width: number;
  readonly height: number;
}

export interface MediaQueryResult {
  readonly matches: boolean;
  readonly breakpoint: Breakpoint;
}

/**
 * Form and input types
 */
export interface FormFieldProps extends BaseComponentProps {
  readonly id: string;
  readonly name: string;
  readonly label: string;
  readonly required?: boolean;
  readonly disabled?: boolean;
  readonly error?: string;
  readonly helperText?: string;
}

export interface InputProps extends FormFieldProps {
  readonly type?: 'text' | 'email' | 'password' | 'number' | 'tel' | 'url';
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly placeholder?: string;
  readonly autoComplete?: string;
}

export interface SelectOption {
  readonly value: string;
  readonly label: string;
  readonly disabled?: boolean;
}

export interface SelectProps extends FormFieldProps {
  readonly value: string;
  readonly onChange: (value: string) => void;
  readonly options: readonly SelectOption[];
  readonly placeholder?: string;
}

/**
 * Button component types
 */
export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

export interface ButtonProps extends BaseComponentProps {
  readonly variant?: ButtonVariant;
  readonly size?: ButtonSize;
  readonly disabled?: boolean;
  readonly loading?: boolean;
  readonly type?: 'button' | 'submit' | 'reset';
  readonly onClick?: (event: React.MouseEvent<HTMLButtonElement>) => void;
  readonly children: React.ReactNode;
  readonly fullWidth?: boolean;
  readonly icon?: React.ReactNode;
  readonly iconPosition?: 'left' | 'right';
}

/**
 * API and data fetching types
 */
export type RequestStatus = 'idle' | 'loading' | 'success' | 'error';

export interface ApiState<T> {
  readonly status: RequestStatus;
  readonly data: T | null;
  readonly error: Error | null;
}

export interface PaginationParams {
  readonly page: number;
  readonly pageSize: number;
}

export interface PaginatedResponse<T> {
  readonly data: readonly T[];
  readonly total: number;
  readonly page: number;
  readonly pageSize: number;
  readonly totalPages: number;
}

/**
 * Vehicle and product types
 */
export interface Vehicle {
  readonly id: string;
  readonly name: string;
  readonly manufacturer: string;
  readonly model: string;
  readonly year: number;
  readonly price: number;
  readonly image: string;
  readonly description: string;
  readonly features: readonly string[];
  readonly specifications: Record<string, string>;
}

export interface VehicleConfiguration {
  readonly vehicleId: string;
  readonly color: string;
  readonly interior: string;
  readonly packages: readonly string[];
  readonly accessories: readonly string[];
}

/**
 * Cart and order types
 */
export interface CartItem {
  readonly id: string;
  readonly vehicle: Vehicle;
  readonly configuration: VehicleConfiguration;
  readonly quantity: number;
  readonly price: number;
}

export interface Cart {
  readonly items: readonly CartItem[];
  readonly subtotal: number;
  readonly tax: number;
  readonly total: number;
}

export type OrderStatus = 'processing' | 'in-transit' | 'delivered' | 'cancelled';

export interface Order {
  readonly id: string;
  readonly orderDate: Date;
  readonly status: OrderStatus;
  readonly items: readonly CartItem[];
  readonly total: number;
  readonly trackingNumber: string;
}

/**
 * User and authentication types
 */
export interface User {
  readonly id: string;
  readonly email: string;
  readonly firstName: string;
  readonly lastName: string;
  readonly phone?: string;
  readonly avatar?: string;
}

export interface AuthState {
  readonly isAuthenticated: boolean;
  readonly user: User | null;
  readonly token: string | null;
}

/**
 * Notification and toast types
 */
export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  readonly id: string;
  readonly type: NotificationType;
  readonly message: string;
  readonly duration?: number;
  readonly dismissible?: boolean;
}

/**
 * Modal and dialog types
 */
export interface ModalProps extends BaseComponentProps, ChildrenProps {
  readonly isOpen: boolean;
  readonly onClose: () => void;
  readonly title?: string;
  readonly size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  readonly closeOnOverlayClick?: boolean;
  readonly closeOnEscape?: boolean;
  readonly showCloseButton?: boolean;
}

/**
 * Accessibility types
 */
export interface AriaProps {
  readonly 'aria-label'?: string;
  readonly 'aria-labelledby'?: string;
  readonly 'aria-describedby'?: string;
  readonly 'aria-expanded'?: boolean;
  readonly 'aria-hidden'?: boolean;
  readonly 'aria-live'?: 'polite' | 'assertive' | 'off';
  readonly 'aria-invalid'?: boolean;
  readonly role?: string;
}

/**
 * Theme and styling types
 */
export type ColorScheme = 'light' | 'dark' | 'auto';

export interface ThemeConfig {
  readonly colorScheme: ColorScheme;
  readonly primaryColor: string;
  readonly fontFamily: string;
}

/**
 * Utility types for type-safe operations
 */
export type DeepReadonly<T> = T extends (infer R)[]
  ? DeepReadonlyArray<R>
  : T extends object
    ? DeepReadonlyObject<T>
    : T;

interface DeepReadonlyArray<T> extends ReadonlyArray<DeepReadonly<T>> {}

type DeepReadonlyObject<T> = {
  readonly [P in keyof T]: DeepReadonly<T[P]>;
};

export type Nullable<T> = T | null;
export type Optional<T> = T | undefined;
export type Maybe<T> = T | null | undefined;

/**
 * Event handler types
 */
export type EventHandler<E = Event> = (event: E) => void;
export type AsyncEventHandler<E = Event> = (event: E) => Promise<void>;

/**
 * Validation types
 */
export interface ValidationRule<T = unknown> {
  readonly validate: (value: T) => boolean;
  readonly message: string;
}

export interface ValidationResult {
  readonly isValid: boolean;
  readonly errors: readonly string[];
}

/**
 * Filter and sort types
 */
export type SortDirection = 'asc' | 'desc';

export interface SortConfig<T> {
  readonly field: keyof T;
  readonly direction: SortDirection;
}

export interface FilterConfig<T> {
  readonly field: keyof T;
  readonly operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'in';
  readonly value: unknown;
}