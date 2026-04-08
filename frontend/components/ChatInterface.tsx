import { useEffect, useRef, useState } from 'react';

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

interface SavedDocument {
  id: number;
  title: string;
  document_type: string;
  fields: Record<string, string>;
  created_at: string;
}

interface ChatResponse {
  response: string;
  fields: Record<string, string>;
  document_type: string | null;
  complete: boolean;
}

export default function ChatInterface({
  loadedDocument,
  resetCounter,
}: {
  loadedDocument: SavedDocument | null;
  resetCounter: number;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [documentType, setDocumentType] = useState<DocumentType | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [catalog, setCatalog] = useState<DocumentType[]>([]);
  const [savedDocId, setSavedDocId] = useState<number | null>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetch('/catalog.json')
      .then((res) => res.json())
      .then((data) => setCatalog(data.documents));
  }, []);

  useEffect(() => {
    fetch('/api/chat/greeting', { credentials: 'include' })
      .then((res) => res.json())
      .then((data) => {
        setMessages([{ id: 'greeting', text: data.greeting, sender: 'ai' }]);
      });
  }, [resetCounter]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, [messages, loading]);

  useEffect(() => {
    if (!loadedDocument || catalog.length === 0) {
      return;
    }

    const matchedType = catalog.find((doc) => doc.type === loadedDocument.document_type) || null;
    setDocumentType(matchedType);
    setFields(loadedDocument.fields || {});
    setSavedDocId(loadedDocument.id);
    setStatusMessage(`Loaded "${loadedDocument.title}".`);
    setMessages([
      {
        id: `loaded-${loadedDocument.id}`,
        text: `Loaded saved ${loadedDocument.document_type}. You can continue editing and download a fresh PDF when ready.`,
        sender: 'ai',
      },
    ]);
  }, [loadedDocument, catalog, resetCounter]);

  useEffect(() => {
    if (loadedDocument) {
      return;
    }
    setDocumentType(null);
    setFields({});
    setSavedDocId(null);
    setStatusMessage('');
  }, [resetCounter, loadedDocument]);

  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed) {
      return;
    }

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      text: trimmed,
      sender: 'user',
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setLoading(true);
    setStatusMessage('');

    try {
      const response = await fetch('/api/chat/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({
          message: trimmed,
          document_type: documentType?.type || null,
          current_fields: fields,
        }),
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const data: ChatResponse = await response.json();
      setFields(data.fields || {});

      if (data.document_type) {
        const matchedType = catalog.find((doc) => doc.type === data.document_type) || null;
        setDocumentType(matchedType);
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `ai-${Date.now()}`,
          text: data.response,
          sender: 'ai',
        },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          text: 'The assistant request failed. Check the backend and try again.',
          sender: 'ai',
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const requiredFieldsFilled = Boolean(
    documentType &&
      documentType.fields
        .filter((field) => field.required)
        .every((field) => String(fields[field.name] || '').trim())
  );

  const saveDocument = async () => {
    if (!documentType) {
      setStatusMessage('Select a document type first.');
      return null;
    }

    const payload = {
      title: `${documentType.type} - ${new Date().toLocaleDateString()}`,
      document_type: documentType.type,
      fields,
    };

    const method = savedDocId ? 'PUT' : 'POST';
    const url = savedDocId ? `/api/documents/${savedDocId}` : '/api/documents';

    const response = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error('Save failed');
    }

    const document = await response.json();
    setSavedDocId(document.id);
    setStatusMessage('Document saved.');
    return document;
  };

  const downloadPDF = async () => {
    try {
      const savedDocument = await saveDocument();
      const documentId = savedDocument?.id || savedDocId;
      if (!documentId) {
        throw new Error('No document id available');
      }

      window.open(`/api/documents/${documentId}/pdf`, '_blank');
    } catch (error) {
      setStatusMessage('Failed to save or download the PDF.');
    }
  };

  return (
    <div className="workspace-grid">
      <div className="panel chat-panel">
        <div className="chat-header">
          <div className="eyebrow">AI Drafting Assistant</div>
          <h2 className="panel-title">
            {documentType ? documentType.type : 'Start a new agreement'}
          </h2>
          <p className="helper-text" style={{ margin: '8px 0 0' }}>
            Describe the document you need, then refine the extracted fields in the preview panel before saving.
          </p>
          {statusMessage ? <div className="status-pill">{statusMessage}</div> : null}
        </div>
        <div className="chat-stream">
          {messages.map((message) => (
            <div key={message.id} className={`message-row ${message.sender}`}>
              <div className="message-bubble">
                {message.text}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div className="chat-composer">
          <div className="composer-row">
            <input
              ref={inputRef}
              className="field-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyPress}
              placeholder="Describe the agreement or paste 'Field Name: value' lines"
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="primary-button"
              style={{ minWidth: '132px', opacity: loading || !input.trim() ? 0.7 : 1 }}
            >
              {loading ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
      <div className="panel preview-panel">
        <div className="preview-header">
          <div className="eyebrow">Structured Preview</div>
          <h3 className="panel-title">Document Preview</h3>
          <p className="helper-text" style={{ margin: '8px 0 0' }}>
            Validate extracted values and complete any missing fields before generating the final document.
          </p>
        </div>
        <div className="preview-body">
        {documentType ? (
          <div>
            <h4 style={{ color: '#032147', marginTop: 0 }}>{documentType.type}</h4>
            {documentType.fields.map((field) => (
              <div key={field.name} className="field-block">
                <label className="field-label">
                  {field.label}
                  {field.required ? ' *' : ''}
                </label>
                {field.type === 'textarea' ? (
                  <textarea
                    className="field-input"
                    value={fields[field.name] || ''}
                    onChange={(e) => setFields((prev) => ({ ...prev, [field.name]: e.target.value }))}
                    rows={4}
                  />
                ) : (
                  <input
                    className="field-input"
                    type={field.type}
                    value={fields[field.name] || ''}
                    onChange={(e) => setFields((prev) => ({ ...prev, [field.name]: e.target.value }))}
                  />
                )}
              </div>
            ))}
            <div className="action-stack">
              <button
                onClick={() => {
                  saveDocument().catch(() => setStatusMessage('Failed to save document.'));
                }}
                className="secondary-button"
                style={{ width: '100%' }}
              >
                Save Document
              </button>
              <button
                onClick={downloadPDF}
                disabled={!requiredFieldsFilled}
                className="primary-button"
                style={{ width: '100%', opacity: requiredFieldsFilled ? 1 : 0.6 }}
              >
                Download PDF
              </button>
            </div>
          </div>
        ) : (
          <p className="helper-text">
            Start by asking for one of the supported agreements, such as Mutual NDA or Cloud Service Agreement.
          </p>
        )}
        </div>
      </div>
    </div>
  );
}
