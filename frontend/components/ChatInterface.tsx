import { useState, useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';

interface Message {
  id: string;
  text: string;
  sender: 'user' | 'ai';
}

interface Field {
  name: string;
  label: string;
  type: string;
  required: boolean;
}

interface DocumentType {
  type: string;
  fields: Field[];
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [documentType, setDocumentType] = useState<DocumentType | null>(null);
  const [fields, setFields] = useState<Record<string, any>>({});
  const [catalog, setCatalog] = useState<DocumentType[]>([]);
  const [savedDocId, setSavedDocId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();

  useEffect(() => {
    fetch('/api/chat/greeting')
      .then(res => res.json())
      .then(data => {
        setMessages([{ id: '1', text: data.greeting, sender: 'ai' }]);
      });

    fetch('/catalog.json')
      .then(res => res.json())
      .then(data => setCatalog(data.documents));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: input,
      sender: 'user'
    };
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input }),
      });
      const data = await response.json();

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: data.response,
        sender: 'ai'
      };
      setMessages(prev => [...prev, aiMessage]);

      if (data.fields) {
        setFields(prev => ({ ...prev, ...data.fields }));
      }

      // Detect document type
      const detectedType = catalog.find(doc =>
        input.toLowerCase().includes(doc.type.toLowerCase().split(' ')[0])
      );
      if (detectedType) {
        setDocumentType(detectedType);
      }
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const allRequiredFieldsFilled = documentType &&
    documentType.fields.every(field => field.required && fields[field.name]);

  const downloadPDF = async () => {
    // Save document first if not saved
    if (!savedDocId) {
      try {
        const response = await fetch('/api/documents', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: `${documentType?.type} - ${new Date().toLocaleDateString()}`,
            document_type: documentType?.type,
            fields
          }),
        });
        const doc = await response.json();
        setSavedDocId(doc.id);
      } catch (error) {
        alert('Failed to save document');
        return;
      }
    }

    // Download PDF
    const link = document.createElement('a');
    link.href = `/api/documents/${savedDocId}/pdf`;
    link.download = `${documentType?.type || 'document'}.pdf`;
    link.click();
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
          {messages.map(message => (
            <div key={message.id} style={{
              marginBottom: '10px',
              textAlign: message.sender === 'user' ? 'right' : 'left'
            }}>
              <div style={{
                display: 'inline-block',
                padding: '10px',
                backgroundColor: message.sender === 'user' ? '#209dd7' : '#f0f0f0',
                color: message.sender === 'user' ? 'white' : 'black',
                borderRadius: '10px',
                maxWidth: '70%'
              }}>
                {message.text}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div style={{ padding: '20px', borderTop: '1px solid #ccc' }}>
          <div style={{ display: 'flex' }}>
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message..."
              disabled={loading}
              style={{ flex: 1, padding: '10px', marginRight: '10px' }}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              style={{
                padding: '10px 20px',
                backgroundColor: '#753991',
                color: 'white',
                border: 'none',
                cursor: 'pointer'
              }}
            >
              Send
            </button>
          </div>
        </div>
      </div>
      <div style={{ width: '400px', borderLeft: '1px solid #ccc', padding: '20px' }}>
        <h3>Document Preview</h3>
        {documentType ? (
          <div>
            <h4>{documentType.type}</h4>
            {documentType.fields.map(field => (
              <div key={field.name} style={{ marginBottom: '10px' }}>
                <label>{field.label}:</label>
                <input
                  type={field.type === 'textarea' ? 'text' : field.type}
                  value={fields[field.name] || ''}
                  onChange={(e) => setFields(prev => ({ ...prev, [field.name]: e.target.value }))}
                  style={{ width: '100%', padding: '5px' }}
                />
              </div>
            ))}
            {allRequiredFieldsFilled && (
              <button
                onClick={downloadPDF}
                style={{
                  width: '100%',
                  padding: '10px',
                  backgroundColor: '#753991',
                  color: 'white',
                  border: 'none',
                  cursor: 'pointer',
                  marginTop: '10px'
                }}
              >
                Download PDF
              </button>
            )}
          </div>
        ) : (
          <p>Select a document type to preview</p>
        )}
      </div>
    </div>
  );
}