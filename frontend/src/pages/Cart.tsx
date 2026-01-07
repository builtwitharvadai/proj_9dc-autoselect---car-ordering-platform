import { useState } from 'react';

interface CartItem {
  readonly id: string;
  readonly name: string;
  readonly description: string;
  readonly price: number;
  readonly quantity: number;
  readonly imageUrl: string;
  readonly category: string;
}

interface CartState {
  readonly items: readonly CartItem[];
  readonly subtotal: number;
  readonly tax: number;
  readonly total: number;
}

const MOCK_CART_ITEMS: readonly CartItem[] = [
  {
    id: '1',
    name: '2024 Luxury Sedan',
    description: 'Premium sedan with advanced features',
    price: 45000,
    quantity: 1,
    imageUrl: 'https://via.placeholder.com/150x100?text=Luxury+Sedan',
    category: 'Vehicle',
  },
  {
    id: '2',
    name: 'Premium Paint Package',
    description: 'Metallic finish with ceramic coating',
    price: 1500,
    quantity: 1,
    imageUrl: 'https://via.placeholder.com/150x100?text=Paint+Package',
    category: 'Exterior',
  },
  {
    id: '3',
    name: 'Leather Interior Package',
    description: 'Premium leather seats with heating and ventilation',
    price: 3000,
    quantity: 1,
    imageUrl: 'https://via.placeholder.com/150x100?text=Leather+Interior',
    category: 'Interior',
  },
] as const;

const TAX_RATE = 0.08;

