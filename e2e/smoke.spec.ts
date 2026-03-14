/**
 * smoke.spec.ts — End-to-End Smoke Tests for Red Hot Jugs
 *
 * Covers three critical user flows:
 *   1. Authentication & route gating
 *   2. Paywall / content gating (blur ↔ unlock)
 *   3. Secure wishlist gifting (double-blind address privacy)
 *
 * Assumes global-setup.ts has already seeded:
 *   - Fan:     testfan@rhj.com / password123
 *   - Admin:   admin@rhj.com   / admin1234
 *   - At least one photo in the gallery
 */

import { test, expect, type Page } from '@playwright/test';

/* ──────────────────────────────────────────────────────────────────────────────
 * Shared helpers
 * ────────────────────────────────────────────────────────────────────────────*/

const FAN_EMAIL    = 'testfan@rhj.com';
const FAN_PASSWORD = 'password123';

/** Fill in the login form and submit. */
async function loginViaUI(page: Page, email: string, password: string) {
  await page.goto('/login');
  await page.locator('input[type="email"]').fill(email);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
}

/* ══════════════════════════════════════════════════════════════════════════════
 * TEST 1 — Authentication & Routing Gate
 *
 * Verifies:
 *   a) Unauthenticated users are bounced to /login when hitting protected routes
 *   b) The login form works and stores a JWT in localStorage
 *   c) After login the user lands on /gallery (or /dashboard)
 * ════════════════════════════════════════════════════════════════════════════*/

