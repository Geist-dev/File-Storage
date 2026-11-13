import uuid

from conftest import account


def credentials(client):
    return account(client, f"{uuid.uuid4().hex}@example.com")


def test_file_lifecycle_and_owner_isolation(client):
    owner, other = credentials(client), credentials(client)
    response = client.post("/files/upload", headers=owner,
        files={"file": ("report.txt", b"original bytes\x00\xff", "text/plain")},
        data={"folder": "work/reports", "tags": '["work", "работа"]'})
    assert response.status_code == 200
    file_id = response.json()["file"]["id"]
    assert client.get("/files", headers=other).json()["total"] == 0
    for endpoint in ("download", "preview", "thumb"):
        assert client.get(f"/files/{file_id}/{endpoint}", headers=other).status_code in (403, 404)
    assert client.delete(f"/files/{file_id}", headers=other).status_code == 404
    assert client.patch(f"/files/{file_id}", headers=other, json={"name": "stolen"}).status_code == 404
    download = client.get(f"/files/{file_id}/download", headers=owner)
    assert download.content == b"original bytes\x00\xff"
    assert client.get("/files", headers=owner, params={"tag": "work"}).json()["total"] == 1
    assert client.get("/files", headers=owner, params={"tag": "работа"}).json()["total"] == 1
    assert client.delete(f"/files/{file_id}", headers=owner).status_code == 200
    assert client.get(f"/files/{file_id}/download", headers=owner).status_code == 404
    assert client.get("/files", headers=owner, params={"state": "deleted"}).json()["total"] == 1
    assert client.post(f"/files/{file_id}/restore", headers=other).status_code == 404
    assert client.post(f"/files/{file_id}/restore", headers=owner).status_code == 200
    assert client.get(f"/files/{file_id}/download", headers=owner).content == download.content


def test_upload_limits_and_private_access(client):
    headers = credentials(client)
    assert client.get("/files").status_code in (401, 403)
    assert client.post("/files/upload", headers=headers, files={"file": ("large.txt", b"x" * (1024 * 1024 + 1), "text/plain")}).status_code == 413
    assert client.post("/files/upload", headers=headers, files={"file": ("script.html", b"<script></script>", "text/html")}).status_code == 415
    assert client.get("/files", headers=headers).json()["total"] == 0


def test_invalid_token_subject_returns_401(client):
    from config import settings
    from jose import jwt
    token = jwt.encode({"sub": "not-an-integer"}, settings.JWT_SECRET, algorithm="HS256")
    assert client.get("/me", headers={"Authorization": "Bearer " + token}).status_code == 401


def test_pagination_and_filter_validation(client):
    headers = credentials(client)
    for name in ("alpha.txt", "beta.txt", "gamma.txt"):
        assert client.post("/files/upload", headers=headers, files={"file": (name, b"hello", "text/plain")}).status_code == 200
    first = client.get("/files", headers=headers, params={"page_size": 2}).json()
    second = client.get("/files", headers=headers, params={"page_size": 2, "page": 2}).json()
    assert first["total"] == 3
    assert len(first["items"]) == 2 and len(second["items"]) == 1
    assert client.get("/files", headers=headers, params={"q": "alpha"}).json()["total"] == 1
    assert client.get("/files", headers=headers, params={"state": "typo"}).status_code == 422


def test_weak_password_rejected(client):
    response = client.post("/auth/register", json={"email": "weak@example.com", "password": "abcdefgh"})
    assert response.status_code == 400


def test_frontend_served_with_api(client):
    assert client.get("/").status_code == 200
    assert "File Storage" in client.get("/").text
    assert client.get("/app.js").status_code == 200
    assert client.get("/backend/.env").status_code == 404


def test_thumbnail_preview_and_safe_filename(client):
    import io
    from PIL import Image
    image = io.BytesIO()
    Image.new('RGB', (640, 480), '#b9e49b').save(image, format='PNG')
    headers = credentials(client)
    response = client.post('/files/upload', headers=headers,
        files={'file': ('../../sample.png', image.getvalue(), 'image/png')})
    assert response.status_code == 200
    item = response.json()['file']
    assert item['name'] == 'sample.png'
    assert item['thumb_available'] is True
    assert item['path'] == ''
    thumbnail = client.get(f"/files/{item['id']}/thumb", headers=headers)
    assert thumbnail.status_code == 200
    with Image.open(io.BytesIO(thumbnail.content)) as resized:
        assert max(resized.size) <= 256
    assert client.get(f"/files/{item['id']}/preview", headers=headers).content == image.getvalue()
    result = client.patch(f"/files/{item['id']}", headers=headers,
        json={'name': 'renamed.png', 'tags': ['личное']})
    assert result.json()['file']['name'] == 'renamed.png'
    assert client.get('/files', headers=headers, params={'tag': 'личное'}).json()['total'] == 1


def test_password_byte_limit(client):
    response = client.post('/auth/register', json={
        'email': 'long@example.com', 'password': 'A1' + 'я' * 40})
    assert response.status_code == 400


def test_login_and_invalid_password(client):
    email = f'{uuid.uuid4().hex}@example.com'
    account(client, email)
    response = client.post('/auth/login', json={'email': email, 'password': 'SamplePass123'})
    assert response.status_code == 200
    assert client.get('/me', headers={'Authorization': 'Bearer ' + response.json()['token']}).json()['email'] == email
    assert client.post('/auth/login', json={'email': email, 'password': 'wrong'}).status_code == 401


def test_search_treats_wildcards_literally_and_reads_legacy_tags(client):
    import json
    from database import SessionLocal
    from models import File
    headers = credentials(client)
    for name in ('100%.txt', '1000.txt'):
        client.post('/files/upload', headers=headers,
            files={'file': (name, b'content', 'text/plain')}, data={'tags': '["a_b"]'})
    assert client.get('/files', headers=headers, params={'q': '%'}).json()['total'] == 1
    assert client.get('/files', headers=headers, params={'tag': 'a%b'}).json()['total'] == 0
    file_id = client.get('/files', headers=headers).json()['items'][0]['id']
    with SessionLocal() as db:
        item = db.get(File, file_id)
        item.tags = json.dumps(['работа'], ensure_ascii=True)
        db.commit()
    assert client.get('/files', headers=headers, params={'tag': 'работа'}).json()['total'] == 1
