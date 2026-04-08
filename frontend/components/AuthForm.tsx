import { useState } from 'react';
import { useAuth } from './AuthContext';

export default function AuthForm() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { login, signup } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      if (isLogin) {
        await login(email, password);
      } else {
        await signup(email, password);
      }
    } catch (error) {
      setError('Authentication failed. Check your email and password and try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="eyebrow">Prelegal Workspace</div>
        <h2>{isLogin ? 'Secure client access' : 'Create your workspace'}</h2>
        <p className="lede">
          Draft legal agreements with a guided assistant, structured templates, and saved document history.
        </p>
        <form onSubmit={handleSubmit} className="form-stack">
          <div>
            <label className="field-label">Email</label>
            <input
              className="field-input"
              type="email"
              placeholder="name@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="field-label">Password</label>
            <input
              className="field-input"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          {error ? <div className="status-pill">{error}</div> : null}
          <button type="submit" disabled={loading} className="primary-button">
            {loading ? 'Working...' : isLogin ? 'Sign In' : 'Create Account'}
          </button>
        </form>
        <button
          onClick={() => {
            setIsLogin(!isLogin);
            setError('');
          }}
          className="ghost-button"
          style={{ width: '100%', marginTop: '14px' }}
        >
          {isLogin ? 'Need an account? Create one' : 'Already have an account? Sign in'}
        </button>
      </div>
    </div>
  );
}
