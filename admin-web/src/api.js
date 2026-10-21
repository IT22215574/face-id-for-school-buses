export function createApiClient(base, onExpired, fetcher = fetch) {
  let session = null;
  let refreshing = null;
  async function send(path, options, access) {
    return fetcher(`${base}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(access ? { Authorization: `Bearer ${access}` } : {}), ...options.headers } });
  }
  async function renew() {
    if (!refreshing) {
      const previous = session;
      refreshing = (async () => {
        const response = await send('/auth/refresh', { method: 'POST', body: JSON.stringify({ refresh_token: previous.refresh_token }) });
        if (!response.ok) throw new Error('Your session expired. Please sign in again.');
        const next = await response.json();
        if (session !== previous) throw new Error('Session changed. Please retry.');
        session = next;
      })().finally(() => { refreshing = null; });
    }
    return refreshing;
  }
  return {
    setSession(value) { session = value; },
    async request(path, options = {}, explicitAccess) {
      const access = explicitAccess ?? session?.access_token;
      let response;
      try {
        response = await send(path, options, access);
        if (response.status === 401 && explicitAccess === undefined && session?.refresh_token) {
          // Parallel list requests share one refresh, including late 401 responses.
          if (access === session.access_token) await renew();
          response = await send(path, options, session?.access_token);
        }
      } catch (error) {
        if (error.message === 'Your session expired. Please sign in again.') { session = null; onExpired(); throw error; }
        throw new Error('Cannot connect to the backend. Check that the API is running.');
      }
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        if (response.status === 401 && explicitAccess === undefined && access) { session = null; onExpired(); throw new Error('Your session expired. Please sign in again.'); }
        throw new Error(Array.isArray(data.detail) ? data.detail.map(e => `${e.loc.slice(1).join('.')}: ${e.msg}`).join('\n') : data.detail || `Request failed (${response.status}).`);
      }
      return data;
    }
  };
}
