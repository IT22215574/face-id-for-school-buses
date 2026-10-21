import React, { useEffect, useId, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';
import { createApiClient } from './api.js';
import { validateField, patchIdentity, photoType } from './validation.js';

const API = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? '/api' : '');
const emptyIdentity = { name: '', phone: '', email: '', nic: '', address: '', id_front: '', id_back: '' };
const emptyDriver = () => ({ ...emptyIdentity, password: '', license_front: '', bus_id: '', assistant: null });
const emptyBus = { plate_no: '', device_id: '', route_name: '' };
function validateForm(event) {
  const form = event.currentTarget;
  for (const input of form.querySelectorAll('input[data-field]')) {
    input.setCustomValidity(!input.required && !input.value ? '' : validateField(input.dataset.field, input.value));
  }
  if (!form.reportValidity()) { event.preventDefault(); event.stopPropagation(); }
}
function Field({ label, onChange, digitsOnly = false, ...props }) {
  const [error, setError] = useState('');
  const id = useId();
  function validate(input) {
    const message = props.required === false && !input.value ? '' : validateField(label, input.value);
    input.setCustomValidity(message);
    setError(message);
  }
  return <label className="field"><span>{label}</span><input required {...props} data-field={label}
    aria-invalid={!!error} aria-describedby={error ? id : undefined}
    onChange={e => { if (digitsOnly) e.target.value = e.target.value.replace(/[^0-9]/g, ''); validate(e.target); onChange?.(e); }}
    onBlur={e => validate(e.target)}
    onInvalid={e => validate(e.target)}/>{error && <small id={id} className="field-error">{error}</small>}</label>;
}
function Photo({ label, value, onChange, onPending }) {
  const [error, setError] = useState('');
  const [reading, setReading] = useState(false);
  const inputRef = useRef(null);
  const sequence = useRef(0);
  const id = useId();
  useEffect(() => { if (!value && inputRef.current && !reading) inputRef.current.value = ''; }, [value, reading]);
  useEffect(() => () => { sequence.current++; }, []);
  async function pick(event) {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;
    const selection = ++sequence.current;
    setError(''); setReading(true); onPending(1);
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error('Choose a photo no larger than 5 MB.');
      const bytes = new Uint8Array(await file.arrayBuffer());
      const type = photoType(bytes, file.size);
      const encoded = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result).split(',')[1]);
        reader.onerror = () => reject(new Error('Unable to read photo. Please retry.'));
        reader.readAsDataURL(file);
      });
      if (selection === sequence.current) onChange(`data:image/${type};base64,${encoded}`);
    } catch (e) {
      if (selection === sequence.current) { setError(e.message); input.value = ''; }
    } finally {
      onPending(-1);
      if (selection === sequence.current) { setReading(false); input.value = ''; }
    }
  }
  return <label className="photo"><span>{label}</span><small>JPEG or PNG · up to 5 MB</small><input ref={inputRef} type="file" accept="image/jpeg,image/png" required={!value} disabled={reading} aria-invalid={!!error} aria-describedby={id} onChange={pick}/><small id={id} aria-live="polite">{reading ? 'Reading photo…' : value ? 'Photo ready to save. Select a file to replace it.' : 'Select a photo.'}</small>{value && <img src={value} alt={label}/ >}{error && <span role="alert" className="error">{error}</span>}</label>;
}
function Identity({ value, onChange, onPending }) {
  const change = (key, data) => patchIdentity(onChange, key, data);
  return <><div className="grid"><Field label="Full name" minLength={2} maxLength={120} value={value.name} onChange={e => change('name', e.target.value)}/><Field label="Phone number" type="tel" inputMode="numeric" digitsOnly pattern="[0-9]{10}" minLength={10} maxLength={10} placeholder="0771234567" value={value.phone} onChange={e => change('phone', e.target.value)}/><Field label="Email address" type="email" maxLength={255} value={value.email} onChange={e => change('email', e.target.value)}/><div className="nic-fields"><Field label="National ID number" inputMode="numeric" digitsOnly pattern="[0-9]+" minLength={5} maxLength={29} value={value.nic.replace(/V$/, '')} onChange={e => { const digits = e.target.value; onChange(current => ({ ...current, nic: digits + (current.nic.endsWith('V') ? 'V' : '') })); }}/><label className="field"><span>ID suffix (optional)</span><select value={value.nic.endsWith('V') ? 'V' : ''} onChange={e => { const suffix = e.target.value; onChange(current => ({ ...current, nic: current.nic.replace(/V$/, '') + suffix })); }}><option value="">None</option><option value="V">V</option></select></label></div><Field label="Residential address" minLength={5} maxLength={500} value={value.address} onChange={e => change('address', e.target.value)}/></div><div className="grid"><Photo onPending={onPending} label="ID front photo" value={value.id_front} onChange={v => change('id_front', v)}/><Photo onPending={onPending} label="ID back photo" value={value.id_back} onChange={v => change('id_back', v)}/></div></>;
}
function App() {
  const pendingPhotos = useRef(0);
  const [photoCount, setPhotoCount] = useState(0);
  function trackPhotos(delta) { pendingPhotos.current += delta; setPhotoCount(pendingPhotos.current); }
  const api = useRef(null);
  if (!api.current) api.current = createApiClient(API, () => clearSession());
  const [user, setUser] = useState(null);
  const [tab, setTab] = useState('drivers');
  const [drivers, setDrivers] = useState([]);
  const [buses, setBuses] = useState([]);
  const [driver, setDriver] = useState(emptyDriver);
  const [bus, setBus] = useState(emptyBus);
  const [editId, setEditId] = useState(null);
  const [driverEditId, setDriverEditId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [search, setSearch] = useState('');
  const [detail, setDetail] = useState(null);
  function clearSession() { api.current.setSession(null); setUser(null); setDrivers([]); setBuses([]); setDetail(null); setDriver(emptyDriver()); setDriverEditId(null); setBus(emptyBus); setEditId(null); setNotice(''); }
  const request = (...args) => api.current.request(...args);
  async function load(auth) {
    setLoading(true);
    try { const [d, b] = await Promise.all([request('/admin/driver-registrations', {}, auth), request('/admin/buses', {}, auth)]); setDrivers(d); setBuses(b); }
    finally { setLoading(false); }
  }
  async function action(task) {
    setBusy(true); setError(''); setNotice('');
    try { await task(); } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  async function login(event) {
    event.preventDefault(); const data = new FormData(event.currentTarget);
    await action(async () => {
      const session = await request('/auth/login', { method: 'POST', body: JSON.stringify({ email: data.get('email'), password: data.get('password') }) }, '');
      const me = await request('/me', {}, session.access_token);
      if (me.role !== 'ADMIN') throw new Error('Sign in with an administrator account.');
      api.current.setSession(session); await load(); setUser(me);
    });
  }
  async function saveDriver(event) {
    event.preventDefault();
    if (pendingPhotos.current) { setError('Wait for photos to finish reading.'); return; }
    await action(async () => {
      if (!driver.id_front || !driver.id_back || !driver.license_front || (driver.assistant && (!driver.assistant.id_front || !driver.assistant.id_back))) throw new Error('Upload all required photos before saving the driver.');
      if (driver.assistant && ['nic', 'phone', 'email'].some(key => driver[key].trim().toLowerCase() === driver.assistant[key].trim().toLowerCase())) throw new Error('Assistant must have a different national ID, phone number and email.');
      if ((!driverEditId || driver.password) && (!/[A-Za-z]/.test(driver.password) || !/[0-9]/.test(driver.password) || new TextEncoder().encode(driver.password).length > 72)) throw new Error('Password must contain letters and numbers and be at most 72 bytes.');
      await request(`/admin/driver-registrations${driverEditId ? `/${driverEditId}` : ''}`, { method: driverEditId ? 'PUT' : 'POST', body: JSON.stringify({ ...driver, password: driver.password || undefined, bus_id: Number(driver.bus_id) }) });
      setDriver(emptyDriver()); setDriverEditId(null); setNotice(driverEditId ? 'Driver updated.' : 'Driver created and assigned to the bus. They can now sign in to the mobile app.');
      try { await load(); } catch { setError('Driver was saved, but the list could not refresh. Use Refresh.'); }
    });
  }
  async function editDriver(id) {
    await action(async () => {
      const data = await request(`/admin/driver-registrations/${id}`);
      const { id: ignoredId, license_no: ignoredLicense, ...values } = data;
      setDriver({ ...emptyDriver(), ...values, bus_id: String(data.bus_id || ''), password: '' });
      setDriverEditId(id);
      document.getElementById('driver-form')?.scrollIntoView({ behavior: 'smooth' });
    });
  }
  async function deleteRecord(kind, id, label) {
    if (!window.confirm(`Delete ${label}? This cannot be undone.${kind === 'driver-registrations' ? ' The driver login will also be removed.' : ''}`)) return;
    await action(async () => {
      await request(`/admin/${kind}/${id}`, { method: 'DELETE' });
      if (kind === 'buses') {
        setBuses(current => current.filter(item => item.id !== id));
        if (editId === id) { setEditId(null); setBus(emptyBus); }
      } else {
        setDrivers(current => current.filter(item => item.id !== id));
        if (driverEditId === id) { setDriverEditId(null); setDriver(emptyDriver()); }
      }
      setNotice('Deleted successfully.');
    });
  }
  async function saveBus(event) {
    event.preventDefault();
    await action(async () => {
      const saved = await request(`/admin/buses${editId ? `/${editId}` : ''}`, { method: editId ? 'PUT' : 'POST', body: JSON.stringify(bus) });
      setBuses(current => [saved, ...current.filter(item => item.id !== saved.id)]);
      setBus(emptyBus); setEditId(null); setNotice(editId ? 'Bus and route updated.' : 'Bus and route created. You can now assign a driver.');
      try { await load(); } catch { setError('Saved successfully, but the list could not refresh. Use Refresh.'); }
    });
  }
  useEffect(() => { function escape(e) { if (e.key === 'Escape') setDetail(null); } window.addEventListener('keydown', escape); return () => window.removeEventListener('keydown', escape); }, []);
  const messages = <div aria-live="polite">{error && <p role="alert" className="message error">{error}</p>}{notice && <p className="message success">{notice}</p>}</div>;
  if (!user) return <main className="login"><section className="login-story"><div className="brand">▰ <span>admin-web</span></div><span className="eyebrow">SCHOOL TRANSPORT MANAGEMENT</span><h1>A smoother start<br/>to every school day.</h1><p>Manage your drivers, buses and routes in one place.</p><div className="route-art"><i/> School <span>───────── ● ─────────</span> Home <i/></div></section><section className="login-panel"><form onSubmitCapture={validateForm} onSubmit={login}><span className="eyebrow">ADMINISTRATOR ACCESS</span><h2>Welcome back</h2><p>Sign in with your school bus admin account.</p>{messages}<Field label="Email address" name="email" type="email" autoComplete="username"/><Field label="Password" name="password" type="password" autoComplete="current-password"/><button disabled={busy}>{busy ? 'Signing in…' : 'Sign in →'}</button><small>Connected to your school bus backend.</small></form></section></main>;
  const available = buses.filter(b => !drivers.some(d => d.bus_id === b.id && d.status === 'ACTIVE'));
  const assignable = buses.filter(b => !drivers.some(d => d.id !== driverEditId && d.bus_id === b.id && d.status === 'ACTIVE'));
  const filtered = drivers.filter(d => [d.name,d.email,d.plate_no,d.route_name].some(v => String(v || '').toLowerCase().includes(search.toLowerCase())));
  return <div className="shell"><aside><div className="brand">▰ <span>admin-web</span></div><p className="nav-label">WORKSPACE</p><button className={tab === 'drivers' ? 'nav active' : 'nav'} onClick={() => setTab('drivers')}>♙ Drivers</button><button className={tab === 'routes' ? 'nav active' : 'nav'} onClick={() => setTab('routes')}>▱ Buses & routes</button><div className="sidebar-bottom"><strong>{user.name}</strong><small>Super admin</small><button className="nav" disabled={busy} onClick={() => action(async () => { try { await request('/auth/logout', { method: 'POST' }); } finally { clearSession(); } })}>Sign out</button></div></aside><main className="workspace"><header><div><span className="eyebrow">TRANSPORT OPERATIONS</span><h1>{tab === 'drivers' ? 'Drivers' : 'Buses & routes'}</h1><p>{tab === 'drivers' ? 'Give every journey a trusted driver.' : 'Organize the fleet. Connect every route.'}</p></div><button className="secondary" disabled={busy || loading} onClick={() => action(() => load())}>{loading ? 'Loading…' : '↻ Refresh'}</button></header><div className="stats"><article><span>Registered drivers</span><strong>{drivers.length}</strong></article><article><span>Buses & routes</span><strong>{buses.length}</strong></article><article><span>Ready for a driver</span><strong>{available.length}</strong></article></div>{messages}
  {tab === 'drivers' ? <><section className="card"><div className="section-heading"><div><h2>Driver directory</h2><p>Your team on the road.</p></div><input aria-label="Search drivers" placeholder="Search name, bus or route…" value={search} onChange={e => setSearch(e.target.value)}/></div><div className="table-scroll"><table><thead><tr><th>Driver</th><th>Contact</th><th>Bus / route</th><th>Status</th><th/></tr></thead><tbody>{filtered.map(d => <tr key={d.id}><td><strong>{d.name}</strong></td><td>{d.email}<small>{d.phone}</small></td><td>{d.plate_no || 'Unassigned'}<small>{d.route_name}</small></td><td><span className="badge">{d.status}</span></td><td><button className="secondary" disabled={busy} onClick={() => action(async () => setDetail(await request(`/admin/driver-registrations/${d.id}`)))}>View</button> <button className="secondary" disabled={busy || photoCount > 0} onClick={() => editDriver(d.id)}>Edit</button> <button className="secondary danger" disabled={busy} onClick={() => deleteRecord('driver-registrations', d.id, d.name)}>Delete</button></td></tr>)}</tbody></table>{!filtered.length && <p className="empty">{search ? 'No matching drivers.' : 'No drivers yet. Create your first driver below.'}</p>}</div></section>
  <form key={driverEditId || 'new-driver'} id="driver-form" className="card" onSubmitCapture={validateForm} onSubmit={saveDriver}><div className="section-heading"><div><span className="eyebrow">GROW YOUR TEAM</span><h2>{driverEditId ? 'Edit bus driver' : 'Create bus driver'}</h2><p>Create a mobile login and assign a bus in one step.</p></div></div><fieldset disabled={busy}><h3>01 · Driver details</h3><Identity value={driver} onChange={setDriver} onPending={trackPhotos}/><div className="grid"><Photo onPending={trackPhotos} label="Driving licence front photo" value={driver.license_front} onChange={v => setDriver(current => ({ ...current, license_front: v }))}/><Field label="Login password" required={!driverEditId} placeholder={driverEditId ? 'Leave blank to keep current password' : ''} type="password" autoComplete="new-password" minLength={8} maxLength={72} value={driver.password} onChange={e => setDriver(current => ({ ...current, password: e.target.value }))}/></div><h3>02 · Bus assignment</h3><label className="field"><span>Bus and route</span><select required value={driver.bus_id} onChange={e => setDriver(current => ({ ...current, bus_id: e.target.value }))}><option value="">Select an available bus</option>{buses.map(b => <option key={b.id} value={b.id} disabled={!assignable.some(a => a.id === b.id)}>{b.plate_no} — {b.route_name}{assignable.some(a => a.id === b.id) ? '' : ' (driver already assigned)'}</option>)}</select></label>{!assignable.length && <p className="hint">{buses.length ? 'All buses already have an active driver. Add another bus and route to register a new driver.' : 'No buses registered yet. Add a bus and route in the Buses & routes tab.'}</p>}<label className="check"><input type="checkbox" checked={!!driver.assistant} onChange={e => setDriver(current => ({ ...current, assistant: e.target.checked ? { ...emptyIdentity } : null }))}/> Driver has an assistant</label>{driver.assistant && <><h3>03 · Assistant details</h3><Identity value={driver.assistant} onPending={trackPhotos} onChange={update => setDriver(current => ({ ...current, assistant: current.assistant ? update(current.assistant) : null }))}/></>}<div className="form-footer"><small>The driver will sign in with the email and password above.</small><button disabled={!assignable.length || photoCount > 0}>{photoCount > 0 ? 'Reading photos…' : busy ? 'Saving…' : driverEditId ? 'Save driver changes' : 'Create driver & assign bus →'}</button>{driverEditId && <button type="button" className="secondary" disabled={busy || photoCount > 0} onClick={() => { setDriverEditId(null); setDriver(emptyDriver()); }}>Cancel editing</button>}</div></fieldset></form></> : <div className="route-layout"><section className="card"><h2>{editId ? 'Edit bus & route' : 'Add bus & route'}</h2><p>Each bus has a named route and device identifier.</p><form onSubmitCapture={validateForm} onSubmit={saveBus}><fieldset disabled={busy}><Field label="Bus plate number" minLength={2} maxLength={32} value={bus.plate_no} onChange={e => setBus({ ...bus, plate_no: e.target.value })}/><Field label="Device identifier" minLength={2} maxLength={64} value={bus.device_id} onChange={e => setBus({ ...bus, device_id: e.target.value })}/><Field label="Route name" minLength={2} maxLength={120} placeholder="e.g. Nugegoda → School" value={bus.route_name} onChange={e => setBus({ ...bus, route_name: e.target.value })}/><button>{busy ? 'Saving…' : editId ? 'Save changes' : 'Create bus & route →'}</button>{editId && <button type="button" className="secondary" onClick={() => { setEditId(null); setBus(emptyBus); }}>Cancel editing</button>}</fieldset></form></section><section className="card"><h2>Saved buses & routes</h2><p>{buses.length} buses and routes</p>{buses.map(b => <article className="bus-row" key={b.id}><div><strong>{b.plate_no}</strong><p>{b.route_name}</p><small>Device: {b.device_id}</small></div><button className="secondary" disabled={busy} onClick={() => { setEditId(b.id); setBus({ plate_no: b.plate_no, device_id: b.device_id, route_name: b.route_name }); }}>Edit</button><button className="secondary danger" disabled={busy} onClick={() => deleteRecord('buses', b.id, `${b.plate_no} / ${b.route_name}`)}>Delete</button></article>)}{!buses.length && <p className="empty">Add your first bus and route to get started.</p>}</section></div>}
  </main>{detail && <div className="modal-backdrop" onClick={() => setDetail(null)}><section role="dialog" aria-modal="true" aria-label="Driver registration" className="modal card" onClick={e => e.stopPropagation()}><button className="secondary close" autoFocus onClick={() => setDetail(null)}>Close ✕</button><h2>Driver registration</h2>{[detail, detail.assistant].filter(Boolean).map((person,i) => <section key={i}><h3>{i ? 'Assistant' : 'Driver'}</h3><dl>{['name','phone','email','nic','address'].map(k => <React.Fragment key={k}><dt>{k === 'nic' ? 'National ID' : k}</dt><dd>{person[k] || '—'}</dd></React.Fragment>)}</dl><div className="grid">{['id_front','id_back','license_front'].filter(k => person[k]).map(k => <div key={k}><p>{k === 'license_front' ? 'Driving licence front' : k === 'id_front' ? 'ID front' : 'ID back'}</p><img className="document" alt={k.replaceAll('_',' ')} src={person[k]}/></div>)}</div></section>)}</section></div>}</div>;
}
createRoot(document.getElementById('root')).render(<App/>);