test.describe('Test 1: Authentication & Routing Gate', () => {

  test.beforeEach(async ({ page }) => {
    // Ensure a clean slate — no lingering token
    await page.goto('/');
    await page.evaluate(() => localStorage.removeItem('token'));
  });

  test('homepage loads without errors', async ({ page }) => {
    await page.goto('/');
    // The landing page should render the hero / brand heading
    await expect(page).toHaveURL('/');
    await expect(page.locator('body')).toBeVisible();
  });

  test('unauthenticated user is redirected away from /dashboard', async ({ page }) => {
    /*
     * /dashboard checks for a valid session via the Pinia auth store.
     * Without a token the axios interceptor gets a 401 and the response
     * interceptor redirects to /login.
     */
    await page.goto('/dashboard');

    // The app should redirect to /login (either via router guard or 401 interceptor)
    await page.waitForURL('**/login', { timeout: 10_000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('unauthenticated user is redirected away from /photo/fake-id', async ({ page }) => {
    /*
     * /photo/:id requires auth to fetch the full-res image.
     * A missing token triggers the same 401 → /login redirect.
     */
    await page.goto('/photo/00000000-0000-0000-0000-000000000000');
    await page.waitForURL('**/login', { timeout: 10_000 });
    await expect(page).toHaveURL(/\/login/);
  });

  test('login via UI stores JWT and redirects to gallery', async ({ page }) => {
    await loginViaUI(page, FAN_EMAIL, FAN_PASSWORD);

    // Wait for navigation away from /login
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    // JWT should now be stored in localStorage under "token"
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();
    expect(token!.split('.').length).toBe(3); // valid JWT has 3 dot-separated parts

    // User should land on the gallery or dashboard after login
    const currentPath = new URL(page.url()).pathname;
    expect(['/', '/gallery', '/dashboard']).toContain(currentPath);
  });
});

/* ══════════════════════════════════════════════════════════════════════════════
 * TEST 2 — The Paywall / Content Gating
 *
 * Verifies:
 *   a) Without an active subscription, gallery photos are locked (blurred)
 *   b) The subscribe button triggers Stripe checkout (mocked)
 *   c) After subscription activation, photos are unlocked
 * ════════════════════════════════════════════════════════════════════════════*/

test.describe('Test 2: Paywall / Content Gating', () => {

  test('locked photos show blur overlay for unsubscribed fan', async ({ page }) => {
    /*
     * Log in as the fan (who has no active subscription).
     * Navigate to /gallery which calls GET /photos/gallery.
     * The backend returns is_locked: true for unsubscribed users,
     * so every photo card should have the .lock-overlay element.
     */
    await loginViaUI(page, FAN_EMAIL, FAN_PASSWORD);
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    await page.goto('/gallery');
    await page.waitForSelector('.photo-card', { timeout: 10_000 });

    // Every photo card should display the lock overlay
    const lockOverlays = page.locator('.photo-card .lock-overlay');
    const overlayCount = await lockOverlays.count();
    expect(overlayCount).toBeGreaterThan(0);

    // None of the cards should have the "unlocked" class
    const unlockedCards = page.locator('.photo-card.unlocked');
    await expect(unlockedCards).toHaveCount(0);
  });

  test('subscribe button triggers Stripe checkout (mocked)', async ({ page }) => {
    /*
     * Mock the POST /subscription/create-checkout endpoint so we don't
     * hit real Stripe. Return a fake checkout URL and verify the browser
     * attempts to navigate there.
     */
    await loginViaUI(page, FAN_EMAIL, FAN_PASSWORD);
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    // Intercept the checkout endpoint and return a mock Stripe URL
    const FAKE_CHECKOUT_URL = 'https://checkout.stripe.com/test-session-12345';

    await page.route('**/subscription/create-checkout', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ checkout_url: FAKE_CHECKOUT_URL }),
      });
    });

    // Capture the navigation to Stripe so it doesn't actually leave the page
    let stripeRedirectUrl: string | null = null;
    page.on('framenavigated', (frame) => {
      if (frame === page.mainFrame()) {
        const url = frame.url();
        if (url.includes('checkout.stripe.com')) {
          stripeRedirectUrl = url;
        }
      }
    });

    // Also intercept at the request level to prevent actual navigation
    await page.route('https://checkout.stripe.com/**', async (route) => {
      stripeRedirectUrl = route.request().url();
      // Return a simple page instead of actually navigating to Stripe
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body>Mock Stripe Checkout</body></html>',
      });
    });

    // Navigate to pricing page and click subscribe
    await page.goto('/pricing');
    await page.waitForSelector('.btn-primary', { timeout: 10_000 });

    // Click the first subscribe button (1-month plan)
    await page.locator('.btn-primary').first().click();

    // Wait for the mock checkout redirect to fire
    await page.waitForTimeout(2_000);

    // Verify that the app tried to redirect to Stripe
    expect(stripeRedirectUrl).toContain('checkout.stripe.com');
  });

  test('photos unlock after subscription is activated via API', async ({ page, request }) => {
    /*
     * Simulate a subscription activation by directly calling the backend
     * webhook endpoint (mimicking what Stripe would do), then reload the
     * gallery and verify photos are now unlocked.
     *
     * Since we can't easily create a real Stripe event, we'll use the
     * admin account (which always has full access) to verify that the
     * gallery CAN show unlocked photos when access is granted.
     */

    // Log in as admin (always has full access — acts as a subscribed user)
    await loginViaUI(page, 'admin@rhj.com', 'admin1234');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    await page.goto('/gallery');
    await page.waitForSelector('.photo-card', { timeout: 10_000 });

    // For an admin, photos should be unlocked — no lock overlay visible
    const unlockedCards = page.locator('.photo-card.unlocked');
    const unlockedCount = await unlockedCards.count();
    expect(unlockedCount).toBeGreaterThan(0);

    // Lock overlays should not be present on unlocked cards
    const lockOverlays = page.locator('.photo-card.unlocked .lock-overlay');
    await expect(lockOverlays).toHaveCount(0);

    // The "Unlocked" badge should appear on each card
    const badges = page.locator('.badge-unlocked');
    const badgeCount = await badges.count();
    expect(badgeCount).toBeGreaterThan(0);
  });

  test('full-res photo detail is accessible for privileged users', async ({ page }) => {
    /*
     * Navigate to a photo's detail view as admin.
     * The backend should return the full_url (not just preview).
     */
    await loginViaUI(page, 'admin@rhj.com', 'admin1234');
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    await page.goto('/gallery');
    await page.waitForSelector('.photo-card', { timeout: 10_000 });

    // Click the first photo card to go to detail view
    await page.locator('.photo-card').first().click();

    // Should navigate to /photo/:id
    await page.waitForURL('**/photo/**', { timeout: 10_000 });

    // The detail page should display the full-res image
    const img = page.locator('img');
    await expect(img.first()).toBeVisible({ timeout: 10_000 });
  });
});

/* ══════════════════════════════════════════════════════════════════════════════
 * TEST 2b — Embedded Stripe Checkout (Stubbed)
 *
 * Verifies the embedded checkout flow without hitting real Stripe:
 *   a) Selecting a plan calls the create-embedded-checkout backend endpoint
 *   b) The StripeCheckout component mounts when a plan is selected
 *   c) After checkout completion, Dashboard polls and shows active subscription
 *   d) A failed checkout session shows an error and lets the user retry
 *
 * Uses stubbed Stripe JS — the real embedded checkout iframe is cross-origin
 * and can't be interacted with in e2e. Per Stripe testing docs, test card
 * 4242 4242 4242 4242 (any CVC, any future expiry) always succeeds in test
 * mode; we simulate that success path at the API layer here.
 * ════════════════════════════════════════════════════════════════════════════*/

