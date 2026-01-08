import { useEffect, useRef, useCallback, useState } from 'react';
import { io, Socket } from 'socket.io-client';
import type {
  OrderWebSocketMessage,
  OrderStatusChangedMessage,
  DeliveryEstimateUpdatedMessage,
  TimelineUpdatedMessage,
} from '../types/orders';

/**
 * WebSocket connection states
 */
export type ConnectionState = 'disconnected' | 'connecting' | 'connected' | 'reconnecting' | 'error';

/**
 * WebSocket configuration options
 */
export interface WebSocketConfig {
  readonly url?: string;
  readonly autoConnect?: boolean;
  readonly reconnection?: boolean;
  readonly reconnectionAttempts?: number;
  readonly reconnectionDelay?: number;
  readonly reconnectionDelayMax?: number;
  readonly timeout?: number;
  readonly transports?: readonly ('websocket' | 'polling')[];
}

/**
 * WebSocket hook options
 */
export interface UseWebSocketOptions extends WebSocketConfig {
  readonly orderId?: string;
  readonly onMessage?: (message: OrderWebSocketMessage) => void;
  readonly onStatusChange?: (message: OrderStatusChangedMessage) => void;
  readonly onDeliveryUpdate?: (message: DeliveryEstimateUpdatedMessage) => void;
  readonly onTimelineUpdate?: (message: TimelineUpdatedMessage) => void;
  readonly onConnect?: () => void;
  readonly onDisconnect?: (reason: string) => void;
  readonly onError?: (error: Error) => void;
  readonly enabled?: boolean;
}

/**
 * WebSocket hook return value
 */
export interface UseWebSocketReturn {
  readonly connectionState: ConnectionState;
  readonly isConnected: boolean;
  readonly isConnecting: boolean;
  readonly error: Error | null;
  readonly lastMessage: OrderWebSocketMessage | null;
  readonly connect: () => void;
  readonly disconnect: () => void;
  readonly reconnect: () => void;
  readonly subscribe: (orderId: string) => void;
  readonly unsubscribe: (orderId: string) => void;
}

/**
 * Default WebSocket configuration
 */
const DEFAULT_CONFIG: Required<WebSocketConfig> = {
  url: import.meta.env['VITE_WS_URL'] ?? 'ws://localhost:8000',
  autoConnect: true,
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 5000,
  timeout: 20000,
  transports: ['websocket', 'polling'],
} as const;

/**
 * WebSocket error class
 */
export class WebSocketError extends Error {
  constructor(
    message: string,
    public readonly code?: string,
    public readonly details?: unknown,
  ) {
    super(message);
    this.name = 'WebSocketError';
  }
}

/**
 * Type guard for order status changed message
 */
function isOrderStatusChangedMessage(
  message: OrderWebSocketMessage,
): message is OrderStatusChangedMessage {
  return message.type === 'order_status_changed';
}

/**
 * Type guard for delivery estimate updated message
 */
function isDeliveryEstimateUpdatedMessage(
  message: OrderWebSocketMessage,
): message is DeliveryEstimateUpdatedMessage {
  return message.type === 'delivery_estimate_updated';
}

/**
 * Type guard for timeline updated message
 */
function isTimelineUpdatedMessage(
  message: OrderWebSocketMessage,
): message is TimelineUpdatedMessage {
  return message.type === 'timeline_updated';
}

/**
 * Custom hook for WebSocket connections with order status updates
 *
 * Provides real-time order tracking updates via WebSocket connection with:
 * - Automatic connection management
 * - Reconnection logic with exponential backoff
 * - Order subscription management
 * - Typed message handling
 * - Connection state tracking
 * - Error handling and recovery
 *
 * @param options - WebSocket configuration and event handlers
 * @returns WebSocket connection state and control methods
 *
 * @example
 * ```tsx
 * const { isConnected, subscribe, lastMessage } = useWebSocket({
 *   orderId: 'order-123',
 *   onStatusChange: (message) => {
 *     console.log('Order status changed:', message.data);
 *   },
 *   onDeliveryUpdate: (message) => {
 *     console.log('Delivery estimate updated:', message.data);
 *   },
 * });
 * ```
 */
