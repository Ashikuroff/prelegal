import { useState } from 'react';
import { useAuth } from './AuthContext';

export default function NewDocumentButton({ onNewDocument }: { onNewDocument: () => void }) {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <button
      onClick={onNewDocument}
      style={{
        position: 'fixed',
        top: '20px',
        right: '120px',
        padding: '10px',
        backgroundColor: '#ecad0a',
        color: 'white',
        border: 'none',
        cursor: 'pointer'
      }}
    >
      New Document
    </button>
  );
}