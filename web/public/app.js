function token() { try { return localStorage.getItem('access'); } catch (e) { return null; } }
function setAuth(d) {
  localStorage.setItem('access', d.access);
  localStorage.setItem('refresh', d.refresh);
  localStorage.setItem('user', JSON.stringify(d.user));
}
function logout() { localStorage.clear(); location.href = '/login'; }

async function api(path, opts = {}) {
  const send = (withToken) => {
    const headers = Object.assign({ 'Content-Type': 'application/json' }, opts.headers || {});
    if (withToken && token()) headers.Authorization = 'Bearer ' + token();
    return fetch('/api' + path, Object.assign({}, opts, {
      headers, body: opts.body ? JSON.stringify(opts.body) : undefined }));
  };
  let r = await send(true);
  const publicGet = (!opts.method || opts.method === 'GET') && /^\/(movies|shows)/.test(path);

  if (r.status === 401 && publicGet) { localStorage.clear(); r = await send(false); }
  else if (r.status === 401) {
    localStorage.clear();
    location.href = '/login?next=' + encodeURIComponent(location.pathname + location.search);
    throw new Error('Please log in');
  }
  const ct = r.headers.get('content-type') || '';
  const data = ct.includes('json') ? await r.json() : await r.blob();
  if (!r.ok) throw new Error(data.error || data.detail || 'Request failed');
  return data;
}

const authLink = document.getElementById('authLink');
if (authLink) {
  if (token()) {
    const u = JSON.parse(localStorage.getItem('user') || '{}');
    if (u.name) {
      const hi = document.createElement('span');
      hi.textContent = 'Hi, ' + u.name.split(' ')[0];
      hi.style.cssText = 'margin-left:16px;color:#f1f1f7';
      authLink.before(hi);
    }
    authLink.textContent = 'Logout';
    authLink.onclick = (e) => { e.preventDefault(); logout(); };
  } else authLink.href = '/login';
}