export function useWebSocket(options: UseWebSocketOptions = {}): UseWebSocketReturn {
  const {
    url = DEFAULT_CONFIG.url,
    autoConnect = DEFAULT_CONFIG.autoConnect,
    reconnection = DEFAULT_CONFIG.reconnection,
    reconnectionAttempts = DEFAULT_CONFIG.reconnectionAttempts,
    reconnectionDelay = DEFAULT_CONFIG.reconnectionDelay,
    reconnectionDelayMax = DEFAULT_CONFIG.reconnectionDelayMax,
    timeout = DEFAULT_CONFIG.timeout,
    transports = DEFAULT_CONFIG.transports,
    orderId,
    onMessage,
    onStatusChange,
    onDeliveryUpdate,
    onTimelineUpdate,
    onConnect,
    onDisconnect,
    onError,
    enabled = true,
  } = options;

  // State
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [error, setError] = useState<Error | null>(null);
  const [lastMessage, setLastMessage] = useState<OrderWebSocketMessage | null>(null);

  // Refs for stable references
  const socketRef = useRef<Socket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const subscribedOrdersRef = useRef<Set<string>>(new Set());

  // Stable callback refs
  const onMessageRef = useRef(onMessage);
  const onStatusChangeRef = useRef(onStatusChange);
  const onDeliveryUpdateRef = useRef(onDeliveryUpdate);
  const onTimelineUpdateRef = useRef(onTimelineUpdate);
  const onConnectRef = useRef(onConnect);
  const onDisconnectRef = useRef(onDisconnect);
  const onErrorRef = useRef(onError);

  // Update callback refs
  useEffect(() => {
    onMessageRef.current = onMessage;
    onStatusChangeRef.current = onStatusChange;
    onDeliveryUpdateRef.current = onDeliveryUpdate;
    onTimelineUpdateRef.current = onTimelineUpdate;
    onConnectRef.current = onConnect;
    onDisconnectRef.current = onDisconnect;
    onErrorRef.current = onError;
  }, [onMessage, onStatusChange, onDeliveryUpdate, onTimelineUpdate, onConnect, onDisconnect, onError]);

  /**
   * Handle incoming WebSocket messages
   */
  const handleMessage = useCallback((message: OrderWebSocketMessage) => {
    try {
      setLastMessage(message);
      setError(null);

      // Call generic message handler
      if (onMessageRef.current) {
        onMessageRef.current(message);
      }

      // Call specific handlers based on message type
      if (isOrderStatusChangedMessage(message) && onStatusChangeRef.current) {
        onStatusChangeRef.current(message);
      } else if (isDeliveryEstimateUpdatedMessage(message) && onDeliveryUpdateRef.current) {
        onDeliveryUpdateRef.current(message);
      } else if (isTimelineUpdatedMessage(message) && onTimelineUpdateRef.current) {
        onTimelineUpdateRef.current(message);
      }
    } catch (err) {
      const wsError = new WebSocketError(
        'Failed to handle WebSocket message',
        'MESSAGE_HANDLER_ERROR',
        err,
      );
      setError(wsError);
      if (onErrorRef.current) {
        onErrorRef.current(wsError);
      }
    }
  }, []);

  /**
   * Subscribe to order updates
   */
  const subscribe = useCallback((orderIdToSubscribe: string) => {
    const socket = socketRef.current;
    if (!socket?.connected) {
      console.warn('Cannot subscribe: WebSocket not connected');
      return;
    }

    if (subscribedOrdersRef.current.has(orderIdToSubscribe)) {
      return;
    }

    try {
      socket.emit('subscribe', { orderId: orderIdToSubscribe });
      subscribedOrdersRef.current.add(orderIdToSubscribe);
    } catch (err) {
      const wsError = new WebSocketError(
        `Failed to subscribe to order ${orderIdToSubscribe}`,
        'SUBSCRIBE_ERROR',
        err,
      );
      setError(wsError);
      if (onErrorRef.current) {
        onErrorRef.current(wsError);
      }
    }
  }, []);

  /**
   * Unsubscribe from order updates
   */
  const unsubscribe = useCallback((orderIdToUnsubscribe: string) => {
    const socket = socketRef.current;
    if (!socket?.connected) {
      return;
    }

    if (!subscribedOrdersRef.current.has(orderIdToUnsubscribe)) {
      return;
    }

    try {
      socket.emit('unsubscribe', { orderId: orderIdToUnsubscribe });
      subscribedOrdersRef.current.delete(orderIdToUnsubscribe);
    } catch (err) {
      const wsError = new WebSocketError(
        `Failed to unsubscribe from order ${orderIdToUnsubscribe}`,
        'UNSUBSCRIBE_ERROR',
        err,
      );
      setError(wsError);
      if (onErrorRef.current) {
        onErrorRef.current(wsError);
      }
    }
  }, []);

  /**
   * Connect to WebSocket server
   */
  const connect = useCallback(() => {
    if (socketRef.current?.connected) {
      return;
    }

    try {
      setConnectionState('connecting');
      setError(null);

      const socket = io(url, {
        reconnection,
        reconnectionAttempts,
        reconnectionDelay,
        reconnectionDelayMax,
        timeout,
        transports: [...transports],
        autoConnect: false,
      });

      // Connection event handlers
      socket.on('connect', () => {
        setConnectionState('connected');
        setError(null);
        reconnectAttemptsRef.current = 0;

        // Resubscribe to orders after reconnection
        subscribedOrdersRef.current.forEach((orderIdToResubscribe) => {
          socket.emit('subscribe', { orderId: orderIdToResubscribe });
        });

        if (onConnectRef.current) {
          onConnectRef.current();
        }
      });

      socket.on('disconnect', (reason: string) => {
        setConnectionState('disconnected');
        if (onDisconnectRef.current) {
          onDisconnectRef.current(reason);
        }
      });

      socket.on('connect_error', (err: Error) => {
        const wsError = new WebSocketError(
          'WebSocket connection error',
          'CONNECTION_ERROR',
          err,
        );
        setError(wsError);
        setConnectionState('error');

        if (onErrorRef.current) {
          onErrorRef.current(wsError);
        }
      });

      socket.on('reconnect_attempt', () => {
        reconnectAttemptsRef.current += 1;
        setConnectionState('reconnecting');
      });

      socket.on('reconnect_failed', () => {
        const wsError = new WebSocketError(
          'Failed to reconnect after maximum attempts',
          'RECONNECT_FAILED',
        );
        setError(wsError);
        setConnectionState('error');

        if (onErrorRef.current) {
          onErrorRef.current(wsError);
        }
      });

      // Order update event handlers
      socket.on('order_update', (message: OrderWebSocketMessage) => {
        handleMessage(message);
      });

      socket.on('error', (err: Error) => {
        const wsError = new WebSocketError('WebSocket error', 'SOCKET_ERROR', err);
        setError(wsError);
        if (onErrorRef.current) {
          onErrorRef.current(wsError);
        }
      });

      socketRef.current = socket;
      socket.connect();
    } catch (err) {
      const wsError = new WebSocketError('Failed to initialize WebSocket', 'INIT_ERROR', err);
      setError(wsError);
      setConnectionState('error');
      if (onErrorRef.current) {
        onErrorRef.current(wsError);
      }
    }
  }, [
    url,
    reconnection,
    reconnectionAttempts,
    reconnectionDelay,
    reconnectionDelayMax,
    timeout,
    transports,
    handleMessage,
  ]);

  /**
   * Disconnect from WebSocket server
   */
  const disconnect = useCallback(() => {
    const socket = socketRef.current;
    if (!socket) {
      return;
    }

    try {
      // Unsubscribe from all orders
      subscribedOrdersRef.current.forEach((orderIdToUnsubscribe) => {
        socket.emit('unsubscribe', { orderId: orderIdToUnsubscribe });
      });
      subscribedOrdersRef.current.clear();

      socket.disconnect();
      socketRef.current = null;
      setConnectionState('disconnected');
      setError(null);
    } catch (err) {
      const wsError = new WebSocketError('Failed to disconnect WebSocket', 'DISCONNECT_ERROR', err);
      setError(wsError);
      if (onErrorRef.current) {
        onErrorRef.current(wsError);
      }
    }
  }, []);

  /**
   * Reconnect to WebSocket server
   */
  const reconnect = useCallback(() => {
    disconnect();
    setTimeout(() => {
      connect();
    }, 100);
  }, [connect, disconnect]);

  // Auto-connect on mount if enabled
  useEffect(() => {
    if (enabled && autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [enabled, autoConnect, connect, disconnect]);

  // Subscribe to initial order if provided
  useEffect(() => {
    if (orderId && connectionState === 'connected') {
      subscribe(orderId);
    }
  }, [orderId, connectionState, subscribe]);

  // Computed state
  const isConnected = connectionState === 'connected';
  const isConnecting = connectionState === 'connecting' || connectionState === 'reconnecting';

  return {
    connectionState,
    isConnected,
    isConnecting,
    error,
    lastMessage,
    connect,
    disconnect,
    reconnect,
    subscribe,
    unsubscribe,
  };
}

/**
 * Type guard for WebSocket error
 */
export function isWebSocketError(error: unknown): error is WebSocketError {
  return error instanceof WebSocketError;
}

export default useWebSocket;