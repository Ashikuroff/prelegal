import { useState } from 'react';
import { useAuth } from './AuthContext';

export default function UserMenu() {
  const [showMenu, setShowMenu] = useState(false);
  const { user, logout } = useAuth();

  if (!user) return null;

  const initials = user.email.slice(0, 2).toUpperCase();

  return (
    <div className="user-chip">
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="user-trigger"
      >
        <span className="user-avatar">{initials}</span>
        <span>{user.email}</span>
      </button>
      {showMenu && (
        <div className="popover">
          <button onClick={logout} className="ghost-button" style={{ width: '100%', textAlign: 'left' }}>
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}
