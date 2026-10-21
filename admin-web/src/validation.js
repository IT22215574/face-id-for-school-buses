export function validateField(label, value) {
  const text = String(value ?? '').trim();
  if (!text) return `${label} is required.`;
  const limits = {
    'Full name': [2, 120], 'Phone number': [10, 10], 'Email address': [3, 255],
    'National ID number': [5, 30], 'Residential address': [5, 500],
    'Bus plate number': [2, 32], 'Device identifier': [2, 64], 'Route name': [2, 120],
  };
  if (label === 'Phone number' && !/^[0-9]{10}$/.test(text)) return 'Enter exactly 10 digits (e.g. 0771234567).';
  if (label === 'Email address' && !/^[^\s@]+@[^\s@.]+(?:\.[^\s@.]+)+$/.test(text)) return 'Enter a valid email address (e.g. name@example.com).';
  if (label === 'Full name' && !/\p{L}/u.test(text)) return 'Enter a name containing letters.';
  if (label === 'National ID number' && !/^[0-9]+V?$/.test(text)) return 'Enter numbers only and select V from the suffix dropdown if needed.';
  if (label === 'Login password' && (value.length < 8 || new TextEncoder().encode(value).length > 72 || !/[A-Za-z]/.test(value) || !/[0-9]/.test(value))) return 'Use at least 8 characters with letters and numbers, up to 72 bytes.';
  const range = limits[label];
  if (range && (text.length < range[0] || text.length > range[1])) return `Enter ${range[0]}–${range[1]} characters for ${label.toLowerCase()}.`;
  return '';
}

export function patchIdentity(setValue, key, value) {
  setValue(current => ({ ...current, [key]: value }));
}

export function photoType(bytes, size) {
  if (size > 5 * 1024 * 1024) throw new Error('Choose a photo no larger than 5 MB.');
  if ([137,80,78,71,13,10,26,10].every((b,i) => bytes[i] === b)) return 'png';
  if (bytes[0] === 255 && bytes[1] === 216 && bytes[2] === 255) return 'jpeg';
  throw new Error('Choose a JPEG or PNG photo.');
}
