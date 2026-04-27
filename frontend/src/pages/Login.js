import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Auth.css';

export default function Login() {
  const { login }   = useAuth();
  const navigate    = useNavigate();
  const [form, setForm]       = useState({ username: '', password: '' });
  const [error, setError]     = useState('');
  const [loading, setLoading] = useState(false);

  const handleChange = (e) =>
    setForm((f) => ({ ...f, [e.target.name]: e.target.value }));

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form.username, form.password);
      navigate('/');
    } catch (err) {
      setError(
        err.response?.data?.detail ||
        err.response?.data?.non_field_errors?.[0] ||
        'Incorrect username or password.'
      );
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
            Your money,<br /><em>clearly.</em>
          </h2>
          <ul className="auth-panel-features">
            <li><span className="feat-dot" />Track income and expenses</li>
            <li><span className="feat-dot" />Set monthly budget limits</li>
            <li><span className="feat-dot" />Visualise spending by category</li>
            <li><span className="feat-dot" />Export your data any time</li>
          </ul>
        </div>

        <p className="auth-panel-footer">Personal finance dashboard</p>
      </div>

      {/* ── Right form ── */}
      <div className="auth-form-side">
        <div className="auth-card">
          <p className="auth-eyebrow">Welcome back</p>
          <h1 className="auth-title">Sign in</h1>
          <p className="auth-sub">Enter your credentials to continue</p>

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
              <label htmlFor="password">Password</label>
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                value={form.password}
                onChange={handleChange}
                required
              />
            </div>
            <button type="submit" className="auth-btn" disabled={loading}>
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <div className="auth-divider"><span>or</span></div>

          <p className="auth-switch">
            No account? <Link to="/register">Create one</Link>
          </p>
        </div>
      </div>

    </div>
  );
}