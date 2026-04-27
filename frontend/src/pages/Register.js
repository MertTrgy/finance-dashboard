import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

export default function Register() {
  const { register } = useAuth();
  const navigate     = useNavigate();
  const [form, setForm]       = useState({ username: '', email: '', password: '' });
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await register(form.username, form.email, form.password);
      navigate('/');
    } catch (err) {
      const data = err.response?.data;
      if (data) {
        const first = Object.values(data)[0];
        setError(Array.isArray(first) ? first[0] : first);
      } else {
        setError('Registration failed. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page">

      {/* ── Left panel ── */}
      <div className="auth-panel">
        <span className="auth-panel-logo">Finance</span>

        <div className="auth-panel-body">
          <h2 className="auth-panel-heading">
            Start knowing<br /><em>where it goes.</em>
          </h2>
          <ul className="auth-panel-features">
            <li><span className="feat-dot" />Free to use, no card needed</li>
            <li><span className="feat-dot" />Your data stays private</li>
            <li><span className="feat-dot" />Set up in under a minute</li>
            <li><span className="feat-dot" />Export everything as CSV</li>
          </ul>
        </div>

        <p className="auth-panel-footer">Personal finance dashboard</p>
      </div>

      {/* ── Right form ── */}
      <div className="auth-form-side">
        <div className="auth-card">
          <p className="auth-eyebrow">Get started</p>
          <h1 className="auth-title">Create account</h1>
          <p className="auth-sub">Takes less than a minute</p>

          {error && <div className="auth-error">{error}</div>}

          <form onSubmit={handleSubmit} className="auth-form">
            <div className="field">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                name="username"
                type="text"
                autoComplete="username"
                autoFocus
                value={form.username}
                onChange={handleChange}
                required
              />
            </div>
            <div className="field">
              <label htmlFor="email">Email <span style={{ color: '#bbb', fontWeight: 400 }}>(optional)</span></label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={form.email}
                onChange={handleChange}
              />
            </div>
            <div className="field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="new-password"
                placeholder="Min. 8 characters"
                value={form.password}
                onChange={handleChange}
                required
                minLength={8}
              />
            </div>
            <button type="submit" className="auth-btn" disabled={loading}>
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <div className="auth-divider"><span>or</span></div>

          <p className="auth-switch">
            Already have an account? <Link to="/login">Sign in</Link>
          </p>
        </div>
      </div>

    </div>
  );
}