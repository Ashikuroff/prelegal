from fastapi import FastAPI, HTTPException, Depends, status, Request, Response, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime, timedelta
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import json
import os
from dotenv import load_dotenv
import litellm
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
import io
import hashlib
import secrets

load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database
DATABASE_URL = "sqlite:///./prelegal.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Models
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Document(Base):
    __tablename__ = "documents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    title = Column(String)
    document_type = Column(String)
    fields = Column(Text)  # JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")

Base.metadata.create_all(bind=engine)

# Pydantic models
class UserCreate(BaseModel):
    email: str = Field(..., pattern=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    password: str = Field(..., min_length=6, max_length=72)

class UserLogin(BaseModel):
    email: str
    password: str

class DocumentCreate(BaseModel):
    title: str
    document_type: str
    fields: Dict[str, Any]

class DocumentResponse(BaseModel):
    id: int
    title: str
    document_type: str
    fields: Dict[str, Any]
    created_at: datetime

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str
    fields: Optional[Dict[str, Any]] = None

# Security
import hashlib
import secrets

# Simple password hashing for now (replace with proper bcrypt later)
def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    hash_obj = hashlib.sha256((password + salt).encode())
    return f"{salt}:{hash_obj.hexdigest()}"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, hash_value = hashed_password.split(":", 1)
        hash_obj = hashlib.sha256((plain_password + salt).encode())
        return secrets.compare_digest(hash_obj.hexdigest(), hash_value)
    except:
        return False

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def authenticate_user(db: Session, email: str, password: str):
    user = get_user(db, email)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def get_current_user(request: Request, db: Session = Depends(lambda: SessionLocal())):
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = get_user(db, email)
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user

# Routes
@app.post("/api/auth/signup")
def signup(user: UserCreate, response: Response, db: Session = Depends(lambda: SessionLocal())):
    db_user = get_user(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed_password = get_password_hash(user.password)
    db_user = User(email=user.email, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    access_token = create_access_token(data={"sub": user.email})
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=1800, expires=1800)
    return {"message": "User created successfully"}

@app.post("/api/auth/signin")
def signin(user: UserLogin, response: Response, db: Session = Depends(lambda: SessionLocal())):
    db_user = authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    access_token = create_access_token(data={"sub": user.email})
    response.set_cookie(key="access_token", value=access_token, httponly=True, max_age=1800, expires=1800)
    return {"message": "Login successful"}

@app.post("/api/auth/signout")
def signout(response: Response):
    response.delete_cookie(key="access_token")
    return {"message": "Logout successful"}

@app.get("/api/auth/me")
def read_users_me(current_user: User = Depends(get_current_user)):
    return {"email": current_user.email}

@app.get("/api/documents", response_model=List[DocumentResponse])
def get_documents(current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    documents = db.query(Document).filter(Document.user_id == current_user.id).all()
    return [
        DocumentResponse(
            id=doc.id,
            title=doc.title,
            document_type=doc.document_type,
            fields=json.loads(doc.fields),
            created_at=doc.created_at
        ) for doc in documents
    ]

@app.post("/api/documents", response_model=DocumentResponse)
def create_document(doc: DocumentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    db_doc = Document(
        user_id=current_user.id,
        title=doc.title,
        document_type=doc.document_type,
        fields=json.dumps(doc.fields)
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return DocumentResponse(
        id=db_doc.id,
        title=db_doc.title,
        document_type=db_doc.document_type,
        fields=json.loads(db_doc.fields),
        created_at=db_doc.created_at
    )

@app.get("/api/documents/{doc_id}", response_model=DocumentResponse)
def get_document(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        document_type=doc.document_type,
        fields=json.loads(doc.fields),
        created_at=doc.created_at
    )

@app.put("/api/documents/{doc_id}", response_model=DocumentResponse)
def update_document(doc_id: int, doc: DocumentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    db_doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db_doc.title = doc.title
    db_doc.document_type = doc.document_type
    db_doc.fields = json.dumps(doc.fields)
    db.commit()
    db.refresh(db_doc)
    return DocumentResponse(
        id=db_doc.id,
        title=db_doc.title,
        document_type=db_doc.document_type,
        fields=json.loads(db_doc.fields),
        created_at=db_doc.created_at
    )

@app.get("/api/documents/{doc_id}/pdf")
def download_pdf(doc_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(lambda: SessionLocal())):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    fields = json.loads(doc.fields)
    pdf_bytes = generate_pdf(doc.document_type, fields)
    
    from fastapi.responses import StreamingResponse
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={doc.document_type.replace(' ', '_')}.pdf"}
    )

# PDF generation helper
def get_greeting():
    return {"greeting": "Hello! I'm here to help you draft a legal agreement. What type of document would you like to create?"}

@app.post("/api/chat/message")
async def chat_message(chat: ChatMessage, request: Request, db: Session = Depends(lambda: SessionLocal())):
    # Load catalog
    with open("/app/catalog.json") as f:
        catalog = json.load(f)
    
    # Use LiteLLM with OpenRouter free model
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return {"response": "AI service not configured. Please set OPENROUTER_API_KEY.", "fields": {}}
    
    litellm.api_key = api_key
    
    # Detect document type from message
    detected_type = None
    for doc in catalog["documents"]:
        if doc["type"].lower() in chat.message.lower():
            detected_type = doc
            break
    
    if not detected_type:
        return {"response": "I couldn't detect the document type. Please specify what kind of legal agreement you want to create.", "fields": {}}
    
    # Prepare structured prompt for field extraction
    fields_prompt = f"Extract the following fields from the user's message for a {detected_type['type']}:\n"
    for field in detected_type["fields"]:
        fields_prompt += f"- {field['name']}: {field['label']}\n"
    fields_prompt += "\nUser message: " + chat.message
    fields_prompt += "\n\nRespond with a JSON object containing the extracted fields. If a field is not mentioned, omit it or use an empty string."
    
    try:
        response = await litellm.acompletion(
            model="openrouter/meta-llama/llama-3.2-3b-instruct:free",
            messages=[{"role": "user", "content": fields_prompt}],
            temperature=0.1,
        )
        ai_response = response.choices[0].message.content
        
        # Parse JSON from response
        try:
            fields = json.loads(ai_response)
        except:
            fields = {}
        
        # Generate conversational response
        conversational_prompt = f"Based on the extracted fields for a {detected_type['type']}, provide a brief conversational response asking for any missing required fields or confirming the information."
        
        conv_response = await litellm.acompletion(
            model="openrouter/meta-llama/llama-3.2-3b-instruct:free",
            messages=[{"role": "user", "content": conversational_prompt}],
            temperature=0.7,
        )
        
        return {"response": conv_response.choices[0].message.content, "fields": fields}
    except Exception as e:
        return {"response": f"Sorry, I encountered an error: {str(e)}. Please try again.", "fields": {}}

@app.get("/api/health")
def health():
    return {"status": "ok"}

# Static files
app.mount("/", StaticFiles(directory="/app/static", html=True), name="static")

# PDF generation helper
def generate_pdf(document_type: str, fields: Dict[str, Any]) -> bytes:
    # Load template
    template_path = f"/app/templates/{document_type.lower().replace(' ', '_')}.json"
    try:
        with open(template_path) as f:
            templates = json.load(f)
        template = templates.get(document_type, {}).get("template", "")
    except:
        # Fallback to simple template
        template = f"{document_type}\n\n" + "\n".join([f"{k}: {v}" for k, v in fields.items()])
    
    # Replace placeholders
    for key, value in fields.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Split template into paragraphs
    paragraphs = template.split('\n\n')
    for para in paragraphs:
        if para.strip():
            story.append(Paragraph(para, styles['Normal']))
            story.append(Spacer(1, 12))
    
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()