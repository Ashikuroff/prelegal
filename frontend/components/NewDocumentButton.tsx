import { useAuth } from './AuthContext';

export default function NewDocumentButton({ onNewDocument }: { onNewDocument: () => void }) {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <button onClick={onNewDocument} className="secondary-button">
      New Document
    </button>
  );
}
