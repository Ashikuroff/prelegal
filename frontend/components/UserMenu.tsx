import { useState } from 'react';
import { useAuth } from './AuthContext';

export default function UserMenu() {
  const [showMenu, setShowMenu] = useState(false);
  const { user, logout } = useAuth();

  if (!user) return null;

  return (
    <div style={{ position: 'relative' }}>
      <button
        onClick={() => setShowMenu(!showMenu)}
        style={{
          position: 'fixed',
          top: '20px',
          left: '20px',
          padding: '10px',
          backgroundColor: '#032147',
          color: 'white',
          border: 'none',
          cursor: 'pointer'
        }}
      >
        {user.email}
      </button>
      {showMenu && (
        <div style={{
          position: 'absolute',
          top: '50px',
          left: '20px',
          backgroundColor: 'white',
          border: '1px solid #ccc',
          borderRadius: '5px',
          boxShadow: '0 2px 10px rgba(0,0,0,0.1)'
        }}>
          <button
            onClick={logout}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: 'transparent',
              border: 'none',
              cursor: 'pointer',
              textAlign: 'left'
            }}
          >
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
}