import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import './Login.css';

const API_URL = 'http://127.0.0.1:8000';
const readings = [
  { label: 'HEALTH', value: 'Normal', color: '#139b78', path: 'M0 30h20l5-7 5 13 5-63 5 88 5-58 5 19h15l5-10 7 14h23l5-6 6 11 5-62 5 85 5-57 5 20h12l5-11 7 13h24l5-8 6 13 5-65 5 90 5-60 5 24h17l5-12 6 15h21l5-8 6 14 5-68 5 91 5-60 5 23' },
  { label: 'TEMP', value: '33.4 °C', color: '#e87e45', path: 'M0 16C35 23 50 21 78 17S110 8 150 10 174 8 200 9 235 20 270 20 300 13 330 12H360' },
  { label: 'HUMID', value: '51 %RH', color: '#219dbe', path: 'M0 19C35 20 48 16 77 16S103 17 133 13 161 11 187 13 222 12 248 15 288 20 317 18 344 18 360 17' },
  { label: 'VIBR', value: '2.1 mm/s', color: '#9665ec', path: 'M0 13l7 4 7-2 6-7 7 4 7-3 7 7 7-2 7 4 7-8 7 1 7 3 7-5 7 2 7 8 7-1 7-8 7 2 7-3 7 8 7 1 7-5 7 3 7-6 7 6 7-1 7 5 7-8 7 2 7-3 7 7 7 2 7-7 7 3 7-5 7 7 7-2 7 4 7-8 7 3 7-2 7 7 7-1 7-6 7 3 7-5 7 4 7-1 7 5 7-8 7 3 7-2 7 6 7-3' },
];

export default function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [help, setHelp] = useState(false);

  async function handleSubmit(event) {
    event.preventDefault();
    if (loading) return;
    setError('');
    if (!email.trim() || !password) {
      setError('Email and password are required. Enter both to continue.');
      return;
    }
    setLoading(true);
    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(response.status === 401
        ? 'Email or password is incorrect. Check your details and try again.'
        : (typeof data.detail === 'string' ? data.detail : 'Login failed. Please try again.'));
      sessionStorage.setItem('nexasense_token', data.access_token);
      navigate('/dashboard');
    } catch (err) {
      setError(err instanceof TypeError ? 'Unable to connect. Check your connection and try again.' : err.message || 'Unable to connect to the server.');
    } finally { setLoading(false); }
  }

  return (
    <main className="login-page">
      <section className="login-info" aria-labelledby="login-intro-title">
        <header className="login-info-header">
          <Link className="login-brand" to="/login" aria-label="NexaSense home">
            <span className="login-brand-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none"><path d="M4 12h4l2-6 4 12 2-6h4" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" /></svg></span>
            <span><strong>NexaSense</strong><small>Smart inspection for homes &amp; facilities</small></span>
          </Link>
          <span className="login-monitoring"><span aria-hidden="true" />Monitoring 12 machines</span>
        </header>
        <div className="login-intro">
          <p className="login-eyebrow">PREDICTIVE INSPECTION · V2026</p>
          <h1 id="login-intro-title">Know your<br />equipment’s<br />health <span>before</span> it<br />fails.</h1>
          <p className="login-description">Schedule robot inspections, watch sensor readings live and get clear alerts and reports for your air conditioners, panels, pumps and ventilation.</p>
        </div>
        <div className="login-readings" role="img" aria-label="Illustrative sensor readings, not live data: health normal, temperature 33.4 degrees Celsius, humidity 51 percent, vibration 2.1 millimeters per second.">
          {readings.map(reading => <div className={`login-reading ${reading.label === 'HEALTH' ? 'health-reading' : ''}`} key={reading.label} style={{ '--reading-color': reading.color }}>
            <span>{reading.label}</span><svg viewBox={reading.label === 'HEALTH' ? '0 -30 360 100' : '0 0 360 32'} preserveAspectRatio="none" aria-hidden="true"><path d={reading.path} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinejoin="round" /></svg><strong>{reading.value}</strong>
          </div>)}
        </div>
        <div className="login-features">
          <div><strong>Smart inspections</strong><span>Scheduled or on demand</span></div>
          <div><strong>Instant alerts</strong><span>When a rule is broken</span></div>
          <div><strong>Clear reports</strong><span>PDF with recommendations</span></div>
        </div>
        <footer className="login-info-footer">© 2026 NexaSense Technologies</footer>
      </section>
      <section className="login-form-section" aria-labelledby="login-title">
        <div className="login-card">
          <p className="login-heading-label">SECURE ACCESS</p>
          <h2 id="login-title">Welcome back</h2>
          <p className="login-subtitle">Log in to monitor your equipment.</p>
          <form onSubmit={handleSubmit} noValidate>
            {error && <div className="login-error" role="alert"><span aria-hidden="true">ⓘ</span><span>{error}</span></div>}
            <div className="login-field">
              <label htmlFor="login-email">Email</label>
              <input id="login-email" name="email" type="email" autoComplete="username" placeholder="you@example.com" value={email} onChange={event => setEmail(event.target.value)} disabled={loading} required />
            </div>
            <div className="login-field">
              <div className="login-password-label"><label htmlFor="login-password">Password</label><button className="login-forgot" type="button" onClick={() => setHelp(previous => !previous)} aria-expanded={help} aria-controls="login-password-help">Forgot password?</button></div>
              <div className="login-password-wrapper">
                <input id="login-password" name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" value={password} onChange={event => setPassword(event.target.value)} disabled={loading} required />
                <button type="button" className="login-show-password" onClick={() => setShowPassword(previous => !previous)} aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword}>
                  <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" stroke="currentColor" strokeWidth="1.6" /><circle cx="12" cy="12" r="2.5" stroke="currentColor" strokeWidth="1.6" />{showPassword && <path d="m4 4 16 16" stroke="currentColor" strokeWidth="1.6" />}</svg>
                </button>
              </div>
            </div>
            {help && <p className="login-help" id="login-password-help" role="status">Password reset is not available yet. Contact the NexaSense project team for help accessing your account.</p>}
            <p className="login-session-note">Your login lasts for this browser session.</p>
            <button type="submit" className="login-submit" disabled={loading}>{loading ? 'Logging in...' : 'Log in'}<span aria-hidden="true">→</span></button>
            <span className="login-sr-only" role="status">{loading ? 'Logging in. Please wait.' : ''}</span>
          </form>
          <p className="login-register-link">Don’t have an account? <Link to="/register">Create one</Link></p>
        </div>
      </section>
    </main>
  );
}
