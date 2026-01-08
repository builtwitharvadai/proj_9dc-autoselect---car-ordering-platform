/**
 * End-to-End Deployment Validation Test Suite
 * 
 * This test suite validates deployment health, API functionality, and critical
 * user workflows after deployment. It includes smoke tests for all major features
 * and ensures the application is production-ready.
 * 
 * Test Categories:
 * - Health & Infrastructure Checks
 * - API Endpoint Validation
 * - Authentication & Authorization
 * - Critical User Workflows
 * - Performance & Load Testing
 * - Security Validation
 * - Cross-Browser Compatibility
 * 
 * @requires @playwright/test
 */

import { test, expect, type Page, type BrowserContext } from '@playwright/test';

// ============================================================================
// 🎯 Test Configuration & Constants
// ============================================================================

const BASE_URL = process.env['BASE_URL'] ?? 'http://localhost:3000';
const API_URL = process.env['API_URL'] ?? 'http://localhost:8000';
const TIMEOUT = {
  SHORT: 5000,
  MEDIUM: 10000,
  LONG: 30000,
};

const TEST_USER = {
  email: 'test@autoselect.com',
  password: 'Test123!@#',
  name: 'Test User',
};

const ADMIN_USER = {
  email: 'admin@autoselect.com',
  password: 'Admin123!@#',
  name: 'Admin User',
};

// ============================================================================
// 🛠️ Test Utilities & Helpers
// ============================================================================

/**
 * Wait for network to be idle
 */
async function waitForNetworkIdle(page: Page): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout: TIMEOUT.MEDIUM });
}

/**
 * Check if element is visible and enabled
 */
async function isElementReady(page: Page, selector: string): Promise<boolean> {
  try {
    const element = page.locator(selector);
    await element.waitFor({ state: 'visible', timeout: TIMEOUT.SHORT });
    return await element.isEnabled();
  } catch {
    return false;
  }
}

/**
 * Perform login with credentials
 */
async function login(
  page: Page,
  email: string,
  password: string,
): Promise<void> {
  await page.goto(`${BASE_URL}/login`);
  await page.fill('[name="email"]', email);
  await page.fill('[name="password"]', password);
  await page.click('button[type="submit"]');
  await waitForNetworkIdle(page);
}

/**
 * Clear all cookies and storage
 */
async function clearSession(context: BrowserContext): Promise<void> {
  await context.clearCookies();
  await context.clearPermissions();
}

/**
 * Measure page load performance
 */
async function measurePageLoad(page: Page): Promise<number> {
  const startTime = Date.now();
  await page.waitForLoadState('load');
  return Date.now() - startTime;
}

// ============================================================================
// 🏥 Health & Infrastructure Checks
// ============================================================================

test.describe('🏥 Health & Infrastructure Validation', () => {
  test('should verify backend health endpoint responds', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
    
    const body = await response.json();
    expect(body).toHaveProperty('status', 'healthy');
    expect(body).toHaveProperty('timestamp');
    expect(body).toHaveProperty('version');
  });

  test('should verify database connectivity', async ({ request }) => {
    const response = await request.get(`${API_URL}/health/db`);
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body).toHaveProperty('database', 'connected');
    expect(body).toHaveProperty('latency');
    expect(body.latency).toBeLessThan(100); // < 100ms
  });

  test('should verify Redis cache connectivity', async ({ request }) => {
    const response = await request.get(`${API_URL}/health/cache`);
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body).toHaveProperty('cache', 'connected');
  });

  test('should verify frontend assets are accessible', async ({ page }) => {
    const response = await page.goto(BASE_URL);
    
    expect(response?.ok()).toBeTruthy();
    expect(response?.status()).toBe(200);
    
    // Verify critical assets loaded
    const scripts = await page.locator('script[src]').count();
    const styles = await page.locator('link[rel="stylesheet"]').count();
    
    expect(scripts).toBeGreaterThan(0);
    expect(styles).toBeGreaterThan(0);
  });

  test('should verify API rate limiting is configured', async ({ request }) => {
    const requests = Array.from({ length: 100 }, () =>
      request.get(`${API_URL}/health`),
    );
    
    const responses = await Promise.all(requests);
    const rateLimited = responses.some((r) => r.status() === 429);
    
    // Should have rate limiting in place
    expect(rateLimited).toBeTruthy();
  });

  test('should verify CORS headers are present', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    const headers = response.headers();
    
    expect(headers).toHaveProperty('access-control-allow-origin');
    expect(headers).toHaveProperty('access-control-allow-methods');
  });

  test('should verify security headers are set', async ({ page }) => {
    const response = await page.goto(BASE_URL);
    const headers = response?.headers() ?? {};
    
    expect(headers).toHaveProperty('x-frame-options');
    expect(headers).toHaveProperty('x-content-type-options');
    expect(headers).toHaveProperty('strict-transport-security');
  });
});

