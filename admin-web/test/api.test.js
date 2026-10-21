import test from 'node:test';
import assert from 'node:assert/strict';
import { createApiClient } from '../src/api.js';
const response = (status, value) => ({ status, ok: status < 400, json: async () => value });
test('parallel unauthorized list requests share refresh and retry with new token', async () => {
  let refreshes = 0;
  const client = createApiClient('', () => assert.fail('unexpected expiry'), async (path, options) => {
    if (path === '/auth/refresh') { refreshes++; await new Promise(resolve => setTimeout(resolve, 5)); return response(200, {access_token:'new',refresh_token:'next'}); }
    return options.headers.Authorization === 'Bearer new' ? response(200, [{id:1}]) : response(401, {});
  });
  client.setSession({access_token:'old',refresh_token:'refresh'});
  const lists = await Promise.all([client.request('/admin/buses'), client.request('/admin/driver-registrations')]);
  assert.deepEqual(lists, [[{id:1}],[{id:1}]]);
  assert.equal(refreshes, 1);
});
test('rejected refresh expires session without retry loop', async () => {
  let expired = 0;
  const client = createApiClient('', () => expired++, async () => response(401, {}));
  client.setSession({access_token:'old',refresh_token:'refresh'});
  await assert.rejects(client.request('/admin/buses'), /session expired/);
  assert.equal(expired, 1);
});
test('login errors do not trigger session renewal', async () => {
  let calls = 0;
  const client = createApiClient('', () => assert.fail(), async () => { calls++; return response(401, {detail:'Invalid email or password'}); });
  await assert.rejects(client.request('/auth/login', {method:'POST'}, ''), /Invalid email or password/);
  assert.equal(calls, 1);
});
