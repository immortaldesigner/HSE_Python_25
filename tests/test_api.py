import pytest

def test_create_link_anonymous(client):
    response = client.post("/links/shorten", json={"original_url": "https://google.com"})
    assert response.status_code == 200
    data = response.json()
    assert "short_code" in data
    assert data["original_url"] == "https://google.com"

def test_create_link_custom_alias(client):
    response = client.post("/links/shorten", json={
        "original_url": "https://yandex.ru",
        "custom_alias": "my-alias"
    })
    assert response.status_code == 200
    assert response.json()["short_code"] == "my-alias"

def test_create_duplicate_alias(client):
    client.post("/links/shorten", json={"original_url": "https://a.com", "custom_alias": "dup"})
    response = client.post("/links/shorten", json={"original_url": "https://b.com", "custom_alias": "dup"})
    assert response.status_code == 400
    assert response.json()["detail"] == "Short code already exists"

def test_redirect_and_404(client):
    resp_404 = client.get("/nonexistent", follow_redirects=False)
    assert resp_404.status_code == 404

    create_resp = client.post("/links/shorten", json={"original_url": "https://fastapi.tiangolo.com"})
    code = create_resp.json()["short_code"]
    
    resp_redir = client.get(f"/{code}", follow_redirects=False)
    assert resp_redir.status_code == 307
    assert resp_redir.headers["location"] == "https://fastapi.tiangolo.com"

def test_get_stats(client):
    client.post("/links/shorten", json={"original_url": "https://test.com", "custom_alias": "stats-test"})
    response = client.get("/links/stats-test/stats")
    assert response.status_code == 200
    assert "click_count" in response.json()

def test_update_link(client):
    client.post("/links/shorten", json={"original_url": "https://old.com", "custom_alias": "upd-me"})
    update_resp = client.put("/links/upd-me", json={"original_url": "https://new.com"})
    
    assert update_resp.status_code == 200

def test_delete_link(client):
    client.post("/links/shorten", json={"original_url": "https://del.com", "custom_alias": "del-me"})
    del_resp = client.delete("/links/del-me")
    assert del_resp.status_code == 200
    
    get_resp = client.get("/links/del-me/stats")
    assert get_resp.status_code == 404

def test_search_link(client):
    url = "https://unique-search-test.com"
    client.post("/links/shorten", json={"original_url": url, "custom_alias": "search-me"})
    
    response = client.get(f"/links/search?original_url={url}")
    assert response.status_code == 200
    assert response.json()["short_code"] == "search-me"

def test_search_link_not_found(client):
    response = client.get("/links/search?original_url=https://notfound.com")
    assert response.status_code == 404

def test_get_qr_code(client):
    client.post("/links/shorten", json={"original_url": "https://google.com", "custom_alias": "qr-test"})
    response = client.get("/links/qr-test/qr")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"

def test_update_link_forbidden(client, db_session):
    from app.models.link import Link
    other_link = Link(original_url="https://other.com", short_code="other", user_id=999)
    db_session.add(other_link)
    db_session.commit()

    response = client.put("/links/other", json={"original_url": "https://hacked.com"})
    assert response.status_code == 403

def test_user_registration_flow(client):
    payload = {"username": "newuser", "password": "strongpassword"}
    response = client.post("/register", json=payload) 
    assert response.status_code in [200, 201]


def test_full_auth_flow(client):
    client.post("/register", json={"username": "testuser", "password": "password123"})
    
    from jose import jwt
    from datetime import datetime, timedelta
    
    SECRET = "your-secret-key"
    ALGO = "HS256"
    
    payload = {
        "sub": "testuser",
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    token = jwt.encode(payload, SECRET, algorithm=ALGO)
    
    headers = {"Authorization": f"Bearer {token}"}
    payload_link = {"original_url": "https://google.com"}
    
    response = client.post("/links/shorten", json=payload_link, headers=headers)
    
    assert response.status_code in [200, 201]

def test_security_utils():
    from app.services.security import hash_password, verify_password, generate_short_code
    
    pwd = "my_password"
    hashed = hash_password(pwd)
    assert verify_password(pwd, hashed) is True
    assert verify_password("wrong", hashed) is False
    
    code = generate_short_code()
    assert len(code) == 6


def test_security_failures(client):
    headers = {"Authorization": "Bearer invalid-token-structure"}
    response = client.post("/links/shorten", json={"original_url": "https://test.com"}, headers=headers)
    assert response.status_code == 200

def test_get_current_user_required(client):
    from app.main import app
    from app.services.security import get_current_user
    
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]

    response = client.delete("/links/any-code")
    assert response.status_code == 401

def test_expired_token(client):
    from jose import jwt
    from datetime import datetime, timedelta
    from app.core.config import SECRET_KEY, ALGORITHM
    
    payload = {"sub": "testuser", "exp": datetime.utcnow() - timedelta(days=1)}
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post("/links/shorten", json={"original_url": "https://test.com"}, headers=headers)
    assert response.status_code == 200

def test_root_and_docs(client):

    assert client.get("/").status_code == 200
    assert client.get("/docs").status_code == 200

def test_security_extra_cases(client):
    headers = {"Authorization": "Bearer "}
    assert client.post("/links/shorten", json={"original_url": "https://a.com"}, headers=headers).status_code == 200

    headers = {"Authorization": "Basic dGVzdDp0ZXN0"}
    assert client.post("/links/shorten", json={"original_url": "https://a.com"}, headers=headers).status_code == 200


def test_security_deep_coverage(client, db_session):
    from app.main import app
    from app.services.security import get_current_user, get_current_user_optional
    from jose import jwt
    from app.core.config import SECRET_KEY, ALGORITHM
    from datetime import datetime, timedelta 

    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
    if get_current_user_optional in app.dependency_overrides:
        del app.dependency_overrides[get_current_user_optional]

    token_no_user = jwt.encode({"sub": "ghost_user", "exp": datetime.utcnow() + timedelta(hours=1)}, 
                               SECRET_KEY, algorithm=ALGORITHM)
    headers = {"Authorization": f"Bearer {token_no_user}"}
    resp = client.post("/links/shorten", json={"original_url": "https://a.com"}, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "User not found"

    headers = {"Authorization": "Bearer totally-garbage-token"}
    resp = client.post("/links/shorten", json={"original_url": "https://a.com"}, headers=headers)
    assert resp.status_code == 401
    assert resp.json()["detail"] == "Invalid token"

    resp = client.post("/links/shorten", json={"original_url": "https://a.com"})
    assert resp.status_code == 200