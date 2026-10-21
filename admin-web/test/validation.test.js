import test from 'node:test';
import assert from 'node:assert/strict';
import { validateField, patchIdentity, photoType } from '../src/validation.js';

test('phone and email validation', () => {
  for (const phone of ['0771234567', '+94771234567']) assert.equal(validateField('Phone number', phone), '');
  for (const phone of ['abc1234567', '123', '077 1234567', '+1234567890123456']) assert.ok(validateField('Phone number', phone));
  assert.equal(validateField('Email address', 'driver@example.com'), '');
  for (const email of ['driver', 'driver@example', '@example.com', 'x y@example.com', 'x@example..com']) assert.ok(validateField('Email address', email));
});

test('required fields, trimmed lengths, identity and password rules', () => {
  for (const label of ['Full name', 'Phone number', 'Email address', 'National ID number', 'Residential address', 'Login password', 'Bus plate number', 'Device identifier', 'Route name']) assert.ok(validateField(label, '   '));
  assert.ok(validateField('Residential address', '   a   '));
  assert.ok(validateField('Full name', '12345'));
  assert.equal(validateField('Full name', 'අමල් පෙරේරා'), '');
  assert.equal(validateField('National ID number', '123456789V'), '');
  assert.ok(validateField('National ID number', '1234!6789'));
  for (const password of ['12345678', 'password', 'abc123', 'a1' + 'é'.repeat(36)]) assert.ok(validateField('Login password', password));
  assert.equal(validateField('Login password', 'password123'), '');
  assert.ok(validateField('Route name', 'a'.repeat(121)));
});

test('async photo completion preserves edits and independently selected photos', () => {
  let state = { name: 'Before', id_front: '', id_back: '' };
  const setState = update => { state = update(state); };
  const finishFront = () => patchIdentity(setState, 'id_front', 'front-data');
  patchIdentity(setState, 'name', 'After');
  patchIdentity(setState, 'id_back', 'back-data');
  finishFront();
  assert.deepEqual(state, { name: 'After', id_front: 'front-data', id_back: 'back-data' });
});

test('photo type validation handles JPEG, PNG, invalid files and size limit', () => {
  assert.equal(photoType(new Uint8Array([255,216,255]), 3), 'jpeg');
  assert.equal(photoType(new Uint8Array([137,80,78,71,13,10,26,10]), 2 * 1024 * 1024), 'png');
  assert.throws(() => photoType(new Uint8Array([255,216,255]), 2 * 1024 * 1024 + 1), /2 MB/);
  assert.throws(() => photoType(new Uint8Array([137,80,78,71]), 4), /JPEG or PNG/);
  assert.throws(() => photoType(new Uint8Array(), 0), /JPEG or PNG/);
});
