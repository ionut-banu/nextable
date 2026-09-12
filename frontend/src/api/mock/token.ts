/**
 * The guest's only credential, so it comes from the platform CSPRNG — never
 * Math.random, never derived from the id, the name, or the phone (spec 10).
 */
export function newToken(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  let binary = '';
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
