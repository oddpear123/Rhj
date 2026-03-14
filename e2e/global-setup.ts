/**
 * global-setup.ts
 *
 * Runs once before the smoke suite. Seeds the database with:
 *   - A Fan account (testfan@rhj.com / password123)
 *   - At least one photo so the gallery isn't empty
 *
 * Prerequisites:
 *   - Backend running on :8000
 *   - Admin account is seeded automatically by init_db() on startup
 */

import { test, expect, request } from '@playwright/test';

const API = 'http://localhost:8000';

test('seed test data', async () => {
  const api = await request.newContext({ baseURL: API });

  // ── 1. Register the Fan account (idempotent — 400 if already exists) ──
  const registerRes = await api.post('/auth/register', {
    data: { email: 'testfan@rhj.com', password: 'password123' },
  });
  // Accept 200 (created) or 400 (already exists)
  expect([200, 400]).toContain(registerRes.status());

  // ── 2. Log in as admin so we can upload a seed photo ──
  const adminLogin = await api.post('/auth/login', {
    data: { email: 'admin@rhj.com', password: 'admin1234' },
  });
  expect(adminLogin.ok()).toBeTruthy();
  const { access_token } = await adminLogin.json();

  // ── 3. Upload a seed photo (skip if gallery already has content) ──
  const photosRes = await api.get('/photos');
  const existingPhotos = await photosRes.json();

  if (existingPhotos.length === 0) {
    // Create a tiny 1x1 red PNG to use as the seed photo
    const pngHeader = Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==',
      'base64',
    );

    const uploadRes = await api.post('/photos/admin/upload', {
      headers: { Authorization: `Bearer ${access_token}` },
      multipart: {
        title: 'Seed Photo',
        file: {
          name: 'seed.png',
          mimeType: 'image/png',
          buffer: pngHeader,
        },
      },
    });
    expect(uploadRes.ok()).toBeTruthy();
  }

  await api.dispose();
});
