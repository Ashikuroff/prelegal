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
      const response = await fetch('/api/documents');
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
      await fetch(`/api/documents/${id}`, { method: 'DELETE' });
      setDocuments(prev => prev.filter(doc => doc.id !== id));
    } catch (error) {
      console.error('Failed to delete document:', error);
    }
  };

  return (
    <>
      <button
        onClick={() => setShowModal(true)}
        style={{
          position: 'fixed',
          top: '20px',
          right: '20px',
          padding: '10px',
          backgroundColor: '#209dd7',
          color: 'white',
          border: 'none',
          cursor: 'pointer'
        }}
      >
        My Documents
      </button>
      {showModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          backgroundColor: 'rgba(0,0,0,0.5)',
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center'
        }}>
          <div style={{
            backgroundColor: 'white',
            padding: '20px',
            borderRadius: '10px',
            maxWidth: '600px',
            width: '90%'
          }}>
            <h2>My Documents</h2>
            {documents.length === 0 ? (
              <p>No documents saved yet.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0 }}>
                {documents.map(doc => (
                  <li key={doc.id} style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '10px',
                    borderBottom: '1px solid #ccc'
                  }}>
                    <div>
                      <strong>{doc.title}</strong> - {doc.document_type}
                      <br />
                      <small>{new Date(doc.created_at).toLocaleDateString()}</small>
                    </div>
                    <div>
                      <button
                        onClick={() => onLoadDocument(doc)}
                        style={{
                          marginRight: '10px',
                          padding: '5px 10px',
                          backgroundColor: '#209dd7',
                          color: 'white',
                          border: 'none',
                          cursor: 'pointer'
                        }}
                      >
                        Load
                      </button>
                      <button
                        onClick={() => deleteDocument(doc.id)}
                        style={{
                          padding: '5px 10px',
                          backgroundColor: '#ecad0a',
                          color: 'white',
                          border: 'none',
                          cursor: 'pointer'
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
            <button
              onClick={() => setShowModal(false)}
              style={{
                marginTop: '20px',
                padding: '10px 20px',
                backgroundColor: '#032147',
                color: 'white',
                border: 'none',
                cursor: 'pointer'
              }}
            >
              Close
            </button>
          </div>
        </div>
      )}
    </>
  );
}