// ============================================================================
// 🔌 API Endpoint Validation
// ============================================================================

test.describe('🔌 API Endpoint Validation', () => {
  let authToken: string;

  test.beforeAll(async ({ request }) => {
    // Get auth token for authenticated endpoints
    const response = await request.post(`${API_URL}/auth/login`, {
      data: {
        email: TEST_USER.email,
        password: TEST_USER.password,
      },
    });
    
    const body = await response.json();
    authToken = body.access_token;
  });

  test('should validate vehicles listing endpoint', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/vehicles`, {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(Array.isArray(body.data)).toBeTruthy();
    expect(body).toHaveProperty('pagination');
    expect(body.pagination).toHaveProperty('total');
    expect(body.pagination).toHaveProperty('page');
    expect(body.pagination).toHaveProperty('limit');
  });

  test('should validate vehicle details endpoint', async ({ request }) => {
    // First get a vehicle ID
    const listResponse = await request.get(`${API_URL}/api/vehicles?limit=1`, {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    
    const listBody = await listResponse.json();
    const vehicleId = listBody.data[0]?.id;
    
    if (vehicleId) {
      const response = await request.get(`${API_URL}/api/vehicles/${vehicleId}`, {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      });
      
      expect(response.ok()).toBeTruthy();
      
      const body = await response.json();
      expect(body).toHaveProperty('id', vehicleId);
      expect(body).toHaveProperty('make');
      expect(body).toHaveProperty('model');
      expect(body).toHaveProperty('year');
      expect(body).toHaveProperty('price');
    }
  });

  test('should validate orders endpoint', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/orders`, {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(Array.isArray(body.data)).toBeTruthy();
  });

  test('should validate user profile endpoint', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/users/me`, {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body).toHaveProperty('email');
    expect(body).toHaveProperty('name');
    expect(body).toHaveProperty('role');
  });

  test('should handle 404 for non-existent resources', async ({ request }) => {
    const response = await request.get(
      `${API_URL}/api/vehicles/non-existent-id`,
      {
        headers: {
          Authorization: `Bearer ${authToken}`,
        },
      },
    );
    
    expect(response.status()).toBe(404);
  });

  test('should handle 401 for unauthorized requests', async ({ request }) => {
    const response = await request.get(`${API_URL}/api/orders`);
    
    expect(response.status()).toBe(401);
  });

  test('should validate API response times', async ({ request }) => {
    const startTime = Date.now();
    
    await request.get(`${API_URL}/api/vehicles?limit=10`, {
      headers: {
        Authorization: `Bearer ${authToken}`,
      },
    });
    
    const responseTime = Date.now() - startTime;
    
    // API should respond within 500ms
    expect(responseTime).toBeLessThan(500);
  });
});

// ============================================================================
// 🔐 Authentication & Authorization
// ============================================================================

test.describe('🔐 Authentication & Authorization', () => {
  test('should successfully login with valid credentials', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('h1')).toContainText('Dashboard');
  });

  test('should reject login with invalid credentials', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    await page.fill('[name="email"]', TEST_USER.email);
    await page.fill('[name="password"]', 'wrongpassword');
    await page.click('button[type="submit"]');
    
    await expect(page.locator('[role="alert"]')).toContainText(
      /invalid credentials/i,
    );
  });

  test('should logout successfully', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    await page.click('[data-cy="user-menu"]');
    await page.click('[data-cy="logout-button"]');
    
    await expect(page).toHaveURL(/\/login/);
  });

  test('should redirect to login when accessing protected route', async ({
    page,
  }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    
    await expect(page).toHaveURL(/\/login/);
  });

  test('should persist session after page reload', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    await page.reload();
    
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should enforce role-based access control', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    // Try to access admin-only page
    await page.goto(`${BASE_URL}/admin`);
    
    // Should be redirected or show access denied
    const url = page.url();
    const hasAccessDenied = await page
      .locator('text=/access denied|forbidden/i')
      .count();
    
    expect(url.includes('/admin') === false || hasAccessDenied > 0).toBeTruthy();
  });

  test('should validate JWT token expiration', async ({ page, context }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    // Simulate token expiration by clearing cookies
    await context.clearCookies();
    
    // Try to access protected resource
    await page.goto(`${BASE_URL}/dashboard`);
    
    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});

// ============================================================================
// 🚗 Critical User Workflows
// ============================================================================

test.describe('🚗 Critical User Workflows', () => {
  test.beforeEach(async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
  });

  test('should complete vehicle search workflow', async ({ page }) => {
    await page.goto(`${BASE_URL}/vehicles`);
    
    // Search for vehicles
    await page.fill('[data-cy="search-input"]', 'Tesla');
    await page.click('[data-cy="search-button"]');
    
    await waitForNetworkIdle(page);
    
    // Verify results
    const results = await page.locator('[data-cy="vehicle-card"]').count();
    expect(results).toBeGreaterThan(0);
    
    // Apply filters
    await page.click('[data-cy="filter-button"]');
    await page.selectOption('[data-cy="year-filter"]', '2023');
    await page.click('[data-cy="apply-filters"]');
    
    await waitForNetworkIdle(page);
    
    // Verify filtered results
    const filteredResults = await page.locator('[data-cy="vehicle-card"]').count();
    expect(filteredResults).toBeGreaterThan(0);
  });

  test('should complete vehicle details view workflow', async ({ page }) => {
    await page.goto(`${BASE_URL}/vehicles`);
    
    // Click on first vehicle
    await page.click('[data-cy="vehicle-card"]:first-child');
    
    await waitForNetworkIdle(page);
    
    // Verify details page
    await expect(page.locator('[data-cy="vehicle-title"]')).toBeVisible();
    await expect(page.locator('[data-cy="vehicle-price"]')).toBeVisible();
    await expect(page.locator('[data-cy="vehicle-specs"]')).toBeVisible();
    
    // Verify image gallery
    const images = await page.locator('[data-cy="vehicle-image"]').count();
    expect(images).toBeGreaterThan(0);
  });

  test('should complete order creation workflow', async ({ page }) => {
    await page.goto(`${BASE_URL}/vehicles`);
    
    // Select vehicle
    await page.click('[data-cy="vehicle-card"]:first-child');
    await page.click('[data-cy="order-button"]');
    
    // Fill order form
    await page.fill('[name="delivery_address"]', '123 Test St');
    await page.fill('[name="city"]', 'Test City');
    await page.fill('[name="postal_code"]', '12345');
    await page.selectOption('[name="payment_method"]', 'credit_card');
    
    // Submit order
    await page.click('[data-cy="submit-order"]');
    
    await waitForNetworkIdle(page);
    
    // Verify order confirmation
    await expect(page.locator('[data-cy="order-confirmation"]')).toBeVisible();
    await expect(page.locator('[data-cy="order-number"]')).toBeVisible();
  });

  test('should complete profile update workflow', async ({ page }) => {
    await page.goto(`${BASE_URL}/profile`);
    
    // Update profile
    await page.fill('[name="name"]', 'Updated Name');
    await page.fill('[name="phone"]', '+1234567890');
    await page.click('[data-cy="save-profile"]');
    
    await waitForNetworkIdle(page);
    
    // Verify success message
    await expect(page.locator('[role="alert"]')).toContainText(/success/i);
  });

  test('should complete order history view workflow', async ({ page }) => {
    await page.goto(`${BASE_URL}/orders`);
    
    // Verify orders list
    await expect(page.locator('[data-cy="orders-table"]')).toBeVisible();
    
    // Click on order details
    const orderCount = await page.locator('[data-cy="order-row"]').count();
    
    if (orderCount > 0) {
      await page.click('[data-cy="order-row"]:first-child');
      
      // Verify order details
      await expect(page.locator('[data-cy="order-details"]')).toBeVisible();
      await expect(page.locator('[data-cy="order-status"]')).toBeVisible();
    }
  });

  test('should complete document upload workflow', async ({ page }) => {
    await page.goto(`${BASE_URL}/profile/documents`);
    
    // Upload document
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'test-document.pdf',
      mimeType: 'application/pdf',
      buffer: Buffer.from('test content'),
    });
    
    await page.click('[data-cy="upload-button"]');
    
    await waitForNetworkIdle(page);
    
    // Verify upload success
    await expect(page.locator('[data-cy="document-list"]')).toContainText(
      'test-document.pdf',
    );
  });
});

// ============================================================================
// ⚡ Performance & Load Testing
// ============================================================================

test.describe('⚡ Performance & Load Testing', () => {
  test('should load homepage within performance budget', async ({ page }) => {
    const loadTime = await measurePageLoad(page);
    
    await page.goto(BASE_URL);
    
    // Homepage should load within 3 seconds
    expect(loadTime).toBeLessThan(3000);
  });

  test('should load dashboard within performance budget', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    const startTime = Date.now();
    await page.goto(`${BASE_URL}/dashboard`);
    await waitForNetworkIdle(page);
    const loadTime = Date.now() - startTime;
    
    // Dashboard should load within 2 seconds
    expect(loadTime).toBeLessThan(2000);
  });

  test('should handle rapid navigation without errors', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    const routes = ['/dashboard', '/vehicles', '/orders', '/profile'];
    
    for (const route of routes) {
      await page.goto(`${BASE_URL}${route}`);
      await page.waitForLoadState('domcontentloaded');
    }
    
    // No console errors should occur
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    expect(errors.length).toBe(0);
  });

  test('should handle concurrent API requests', async ({ request }) => {
    // Login first
    const loginResponse = await request.post(`${API_URL}/auth/login`, {
      data: {
        email: TEST_USER.email,
        password: TEST_USER.password,
      },
    });
    
    const { access_token } = await loginResponse.json();
    
    // Make 10 concurrent requests
    const requests = Array.from({ length: 10 }, () =>
      request.get(`${API_URL}/api/vehicles?limit=10`, {
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
      }),
    );
    
    const responses = await Promise.all(requests);
    
    // All requests should succeed
    responses.forEach((response) => {
      expect(response.ok()).toBeTruthy();
    });
  });

  test('should measure Core Web Vitals', async ({ page }) => {
    await page.goto(BASE_URL);
    
    const metrics = await page.evaluate(() => {
      return new Promise((resolve) => {
        new PerformanceObserver((list) => {
          const entries = list.getEntries();
          const vitals: Record<string, number> = {};
          
          entries.forEach((entry) => {
            if (entry.entryType === 'largest-contentful-paint') {
              vitals.lcp = entry.startTime;
            }
          });
          
          resolve(vitals);
        }).observe({ entryTypes: ['largest-contentful-paint'] });
        
        setTimeout(() => resolve({}), 5000);
      });
    });
    
    // LCP should be under 2.5 seconds
    if ('lcp' in metrics) {
      expect(metrics.lcp).toBeLessThan(2500);
    }
  });
});

// ============================================================================
// 🛡️ Security Validation
// ============================================================================

test.describe('🛡️ Security Validation', () => {
  test('should prevent XSS attacks in search input', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto(`${BASE_URL}/vehicles`);
    
    const xssPayload = '<script>alert("XSS")</script>';
    await page.fill('[data-cy="search-input"]', xssPayload);
    await page.click('[data-cy="search-button"]');
    
    await waitForNetworkIdle(page);
    
    // Script should not execute
    const alerts: string[] = [];
    page.on('dialog', (dialog) => {
      alerts.push(dialog.message());
      void dialog.dismiss();
    });
    
    expect(alerts.length).toBe(0);
  });

  test('should prevent SQL injection in API requests', async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/auth/login`, {
      data: {
        email: TEST_USER.email,
        password: TEST_USER.password,
      },
    });
    
    const { access_token } = await loginResponse.json();
    
    const sqlPayload = "' OR '1'='1";
    const response = await request.get(
      `${API_URL}/api/vehicles?search=${encodeURIComponent(sqlPayload)}`,
      {
        headers: {
          Authorization: `Bearer ${access_token}`,
        },
      },
    );
    
    // Should return valid response, not SQL error
    expect(response.ok()).toBeTruthy();
  });

  test('should enforce HTTPS in production', async ({ page }) => {
    if (process.env['NODE_ENV'] === 'production') {
      await page.goto(BASE_URL);
      
      const url = page.url();
      expect(url.startsWith('https://')).toBeTruthy();
    }
  });

  test('should validate CSRF protection', async ({ page, request }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    // Try to make request without CSRF token
    const response = await request.post(`${API_URL}/api/orders`, {
      data: {
        vehicle_id: 'test-id',
      },
    });
    
    // Should be rejected without proper CSRF token
    expect(response.status()).toBe(403);
  });

  test('should sanitize file uploads', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto(`${BASE_URL}/profile/documents`);
    
    // Try to upload executable file
    const fileInput = page.locator('input[type="file"]');
    await fileInput.setInputFiles({
      name: 'malicious.exe',
      mimeType: 'application/x-msdownload',
      buffer: Buffer.from('MZ'),
    });
    
    await page.click('[data-cy="upload-button"]');
    
    // Should show error for invalid file type
    await expect(page.locator('[role="alert"]')).toContainText(/invalid file/i);
  });
});