export default function Cart(): JSX.Element {
  const [cart, setCart] = useState<CartState>(() => {
    const subtotal = MOCK_CART_ITEMS.reduce(
      (sum, item) => sum + item.price * item.quantity,
      0
    );
    const tax = subtotal * TAX_RATE;
    const total = subtotal + tax;

    return {
      items: MOCK_CART_ITEMS,
      subtotal,
      tax,
      total,
    };
  });

  const handleQuantityChange = (itemId: string, newQuantity: number): void => {
    if (newQuantity < 1) return;

    setCart((prev) => {
      const updatedItems = prev.items.map((item) =>
        item.id === itemId ? { ...item, quantity: newQuantity } : item
      );

      const subtotal = updatedItems.reduce(
        (sum, item) => sum + item.price * item.quantity,
        0
      );
      const tax = subtotal * TAX_RATE;
      const total = subtotal + tax;

      return {
        items: updatedItems,
        subtotal,
        tax,
        total,
      };
    });
  };

  const handleRemoveItem = (itemId: string): void => {
    setCart((prev) => {
      const updatedItems = prev.items.filter((item) => item.id !== itemId);

      const subtotal = updatedItems.reduce(
        (sum, item) => sum + item.price * item.quantity,
        0
      );
      const tax = subtotal * TAX_RATE;
      const total = subtotal + tax;

      return {
        items: updatedItems,
        subtotal,
        tax,
        total,
      };
    });
  };

  const formatPrice = (price: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(price);
  };

  return (
    <div className="min-h-screen bg-[rgb(var(--color-gray-50))] pt-16">
      <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[rgb(var(--color-gray-900))] sm:text-4xl">
            Shopping Cart
          </h1>
          <p className="mt-2 text-base text-[rgb(var(--color-gray-600))] sm:text-lg">
            Review your selected items and proceed to checkout
          </p>
        </div>

        {cart.items.length === 0 ? (
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
                d="M16 11V7a4 4 0 00-8 0v4M5 9h14l1 12H4L5 9z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-[rgb(var(--color-gray-900))]">
              Your cart is empty
            </h3>
            <p className="mt-2 text-sm text-[rgb(var(--color-gray-600))]">
              Start browsing vehicles and add items to your cart
            </p>
            <button
              type="button"
              className="mt-6 rounded-[var(--radius-md)] bg-[rgb(var(--color-primary-600))] px-6 py-3 text-base font-medium text-white transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-primary-700))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
              aria-label="Browse vehicles"
            >
              Browse Vehicles
            </button>
          </div>
        ) : (
          <div className="grid gap-8 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <div className="space-y-4">
                {cart.items.map((item) => (
                  <article
                    key={item.id}
                    className="overflow-hidden rounded-[var(--radius-lg)] bg-white shadow-[var(--shadow-sm)] transition-shadow duration-[var(--transition-base)] hover:shadow-[var(--shadow-md)]"
                  >
                    <div className="flex flex-col gap-4 p-6 sm:flex-row">
                      <div className="flex-shrink-0">
                        <img
                          src={item.imageUrl}
                          alt={item.name}
                          className="h-24 w-full rounded-[var(--radius-md)] object-cover sm:w-36"
                          loading="lazy"
                        />
                      </div>

                      <div className="flex flex-1 flex-col justify-between">
                        <div>
                          <div className="flex items-start justify-between">
                            <div>
                              <h3 className="text-lg font-semibold text-[rgb(var(--color-gray-900))]">
                                {item.name}
                              </h3>
                              <p className="mt-1 text-sm text-[rgb(var(--color-gray-600))]">
                                {item.description}
                              </p>
                              <span className="mt-2 inline-flex items-center rounded-[var(--radius-full)] bg-[rgb(var(--color-primary-50))] px-3 py-1 text-xs font-medium text-[rgb(var(--color-primary-700))]">
                                {item.category}
                              </span>
                            </div>
                            <button
                              type="button"
                              onClick={() => handleRemoveItem(item.id)}
                              className="text-[rgb(var(--color-gray-400))] transition-colors duration-[var(--transition-fast)] hover:text-[rgb(var(--color-gray-600))]"
                              aria-label={`Remove ${item.name} from cart`}
                            >
                              <svg
                                className="h-5 w-5"
                                fill="none"
                                viewBox="0 0 24 24"
                                stroke="currentColor"
                                aria-hidden="true"
                              >
                                <path
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  strokeWidth={2}
                                  d="M6 18L18 6M6 6l12 12"
                                />
                              </svg>
                            </button>
                          </div>
                        </div>

                        <div className="mt-4 flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <label
                              htmlFor={`quantity-${item.id}`}
                              className="text-sm font-medium text-[rgb(var(--color-gray-700))]"
                            >
                              Quantity:
                            </label>
                            <div className="flex items-center gap-2">
                              <button
                                type="button"
                                onClick={() =>
                                  handleQuantityChange(item.id, item.quantity - 1)
                                }
                                disabled={item.quantity <= 1}
                                className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] border border-[rgb(var(--color-gray-300))] text-[rgb(var(--color-gray-700))] transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-gray-100))] disabled:cursor-not-allowed disabled:opacity-50"
                                aria-label={`Decrease quantity of ${item.name}`}
                              >
                                <svg
                                  className="h-4 w-4"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  aria-hidden="true"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M20 12H4"
                                  />
                                </svg>
                              </button>
                              <input
                                type="number"
                                id={`quantity-${item.id}`}
                                value={item.quantity}
                                onChange={(e) => {
                                  const value = parseInt(e.target.value, 10);
                                  if (!isNaN(value) && value > 0) {
                                    handleQuantityChange(item.id, value);
                                  }
                                }}
                                min="1"
                                className="w-16 rounded-[var(--radius-md)] border border-[rgb(var(--color-gray-300))] px-3 py-1 text-center text-sm text-[rgb(var(--color-gray-900))] focus:border-[rgb(var(--color-primary-500))] focus:outline-none focus:ring-2 focus:ring-[rgb(var(--color-primary-500))] focus:ring-opacity-20"
                                aria-label={`Quantity of ${item.name}`}
                              />
                              <button
                                type="button"
                                onClick={() =>
                                  handleQuantityChange(item.id, item.quantity + 1)
                                }
                                className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-md)] border border-[rgb(var(--color-gray-300))] text-[rgb(var(--color-gray-700))] transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-gray-100))]"
                                aria-label={`Increase quantity of ${item.name}`}
                              >
                                <svg
                                  className="h-4 w-4"
                                  fill="none"
                                  viewBox="0 0 24 24"
                                  stroke="currentColor"
                                  aria-hidden="true"
                                >
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M12 4v16m8-8H4"
                                  />
                                </svg>
                              </button>
                            </div>
                          </div>
                          <div className="text-lg font-bold text-[rgb(var(--color-gray-900))]">
                            {formatPrice(item.price * item.quantity)}
                          </div>
                        </div>
                      </div>
                    </div>
                  </article>
                ))}
              </div>
            </div>

            <div className="lg:col-span-1">
              <div className="sticky top-20 rounded-[var(--radius-lg)] bg-white p-6 shadow-[var(--shadow-sm)]">
                <h2 className="mb-4 text-xl font-semibold text-[rgb(var(--color-gray-900))]">
                  Order Summary
                </h2>

                <div className="space-y-3 border-b border-[rgb(var(--color-gray-200))] pb-4">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[rgb(var(--color-gray-600))]">
                      Subtotal ({cart.items.length}{' '}
                      {cart.items.length === 1 ? 'item' : 'items'})
                    </span>
                    <span className="font-medium text-[rgb(var(--color-gray-900))]">
                      {formatPrice(cart.subtotal)}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-[rgb(var(--color-gray-600))]">
                      Tax (8%)
                    </span>
                    <span className="font-medium text-[rgb(var(--color-gray-900))]">
                      {formatPrice(cart.tax)}
                    </span>
                  </div>
                </div>

                <div className="mt-4 flex items-center justify-between">
                  <span className="text-lg font-bold text-[rgb(var(--color-gray-900))]">
                    Total
                  </span>
                  <span className="text-2xl font-bold text-[rgb(var(--color-primary-600))]">
                    {formatPrice(cart.total)}
                  </span>
                </div>

                <button
                  type="button"
                  className="mt-6 w-full rounded-[var(--radius-md)] bg-[rgb(var(--color-primary-600))] px-6 py-3 text-base font-medium text-white transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-primary-700))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-primary-600))]"
                  aria-label="Proceed to checkout"
                >
                  Proceed to Checkout
                </button>

                <button
                  type="button"
                  className="mt-3 w-full rounded-[var(--radius-md)] border border-[rgb(var(--color-gray-300))] bg-white px-6 py-3 text-base font-medium text-[rgb(var(--color-gray-700))] transition-colors duration-[var(--transition-fast)] hover:bg-[rgb(var(--color-gray-50))] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[rgb(var(--color-gray-500))]"
                  aria-label="Continue shopping"
                >
                  Continue Shopping
                </button>

                <div className="mt-6 space-y-3 border-t border-[rgb(var(--color-gray-200))] pt-4">
                  <div className="flex items-center gap-2 text-sm text-[rgb(var(--color-gray-600))]">
                    <svg
                      className="h-5 w-5 text-[rgb(var(--color-primary-600))]"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span>Secure checkout</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-[rgb(var(--color-gray-600))]">
                    <svg
                      className="h-5 w-5 text-[rgb(var(--color-primary-600))]"
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
                    <span>Free delivery on orders over $50,000</span>
                  </div>
                  <div className="flex items-center gap-2 text-sm text-[rgb(var(--color-gray-600))]">
                    <svg
                      className="h-5 w-5 text-[rgb(var(--color-primary-600))]"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      aria-hidden="true"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                      />
                    </svg>
                    <span>Estimated delivery: 4-6 weeks</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}