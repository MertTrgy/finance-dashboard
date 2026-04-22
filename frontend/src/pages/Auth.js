import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

export default function Dashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="dashboard">
      <header className="dash-header">
        <span className="dash-logo">Finance</span>
        <div className="dash-user">
          <span>Hi, {user?.username}</span>
          <button onClick={handleLogout} className="logout-btn">Sign out</button>
        </div>
      </header>

      <main className="dash-main">
        <div className="dash-welcome">
          <h1>Your dashboard</h1>
          <p>You're in! Transactions and charts coming next.</p>
        </div>
      </main>
    </div>
  );
}