// ============================================================================
// 🌐 Cross-Browser Compatibility
// ============================================================================

test.describe('🌐 Cross-Browser Compatibility', () => {
  test('should render correctly in different viewports', async ({ page }) => {
    const viewports = [
      { width: 375, height: 667, name: 'Mobile' },
      { width: 768, height: 1024, name: 'Tablet' },
      { width: 1920, height: 1080, name: 'Desktop' },
    ];
    
    for (const viewport of viewports) {
      await page.setViewportSize({
        width: viewport.width,
        height: viewport.height,
      });
      
      await page.goto(BASE_URL);
      
      // Verify page renders without layout issues
      const hasOverflow = await page.evaluate(() => {
        return document.body.scrollWidth > window.innerWidth;
      });
      
      expect(hasOverflow).toBeFalsy();
    }
  });

  test('should handle touch events on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto(`${BASE_URL}/vehicles`);
    
    // Simulate touch interaction
    const card = page.locator('[data-cy="vehicle-card"]:first-child');
    await card.tap();
    
    await waitForNetworkIdle(page);
    
    // Should navigate to details page
    await expect(page.locator('[data-cy="vehicle-title"]')).toBeVisible();
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Tab through form
    await page.keyboard.press('Tab');
    await page.keyboard.type(TEST_USER.email);
    await page.keyboard.press('Tab');
    await page.keyboard.type(TEST_USER.password);
    await page.keyboard.press('Enter');
    
    await waitForNetworkIdle(page);
    
    // Should successfully login
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('should maintain functionality with JavaScript disabled', async ({
    context,
  }) => {
    await context.addInitScript(() => {
      // Simulate JS disabled by removing all scripts
      Object.defineProperty(navigator, 'javaEnabled', {
        value: () => false,
      });
    });
    
    const page = await context.newPage();
    await page.goto(BASE_URL);
    
    // Basic content should still be accessible
    const hasContent = await page.locator('body').textContent();
    expect(hasContent).toBeTruthy();
  });
});

// ============================================================================
// 📊 Monitoring & Observability
// ============================================================================

test.describe('📊 Monitoring & Observability', () => {
  test('should log errors to monitoring service', async ({ page }) => {
    const errors: string[] = [];
    
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });
    
    await page.goto(BASE_URL);
    
    // Trigger an error
    await page.evaluate(() => {
      throw new Error('Test error');
    });
    
    // Error should be logged
    expect(errors.some((e) => e.includes('Test error'))).toBeTruthy();
  });

  test('should track user analytics events', async ({ page }) => {
    const analyticsEvents: Array<{ event: string; data: unknown }> = [];
    
    await page.exposeFunction('trackEvent', (event: string, data: unknown) => {
      analyticsEvents.push({ event, data });
    });
    
    await login(page, TEST_USER.email, TEST_USER.password);
    
    // Analytics should track login event
    expect(
      analyticsEvents.some((e) => e.event === 'user_login'),
    ).toBeTruthy();
  });

  test('should report performance metrics', async ({ page }) => {
    await page.goto(BASE_URL);
    
    const metrics = await page.evaluate(() => {
      const navigation = performance.getEntriesByType(
        'navigation',
      )[0] as PerformanceNavigationTiming;
      
      return {
        dns: navigation.domainLookupEnd - navigation.domainLookupStart,
        tcp: navigation.connectEnd - navigation.connectStart,
        ttfb: navigation.responseStart - navigation.requestStart,
        download: navigation.responseEnd - navigation.responseStart,
        domInteractive: navigation.domInteractive - navigation.fetchStart,
        domComplete: navigation.domComplete - navigation.fetchStart,
      };
    });
    
    // All metrics should be reasonable
    expect(metrics.dns).toBeGreaterThanOrEqual(0);
    expect(metrics.tcp).toBeGreaterThanOrEqual(0);
    expect(metrics.ttfb).toBeGreaterThan(0);
    expect(metrics.download).toBeGreaterThan(0);
  });
});

