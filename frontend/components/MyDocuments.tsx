import { useState, useEffect } from 'react';
import { useAuth } from './AuthContext';

interface Document {
  id: number;
  title: string;
  document_type: string;
  fields: Record<string, any>;
  created_at: string;
}

export default function MyDocuments({ onLoadDocument }: { onLoadDocument: (doc: Document) => void }) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [showModal, setShowModal] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      fetchDocuments();
    }
  }, [user]);

  const fetchDocuments = async () => {
    try {
      const response = await fetch('/api/documents', { credentials: 'include' });
      if (response.ok) {
        const data = await response.json();
        setDocuments(data);
      }
    } catch (error) {
      console.error('Failed to fetch documents:', error);
    }
  };

  const deleteDocument = async (id: number) => {
    try {
      await fetch(`/api/documents/${id}`, { method: 'DELETE', credentials: 'include' });
      setDocuments(prev => prev.filter(doc => doc.id !== id));
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  return (
    <>
      <button onClick={() => setShowModal(true)} className="ghost-button">
        My Documents
      </button>
      {showModal && (
        <div className="modal-backdrop">
          <div className="modal-card">
            <div className="modal-header">
              <h2 style={{ margin: 0 }}>My Documents</h2>
              <p className="helper-text" style={{ margin: '6px 0 0' }}>
                Reload previous drafts and continue working from the latest saved state.
              </p>
            </div>
            <div className="modal-content">
              {documents.length === 0 ? (
                <p className="helper-text">No saved documents yet.</p>
              ) : (
                <div className="document-list">
                  {documents.map(doc => (
                    <div key={doc.id} className="document-card">
                      <div className="document-meta">
                        <strong>{doc.title}</strong>
                        <span>{doc.document_type}</span>
                        <br />
                        <small>{new Date(doc.created_at).toLocaleString()}</small>
                      </div>
                      <div className="document-actions">
                        <button
                          onClick={() => {
                            onLoadDocument(doc);
                            setShowModal(false);
                          }}
                          className="secondary-button"
                        >
                          Load
                        </button>
                      <button
                        onClick={() => deleteDocument(doc.id)}
                        className="danger-button"
                      >
                        Delete
                      </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="modal-footer">
              <button onClick={() => setShowModal(false)} className="ghost-button">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
