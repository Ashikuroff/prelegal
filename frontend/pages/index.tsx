import { useState } from 'react';
import AuthForm from '../components/AuthForm';
import ChatInterface from '../components/ChatInterface';
import MyDocuments from '../components/MyDocuments';
import UserMenu from '../components/UserMenu';
import NewDocumentButton from '../components/NewDocumentButton';
import { AuthProvider, useAuth } from '../components/AuthContext';

function AppContent() {
  const [currentView, setCurrentView] = useState<'auth' | 'chat'>('auth');
  const { user, loading } = useAuth();

  if (loading) return <div>Loading...</div>;

  if (!user) return <AuthForm />;

  return (
    <div>
      <UserMenu />
      <NewDocumentButton onNewDocument={() => setCurrentView('chat')} />
      <MyDocuments onLoadDocument={(doc) => console.log('Load document:', doc)} />
      <ChatInterface />
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