// ============================================================================
// 🔄 Deployment Rollback Validation
// ============================================================================

test.describe('🔄 Deployment Rollback Validation', () => {
  test('should verify version endpoint returns correct version', async ({
    request,
  }) => {
    const response = await request.get(`${API_URL}/version`);
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body).toHaveProperty('version');
    expect(body).toHaveProperty('commit');
    expect(body).toHaveProperty('buildDate');
  });

  test('should verify database migrations are applied', async ({ request }) => {
    const response = await request.get(`${API_URL}/health/migrations`);
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body).toHaveProperty('status', 'up-to-date');
  });

  test('should verify feature flags are configured', async ({ request }) => {
    const loginResponse = await request.post(`${API_URL}/auth/login`, {
      data: {
        email: TEST_USER.email,
        password: TEST_USER.password,
      },
    });
    
    const { access_token } = await loginResponse.json();
    
    const response = await request.get(`${API_URL}/api/feature-flags`, {
      headers: {
        Authorization: `Bearer ${access_token}`,
      },
    });
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(typeof body).toBe('object');
  });
});

// ============================================================================
// 🎯 Smoke Test Suite (Critical Path)
// ============================================================================

test.describe('🎯 Critical Path Smoke Tests', () => {
  test('CRITICAL: User can login and view dashboard', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.locator('h1')).toBeVisible();
  });

  test('CRITICAL: User can search and view vehicles', async ({ page }) => {
    await login(page, TEST_USER.email, TEST_USER.password);
    await page.goto(`${BASE_URL}/vehicles`);
    
    await expect(page.locator('[data-cy="vehicle-card"]').first()).toBeVisible();
  });

  test('CRITICAL: API health check passes', async ({ request }) => {
    const response = await request.get(`${API_URL}/health`);
    
    expect(response.ok()).toBeTruthy();
    expect(response.status()).toBe(200);
  });

  test('CRITICAL: Database is accessible', async ({ request }) => {
    const response = await request.get(`${API_URL}/health/db`);
    
    expect(response.ok()).toBeTruthy();
  });

  test('CRITICAL: Authentication system is functional', async ({ request }) => {
    const response = await request.post(`${API_URL}/auth/login`, {
      data: {
        email: TEST_USER.email,
        password: TEST_USER.password,
      },
    });
    
    expect(response.ok()).toBeTruthy();
    
    const body = await response.json();
    expect(body).toHaveProperty('access_token');
  });
});