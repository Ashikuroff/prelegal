import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import backend.main as main


def setup_module() -> None:
    main.Base.metadata.drop_all(bind=main.engine)
    main.Base.metadata.create_all(bind=main.engine)


def teardown_function() -> None:
    with main.SessionLocal() as db:
        db.query(main.Document).delete()
        db.query(main.User).delete()
        db.commit()


client = TestClient(main.app)


def signup_and_authenticate(email: str = "user@example.com", password: str = "password123"):
    response = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert response.status_code == 200
    return response


def test_auth_document_chat_and_pdf_flow():
    signup_and_authenticate()

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"

    greeting = client.get("/api/chat/greeting")
    assert greeting.status_code == 200
    assert "draft" in greeting.json()["greeting"].lower()

    chat = client.post(
        "/api/chat/message",
        json={
            "message": "I need a Mutual NDA\nParty 1 Name: Acme Inc\nParty 2 Name: Beta LLC",
            "current_fields": {},
        },
    )
    assert chat.status_code == 200
    chat_payload = chat.json()
    assert chat_payload["document_type"] == "Mutual NDA"
    assert chat_payload["fields"]["party1_name"] == "Acme Inc"
    assert chat_payload["fields"]["party2_name"] == "Beta LLC"
    assert chat_payload["complete"] is False

    create_doc = client.post(
        "/api/documents",
        json={
            "title": "Mutual NDA Test",
            "document_type": "Mutual NDA",
            "fields": {
                "party1_name": "Acme Inc",
                "party1_address": "1 Main St",
                "party2_name": "Beta LLC",
                "party2_address": "2 Oak Ave",
                "effective_date": "2026-04-08",
                "confidentiality_period": "3",
                "jurisdiction": "California",
            },
        },
    )
    assert create_doc.status_code == 200
    doc = create_doc.json()
    doc_id = doc["id"]

    listed = client.get("/api/documents")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    fetched = client.get(f"/api/documents/{doc_id}")
    assert fetched.status_code == 200
    assert fetched.json()["title"] == "Mutual NDA Test"

    updated = client.put(
        f"/api/documents/{doc_id}",
        json={
            "title": "Mutual NDA Final",
            "document_type": "Mutual NDA",
            "fields": {
                "party1_name": "Acme Inc",
                "party1_address": "1 Main St",
                "party2_name": "Beta LLC",
                "party2_address": "2 Oak Ave",
                "effective_date": "2026-04-08",
                "confidentiality_period": "5",
                "jurisdiction": "California",
            },
        },
    )
    assert updated.status_code == 200
    assert updated.json()["fields"]["confidentiality_period"] == "5"

    pdf = client.get(f"/api/documents/{doc_id}/pdf")
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    deleted = client.delete(f"/api/documents/{doc_id}")
    assert deleted.status_code == 200

    listed_after_delete = client.get("/api/documents")
    assert listed_after_delete.status_code == 200
    assert listed_after_delete.json() == []


def test_chat_requires_document_hint_when_not_detectable():
    response = client.post(
        "/api/chat/message",
        json={"message": "Please help me draft something", "current_fields": {}},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["document_type"] is None
    assert "identify" in payload["response"].lower()


def test_legacy_password_hash_can_still_sign_in_and_is_upgraded():
    legacy_salt = "legacysalt"
    legacy_hash = main.hashlib.sha256(("password123" + legacy_salt).encode()).hexdigest()

    with main.SessionLocal() as db:
        db_user = main.User(email="legacy@example.com", hashed_password=f"{legacy_salt}:{legacy_hash}")
        db.add(db_user)
        db.commit()

    signin = client.post(
        "/api/auth/signin",
        json={"email": "legacy@example.com", "password": "password123"},
    )
    assert signin.status_code == 200

    with main.SessionLocal() as db:
        user = db.query(main.User).filter(main.User.email == "legacy@example.com").first()
        assert user is not None
        assert user.hashed_password != f"{legacy_salt}:{legacy_hash}"
        assert main.verify_password("password123", user.hashed_password)
