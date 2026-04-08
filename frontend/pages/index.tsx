import { useState } from 'react';
import AuthForm from '../components/AuthForm';
import ChatInterface from '../components/ChatInterface';
import MyDocuments from '../components/MyDocuments';
import UserMenu from '../components/UserMenu';
import NewDocumentButton from '../components/NewDocumentButton';
import { AuthProvider, useAuth } from '../components/AuthContext';

interface SavedDocument {
  id: number;
  title: string;
  document_type: string;
  fields: Record<string, string>;
  created_at: string;
}

function AppContent() {
  const [loadedDocument, setLoadedDocument] = useState<SavedDocument | null>(null);
  const [resetCounter, setResetCounter] = useState(0);
  const { user, loading } = useAuth();

  if (loading) return <div className="loading-screen">Loading workspace...</div>;

  if (!user) return <AuthForm />;

  return (
    <div className="page-shell">
      <div className="toolbar">
        <div className="brand-block">
          <div className="brand-mark">P</div>
          <div className="brand-copy">
            <h1>Prelegal</h1>
            <p>Draft agreements with structured guidance and saved client workspaces.</p>
          </div>
        </div>
        <div className="toolbar-actions">
          <NewDocumentButton
            onNewDocument={() => {
              setLoadedDocument(null);
              setResetCounter((value) => value + 1);
            }}
          />
          <MyDocuments
            onLoadDocument={(doc) => {
              setLoadedDocument(doc);
              setResetCounter((value) => value + 1);
            }}
          />
          <UserMenu />
        </div>
      </div>
      <ChatInterface loadedDocument={loadedDocument} resetCounter={resetCounter} />
    </div>
  );
}

export default function Home() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
