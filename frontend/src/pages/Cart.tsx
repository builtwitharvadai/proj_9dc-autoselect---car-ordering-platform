import { CartProvider } from '../contexts/CartContext';
import CartPage from '../components/Cart/CartPage';

export default function Cart(): JSX.Element {
  return (
    <CartProvider enableOptimisticUpdates={true} enableAutoRefresh={true}>
      <CartPage />
    </CartProvider>
  );
}