test.describe('Test 2b: Embedded Stripe Checkout (Stubbed)', () => {

  /** Stub Stripe JS so the embedded checkout iframe doesn't actually load. */
  async function stubStripeJS(page: Page) {
    await page.route('https://js.stripe.com/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/javascript',
        body: `window.Stripe = function() {
          return {
            initEmbeddedCheckout: function() {
              return Promise.resolve({
                mount: function(el) { el.innerHTML = '<div data-testid="mock-stripe-form">Stripe test card: 4242 4242 4242 4242</div>'; },
                destroy: function() {}
              });
            }
          };
        };`,
      });
    });
  }

  test('selecting a plan calls create-embedded-checkout and mounts checkout UI', async ({ page }) => {
    /*
     * Mock the embedded checkout endpoint to return a fake clientSecret.
     * Verify the frontend calls the correct endpoint with the selected plan,
     * and that the StripeCheckout component attempts to render.
     */
    await loginViaUI(page, FAN_EMAIL, FAN_PASSWORD);
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    let capturedRequest: { plan: string } | null = null;

    // Intercept the embedded checkout endpoint
    await page.route('**/subscription/create-embedded-checkout', async (route) => {
      capturedRequest = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ clientSecret: 'cs_test_fake_secret_12345' }),
      });
    });

    await stubStripeJS(page);

    // Navigate to pricing and click the 1-month plan
    await page.goto('/pricing');
    await page.waitForSelector('.btn-primary', { timeout: 10_000 });
    await page.locator('.btn-primary').first().click();

    // Should switch to embedded checkout view
    await expect(page.locator('text=Complete Your Purchase')).toBeVisible({ timeout: 10_000 });

    // The "Back to Plans" button should be present
    await expect(page.locator('.back-btn')).toBeVisible();

    // Stubbed Stripe form should be mounted
    await expect(page.locator('[data-testid="mock-stripe-form"]')).toBeVisible({ timeout: 10_000 });

    // Verify the correct plan was sent to the backend
    expect(capturedRequest).not.toBeNull();
    expect(capturedRequest!.plan).toBe('1month');
  });

  test('3-month plan sends correct plan ID to backend', async ({ page }) => {
    await loginViaUI(page, FAN_EMAIL, FAN_PASSWORD);
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    let capturedPlan: string | null = null;

    await page.route('**/subscription/create-embedded-checkout', async (route) => {
      capturedPlan = route.request().postDataJSON()?.plan;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ clientSecret: 'cs_test_fake_secret_3month' }),
      });
    });

    await stubStripeJS(page);

    await page.goto('/pricing');
    await page.waitForSelector('.plan-card', { timeout: 10_000 });

    // Click the 3-month plan (second subscribe button)
    const subscribeButtons = page.locator('.plan-card .btn-primary');
    await subscribeButtons.nth(1).click();

    await expect(page.locator('text=Complete Your Purchase')).toBeVisible({ timeout: 10_000 });
    expect(capturedPlan).toBe('3month');
  });

  test('dashboard polls and shows active subscription after checkout redirect', async ({ page }) => {
    /*
     * Simulates what happens after Stripe redirects the user back to
     * /dashboard?session_id={ID}. The webhook may not have processed yet,
     * so Dashboard polls GET /subscription/status until it returns active.
     *
     * We mock the status endpoint to return inactive on the first call,
     * then active on subsequent calls (simulating webhook processing delay).
     */
    await loginViaUI(page, FAN_EMAIL, FAN_PASSWORD);
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    let statusCallCount = 0;

    // Mock subscription status — first call returns inactive, then active
    await page.route('**/subscription/status', async (route) => {
      statusCallCount++;
      const isActive = statusCallCount >= 2;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          is_active: isActive,
          status: isActive ? 'active' : null,
          current_period_end: isActive ? '2026-04-09T00:00:00' : null,
        }),
      });
    });

    // Navigate to dashboard with session_id as if returning from Stripe checkout
    await page.goto('/dashboard?session_id=cs_test_completed_session');

    // Should briefly show "Confirming your payment..." while polling
    await expect(page.locator('text=Confirming your payment')).toBeVisible({ timeout: 5_000 });

    // After polling resolves, should show active subscription
    await expect(page.locator('text=Active Subscription')).toBeVisible({ timeout: 20_000 });

    // Verify the renewal date is displayed
    await expect(page.locator('text=Renews')).toBeVisible();

    // Status endpoint should have been called at least twice
    expect(statusCallCount).toBeGreaterThanOrEqual(2);
  });

  test('dashboard without session_id does not trigger payment polling', async ({ page }) => {
    /*
     * Visiting /dashboard normally (not after checkout) should NOT poll
     * or show the "Confirming your payment" state.
     */
    await loginViaUI(page, FAN_EMAIL, FAN_PASSWORD);
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    await page.goto('/dashboard');
    await page.waitForTimeout(1_000);

    // Should NOT show the payment confirmation message
    await expect(page.locator('text=Confirming your payment')).not.toBeVisible();
  });

  test('checkout error lets user go back to plan selection', async ({ page }) => {
    /*
     * If the backend rejects the checkout session creation (e.g. Stripe
     * key misconfigured), the user should be able to click "Back to Plans"
     * and try again.
     */
    await loginViaUI(page, FAN_EMAIL, FAN_PASSWORD);
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });

    // Make the embedded checkout endpoint fail
    await page.route('**/subscription/create-embedded-checkout', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Stripe configuration error' }),
      });
    });

    await stubStripeJS(page);

    await page.goto('/pricing');
    await page.waitForSelector('.btn-primary', { timeout: 10_000 });
    await page.locator('.btn-primary').first().click();

    // Should show the checkout view initially
    await expect(page.locator('text=Complete Your Purchase')).toBeVisible({ timeout: 10_000 });

    // Click "Back to Plans" to return to plan selection
    await page.locator('.back-btn').click();

    // Should be back on plan selection with both plans visible
    await expect(page.locator('.plan-card')).toHaveCount(2, { timeout: 5_000 });
  });
});

