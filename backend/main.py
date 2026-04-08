import io
import json
import os
import re
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from dotenv import load_dotenv
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import Session, declarative_base, relationship, sessionmaker
import hashlib

try:
    import litellm
except Exception:  # pragma: no cover - optional dependency at runtime
    litellm = None

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path("/app/static")
TEMPLATES_DIR = Path("/app/templates")
CATALOG_PATH = Path("/app/catalog.json")
DATABASE_PATH = BASE_DIR / "prelegal.db"

if not STATIC_DIR.exists():
    STATIC_DIR = BASE_DIR / "frontend" / "out"
if not TEMPLATES_DIR.exists():
    TEMPLATES_DIR = BASE_DIR / "templates"
if not CATALOG_PATH.exists():
    CATALOG_PATH = BASE_DIR / "catalog.json"

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
FREE_MODEL_NAME = "openrouter/meta-llama/llama-3.2-3b-instruct:free"

app = FastAPI(title="Prelegal")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    document_type = Column(String, nullable=False)
    fields = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    user = relationship("User")


Base.metadata.create_all(bind=engine)


class UserCreate(BaseModel):
    email: str = Field(
        ...,
        pattern=r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    )
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
    document_type: Optional[str] = None
    current_fields: Dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    response: str
    fields: Dict[str, Any] = Field(default_factory=dict)
    document_type: Optional[str] = None
    complete: bool = False


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def load_catalog() -> Dict[str, Any]:
    with CATALOG_PATH.open() as handle:
        return json.load(handle)


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def get_password_hash(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    return f"{salt}:{derived}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        salt, expected = hashed_password.split(":", 1)
    except ValueError:
        return False

    derived_pbkdf2 = hashlib.pbkdf2_hmac("sha256", plain_password.encode(), salt.encode(), 100_000).hex()
    if secrets.compare_digest(derived_pbkdf2, expected):
        return True

    # Backward compatibility for accounts created before the PBKDF2 upgrade.
    derived_legacy = hashlib.sha256((plain_password + salt).encode()).hexdigest()
    return secrets.compare_digest(derived_legacy, expected)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_user(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    salt, expected = user.hashed_password.split(":", 1)
    derived_pbkdf2 = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 100_000).hex()
    if not secrets.compare_digest(derived_pbkdf2, expected):
        user.hashed_password = get_password_hash(password)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def get_current_user(
    access_token: Optional[str] = Cookie(default=None),
    db: Session = Depends(get_db),
) -> User:
    if not access_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if not email:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = get_user(db, email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


def get_document_type_by_name(document_type: str) -> Optional[Dict[str, Any]]:
    normalized_target = normalize_text(document_type)
    for document in load_catalog()["documents"]:
        if normalize_text(document["type"]) == normalized_target:
            return document
    return None


def detect_document_type(message: str) -> Optional[Dict[str, Any]]:
    normalized_message = normalize_text(message)
    ranked: List[tuple[int, Dict[str, Any]]] = []
    for document in load_catalog()["documents"]:
        doc_name = normalize_text(document["type"])
        tokens = doc_name.split()
        score = 0
        if doc_name in normalized_message:
            score += 5
        for token in tokens:
            if token and token in normalized_message:
                score += 1
        if document["type"] == "Mutual NDA" and ("nda" in normalized_message or "non disclosure" in normalized_message):
            score += 4
        if score:
            ranked.append((score, document))
    if not ranked:
        return None
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def extract_fields_from_message(document: Dict[str, Any], message: str) -> Dict[str, str]:
    extracted: Dict[str, str] = {}
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    lower_message = message.lower()

    for field in document["fields"]:
        field_name = field["name"]
        label = field["label"]
        synonyms = {
            field_name.lower(),
            label.lower(),
            field_name.replace("_", " ").lower(),
        }

        for line in lines:
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            if normalize_text(key) in {normalize_text(item) for item in synonyms} and value.strip():
                extracted[field_name] = value.strip()
                break

        if field_name in extracted:
            continue

        token_match = re.search(rf"{re.escape(field_name.replace('_', ' '))}\s+is\s+(.+?)(?:[.,]|$)", lower_message)
        if token_match:
            extracted[field_name] = token_match.group(1).strip().strip(".")

    return extracted


async def extract_fields_with_free_llm(document: Dict[str, Any], message: str) -> Dict[str, Any]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key or litellm is None:
        return {}

    schema = {
        "type": "object",
        "properties": {
            field["name"]: {"type": "string"} for field in document["fields"]
        },
        "additionalProperties": False,
    }
    field_list = ", ".join(field["name"] for field in document["fields"])
    prompt = (
        f"Extract values for {document['type']} fields from the user message. "
        f"Return JSON only. Omit unknown values. Supported fields: {field_list}.\n\n"
        f"User message:\n{message}"
    )

    try:
        response = await litellm.acompletion(
            model=FREE_MODEL_NAME,
            api_key=api_key,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=400,
        )
    except Exception:
        return {}

    try:
        content = response.choices[0].message.content or "{}"
        payload = json.loads(content)
    except Exception:
        return {}

    return {
        key: value
        for key, value in payload.items()
        if isinstance(value, str) and value.strip() and key in schema["properties"]
    }


def merge_fields(existing_fields: Dict[str, Any], new_fields: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(existing_fields)
    for key, value in new_fields.items():
        if value is None:
            continue
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                continue
            merged[key] = stripped
        else:
            merged[key] = value
    return merged


def missing_required_fields(document: Dict[str, Any], fields: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        field
        for field in document["fields"]
        if field.get("required") and not str(fields.get(field["name"], "")).strip()
    ]


def build_chat_response(document: Dict[str, Any], fields: Dict[str, Any]) -> str:
    missing = missing_required_fields(document, fields)
    if not missing:
        return (
            f"I have enough information to prepare the {document['type']}. "
            "Review the preview, save it, or download the PDF."
        )

    next_field = missing[0]
    filled_count = len(document["fields"]) - len(missing)
    if filled_count == 0:
        return (
            f"I can help you draft a {document['type']}. "
            f"Please provide {next_field['label']}."
        )

    return (
        f"Captured what I could for the {document['type']}. "
        f"I still need {next_field['label']}."
    )


def template_filename(document_type: str) -> str:
    return f"{normalize_text(document_type).replace(' ', '_')}.json"


def render_document_text(document_type: str, fields: Dict[str, Any]) -> str:
    template_path = TEMPLATES_DIR / template_filename(document_type)
    template = None

    if template_path.exists():
        with template_path.open() as handle:
            template_payload = json.load(handle)
        template = template_payload.get(document_type, {}).get("template")

    if not template:
        lines = [document_type, ""]
        lines.extend(f"{key.replace('_', ' ').title()}: {value}" for key, value in fields.items())
        template = "\n".join(lines)

    for key, value in fields.items():
        template = template.replace(f"{{{{{key}}}}}", str(value))

    return re.sub(r"{{[^}]+}}", "[pending]", template)


def generate_pdf(document_type: str, fields: Dict[str, Any]) -> bytes:
    rendered = render_document_text(document_type, fields)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    for paragraph in rendered.split("\n\n"):
        if not paragraph.strip():
            continue
        story.append(Paragraph(paragraph.replace("\n", "<br/>"), styles["Normal"]))
        story.append(Spacer(1, 12))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()


@app.post("/api/auth/signup")
def signup(user: UserCreate, response: Response, db: Session = Depends(get_db)) -> Dict[str, str]:
    existing = get_user(db, user.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    db_user = User(email=user.email, hashed_password=get_password_hash(user.password))
    db.add(db_user)
    db.commit()
    access_token = create_access_token({"sub": user.email})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"message": "User created successfully"}


@app.post("/api/auth/signin")
def signin(user: UserLogin, response: Response, db: Session = Depends(get_db)) -> Dict[str, str]:
    db_user = authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token({"sub": user.email})
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"message": "Login successful"}


@app.post("/api/auth/signout")
def signout(response: Response) -> Dict[str, str]:
    response.delete_cookie(key="access_token")
    return {"message": "Logout successful"}


@app.get("/api/auth/me")
def read_users_me(current_user: User = Depends(get_current_user)) -> Dict[str, str]:
    return {"email": current_user.email}


@app.get("/api/documents", response_model=List[DocumentResponse])
def get_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[DocumentResponse]:
    documents = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .all()
    )
    return [
        DocumentResponse(
            id=doc.id,
            title=doc.title,
            document_type=doc.document_type,
            fields=json.loads(doc.fields),
            created_at=doc.created_at,
        )
        for doc in documents
    ]


@app.post("/api/documents", response_model=DocumentResponse)
def create_document(
    doc: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    if not get_document_type_by_name(doc.document_type):
        raise HTTPException(status_code=400, detail="Unsupported document type")

    db_doc = Document(
        user_id=current_user.id,
        title=doc.title,
        document_type=doc.document_type,
        fields=json.dumps(doc.fields),
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return DocumentResponse(
        id=db_doc.id,
        title=db_doc.title,
        document_type=db_doc.document_type,
        fields=json.loads(db_doc.fields),
        created_at=db_doc.created_at,
    )


@app.get("/api/documents/{doc_id}", response_model=DocumentResponse)
def get_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        id=doc.id,
        title=doc.title,
        document_type=doc.document_type,
        fields=json.loads(doc.fields),
        created_at=doc.created_at,
    )


@app.put("/api/documents/{doc_id}", response_model=DocumentResponse)
def update_document(
    doc_id: int,
    doc: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DocumentResponse:
    db_doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not get_document_type_by_name(doc.document_type):
        raise HTTPException(status_code=400, detail="Unsupported document type")

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
        created_at=db_doc.created_at,
    )


@app.delete("/api/documents/{doc_id}")
def delete_document(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    db_doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not db_doc:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(db_doc)
    db.commit()
    return {"message": "Document deleted"}


@app.get("/api/documents/{doc_id}/pdf")
def download_pdf(
    doc_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == current_user.id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    pdf_bytes = generate_pdf(doc.document_type, json.loads(doc.fields))
    filename = normalize_text(doc.document_type).replace(" ", "_")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}.pdf"},
    )


@app.get("/api/chat/greeting")
def get_greeting() -> Dict[str, str]:
    return {
        "greeting": (
            "Hello. Tell me which agreement you want to draft, and you can also paste details "
            "as 'Field Name: value' lines for faster extraction."
        )
    }


@app.post("/api/chat/message", response_model=ChatResponse)
async def chat_message(chat: ChatMessage, request: Request) -> ChatResponse:
    document = get_document_type_by_name(chat.document_type) if chat.document_type else detect_document_type(chat.message)
    if not document:
        return ChatResponse(
            response=(
                "I couldn't identify the document type yet. Choose one from the catalog, "
                "for example Mutual NDA, Cloud Service Agreement, or Pilot Agreement."
            ),
            fields=chat.current_fields,
            document_type=None,
            complete=False,
        )

    extracted = extract_fields_from_message(document, chat.message)
    if not extracted:
        extracted = await extract_fields_with_free_llm(document, chat.message)
    merged_fields = merge_fields(chat.current_fields, extracted)
    complete = not missing_required_fields(document, merged_fields)

    return ChatResponse(
        response=build_chat_response(document, merged_fields),
        fields=merged_fields,
        document_type=document["type"],
        complete=complete,
    )


@app.get("/api/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


if STATIC_DIR.exists():
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