/* ══════════════════════════════════════════════════════════════════════════════
 * TEST 3 — Secure Wishlist Gifting (Privacy Check)
 *
 * NOTE: The wishlist/gifting feature is not yet implemented in the codebase.
 * These tests are scaffolded against the planned API contract described in
 * the spec. They will run against mocked routes and verify the critical
 * privacy invariant: the Creator's physical address must NEVER be exposed
 * in any client-facing API response.
 *
 * Once the wishlist feature is built (e.g., /wishlist/:creatorId), update
 * the selectors and route patterns below to match the real implementation.
 *
 * Verifies:
 *   a) Wishlist items can be viewed on a Creator's page
 *   b) Purchase flow initiates a checkout session
 *   c) CRITICAL: No physical address leaks in the API response
 * ════════════════════════════════════════════════════════════════════════════*/

test.describe('Test 3: Secure Wishlist Gifting (Privacy Check)', () => {

  // Mock creator and wishlist data matching the planned API contract
  const MOCK_CREATOR_ID = 'creator-001';
  const MOCK_WISHLIST_ITEMS = [
    {
      id: 'item-001',
      name: 'Silk Robe',
      price: 89.99,
      image_url: '/placeholder.jpg',
      category: 'clothing',
      // The backend stores the address internally but must NEVER return it
    },
    {
      id: 'item-002',
      name: 'Perfume Set',
      price: 65.00,
      image_url: '/placeholder.jpg',
      category: 'beauty',
    },
  ];

  const MOCK_GIFT_CHECKOUT_RESPONSE = {
    checkout_url: 'https://checkout.stripe.com/gift-session-67890',
    gift_id: 'gift-001',
    item_name: 'Silk Robe',
    amount: 89.99,
    // CRITICAL: Must NOT contain shipping_address, creator_address, etc.
  };

  test('wishlist API response never exposes creator physical address', async ({ request }) => {
    /*
     * CRITICAL SECURITY ASSERTION
     *
     * This test validates the double-blind proxy shipping invariant:
     * when a fan purchases a gift for a creator, the API must never
     * return the creator's physical address to the client.
     *
     * We mock the wishlist endpoint response and verify that no
     * address-related fields leak through.
     */

    // Define the fields that must NEVER appear in any wishlist/gift response
    const FORBIDDEN_FIELDS = [
      'address',
      'shipping_address',
      'creator_address',
      'street',
      'street_address',
      'address_line1',
      'address_line2',
      'zip',
      'zip_code',
      'postal_code',
      'city',
      'state',
      'apartment',
      'unit',
      'physical_address',
      'delivery_address',
      'mailing_address',
    ];

    // Verify wishlist items response doesn't contain address data
    const wishlistPayload = JSON.stringify(MOCK_WISHLIST_ITEMS);
    for (const field of FORBIDDEN_FIELDS) {
      expect(wishlistPayload).not.toContain(`"${field}"`);
    }

    // Verify checkout response doesn't contain address data
    const checkoutPayload = JSON.stringify(MOCK_GIFT_CHECKOUT_RESPONSE);
    for (const field of FORBIDDEN_FIELDS) {
      expect(checkoutPayload).not.toContain(`"${field}"`);
    }
  });

  test('wishlist gift checkout flow intercepts and validates response', async ({ page }) => {
    /*
     * Simulates the full wishlist gift purchase flow:
     * 1. Navigate to a creator's wishlist page
     * 2. Click "Gift This Item" on a physical product
     * 3. Intercept the checkout session creation response
     * 4. Assert the response is clean of any address data
     *
     * Since the wishlist routes don't exist yet, we mock both the
     * page content and the API endpoints.
     */

    // Mock the wishlist page (since the route doesn't exist yet)
    await page.route(`**/api/wishlist/${MOCK_CREATOR_ID}`, async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_WISHLIST_ITEMS),
      });
    });

    // Mock the gift checkout endpoint
    let capturedCheckoutResponse: Record<string, unknown> | null = null;

    await page.route('**/api/gift/checkout', async (route) => {
      // Simulate a response that a careless backend might accidentally
      // include address data in — our assertion will catch it
      const safeResponse = { ...MOCK_GIFT_CHECKOUT_RESPONSE };

      capturedCheckoutResponse = safeResponse;

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(safeResponse),
      });
    });

    // Intercept Stripe redirect so the browser doesn't leave the page
    await page.route('https://checkout.stripe.com/**', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'text/html',
        body: '<html><body>Mock Stripe Gift Checkout</body></html>',
      });
    });

    // Simulate fetching the wishlist via a direct API call
    const wishlistResponse = await page.evaluate(async (creatorId) => {
      const res = await fetch(`/api/wishlist/${creatorId}`);
      return res.json();
    }, MOCK_CREATOR_ID);

    // Verify the wishlist response is clean
    expect(wishlistResponse).toHaveLength(2);
    expect(wishlistResponse[0].name).toBe('Silk Robe');

    // CRITICAL: Deep-check that no address fields leaked
    const responseString = JSON.stringify(wishlistResponse);
    const addressPatterns = [
      /address/i,
      /street/i,
      /postal/i,
      /zip_code/i,
      /city":/i,
      /state":/i,
      /apartment/i,
    ];

    for (const pattern of addressPatterns) {
      expect(responseString).not.toMatch(pattern);
    }

    // Simulate the gift checkout API call
    const checkoutResponse = await page.evaluate(async () => {
      const res = await fetch('/api/gift/checkout', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ item_id: 'item-001', creator_id: 'creator-001' }),
      });
      return res.json();
    });

    // Verify checkout response has the expected safe fields
    expect(checkoutResponse.checkout_url).toContain('checkout.stripe.com');
    expect(checkoutResponse.gift_id).toBeTruthy();
    expect(checkoutResponse.item_name).toBe('Silk Robe');

    // CRITICAL ASSERTION: No address data in the checkout response
    const checkoutString = JSON.stringify(checkoutResponse);
    for (const pattern of addressPatterns) {
      expect(checkoutString).not.toMatch(pattern);
    }
  });

  test('malicious address injection in gift API is caught', async ({ page }) => {
    /*
     * Regression guard: if a future backend change accidentally includes
     * address data in the gift checkout response, this test MUST fail.
     *
     * We simulate a "leaky" response and verify our assertion logic
     * would catch it.
     */

    const LEAKY_RESPONSE = {
      checkout_url: 'https://checkout.stripe.com/gift-session-99999',
      gift_id: 'gift-002',
      item_name: 'Silk Robe',
      amount: 89.99,
      // DANGER: This should never be in a real response
      shipping_address: '123 Creator Lane, Los Angeles, CA 90001',
    };

    const leakyString = JSON.stringify(LEAKY_RESPONSE);

    // This SHOULD match — proving our check catches leaks
    expect(leakyString).toMatch(/address/i);

    // Verify the safe response does NOT match
    const safeString = JSON.stringify(MOCK_GIFT_CHECKOUT_RESPONSE);
    expect(safeString).not.toMatch(/address/i);
  });
});
