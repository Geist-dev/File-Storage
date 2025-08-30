import os, json, time, mimetypes, re
from typing import Optional, List
from PIL import Image

from fastapi import FastAPI, Depends, HTTPException, UploadFile, File as F, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from config import settings
from database import Base, engine, get_db
from models import User, File
from schemas import RegisterIn, LoginIn, TokenOut, FileOut, FileListOut, VisibilityIn, FileMetaPatchIn
from security import hash_password, verify_password, make_token
from auth import get_current_user

app = FastAPI(title=settings.APP_NAME, version="0.3.0", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
os.makedirs(settings.STORAGE_DIR, exist_ok=True)

def validate_password(pw: str) -> str | None:
    """Вернуть текст ошибки, если пароль плохой; иначе None."""
    if not isinstance(pw, str) or len(pw) < 8:
        return "Пароль должен быть не короче 8 символов"
    import re
    if not re.search(r"[A-Za-z]", pw):
        return "Пароль должен содержать хотя бы одну букву"
    if not re.search(r"\d", pw):
        return "Пароль должен содержать хотя бы одну цифру"
    return None

def sanitize_folder(folder: str) -> str:
    folder = folder.strip().replace('..', '.')
    folder = re.sub(r'[^A-Za-z0-9_\-\/ ]+', '', folder)
    return folder.strip('/')

def json_load(s: str) -> List[str]:
    try:
        val = json.loads(s)
        if isinstance(val, list): return val
    except Exception: pass
    return []

def to_file_out(f: File) -> dict:
    return {
        "id": f.id,
        "name": f.name,
        "mime": f.mime,
        "size": f.size,
        "tags": json_load(f.tags),
        "is_public": f.is_public,
        "state": f.state,
        "created_at": f.created_at.isoformat() if f.created_at else "",
        "updated_at": f.updated_at.isoformat() if f.updated_at else "",
        "path": f.key.split("/",1)[1] if "/" in f.key else f.key,
        "thumb_available": os.path.exists(os.path.join(settings.STORAGE_DIR, f.key + ".thumb.png")),
    }

def make_thumbnail(src_path: str, thumb_path: str, max_size: int = 256):
    try:
        os.makedirs(os.path.dirname(thumb_path), exist_ok=True)
        with Image.open(src_path) as im:
            im.thumbnail((max_size, max_size))
            im.save(thumb_path, format='PNG')
            return True
    except Exception:
        return False

@app.post("/auth/register", response_model=TokenOut)
def register(payload: RegisterIn, db: Session = Depends(get_db)):
    exists = db.query(User).filter(User.email == payload.email).first()
    if exists:
        raise HTTPException(status_code=409, detail="Email already registered")
    err = validate_password(payload.password)
    if err:
        raise HTTPException(status_code=400, detail=err)
    user = User(email=payload.email, pass_hash=hash_password(payload.password))
    db.add(user); db.commit(); db.refresh(user)
    return {"token": make_token(user.id, user.email)}

@app.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.pass_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"token": make_token(user.id, user.email)}

@app.get("/me")
def me(current: User = Depends(get_current_user)):
    return {"id": current.id, "email": current.email}

@app.post("/files/upload", response_model=dict)
async def upload_file(
    file: UploadFile = F(...),
    tags: Optional[str] = Form(None),
    folder: Optional[str] = Form(None),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    allowed = [m.strip() for m in settings.ALLOWED_MIME.split(",") if m.strip()]
    mime = file.content_type or (mimetypes.guess_type(file.filename or "file")[0] or "application/octet-stream")
    if allowed and mime not in allowed:
        raise HTTPException(status_code=415, detail=f"Mime not allowed: {mime}")
    filename = file.filename or "file"
    sub = sanitize_folder(folder) if folder else ""
    ts = int(time.time() * 1000)
    safe = f"{ts}_{filename}".replace("..", ".")
    rel_key = f"{current.id}/" + (sub + "/" if sub else "") + safe
    abs_path = os.path.join(settings.STORAGE_DIR, rel_key)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)

    size = 0
    max_bytes = settings.MAX_UPLOAD_MB * 1024 * 1024
    with open(abs_path, "wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk: break
            size += len(chunk)
            if size > max_bytes:
                out.close()
                try: os.remove(abs_path)
                except Exception: pass
                raise HTTPException(status_code=413, detail="File too large")
            out.write(chunk)

    tag_str = tags if tags else "[]"
    try:
        t = json.loads(tag_str)
        if not isinstance(t, list): raise ValueError
        tag_str = json.dumps(t)
    except Exception:
        tag_str = "[]"

    rec = File(owner_id=current.id, key=rel_key, name=filename, mime=mime, size=size, tags=tag_str, state="ready")
    db.add(rec); db.commit(); db.refresh(rec)

    if mime.startswith("image/"):
        thumb_key = rel_key + ".thumb.png"
        thumb_path = os.path.join(settings.STORAGE_DIR, thumb_key)
        make_thumbnail(abs_path, thumb_path)

    return {"file": to_file_out(rec)}

@app.get("/files", response_model=FileListOut)
def list_files(
    q: Optional[str] = Query(None),
    tag: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: str = Query("active", description="active|deleted|all"),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(File).filter(File.owner_id == current.id)
    if state == "active":
        query = query.filter(File.state != "deleted")
    elif state == "deleted":
        query = query.filter(File.state == "deleted")
    if q:
        query = query.filter(File.name.like(f"%{q}%"))
    if tag:
        query = query.filter(File.tags.like(f"%\"{tag}\"%"))
    total = query.count()
    items = query.order_by(File.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": [to_file_out(f) for f in items], "total": total, "page": page, "page_size": page_size}

@app.get("/files/{file_id}/download")
def download_file(file_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.get(File, file_id)
    if not f or f.state != "ready": raise HTTPException(status_code=404, detail="File not found")
    if f.owner_id != current.id: raise HTTPException(status_code=403, detail="Forbidden")
    path = os.path.join(settings.STORAGE_DIR, f.key)
    if not os.path.exists(path): raise HTTPException(status_code=410, detail="File missing on disk")
    return FileResponse(path, media_type=f.mime, filename=f.name)

@app.get("/files/{file_id}/preview")
def preview(file_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.get(File, file_id)
    if not f or f.state != "ready": raise HTTPException(status_code=404, detail="File not found")
    if f.owner_id != current.id: raise HTTPException(status_code=403, detail="Forbidden")
    path = os.path.join(settings.STORAGE_DIR, f.key)
    if not os.path.exists(path): raise HTTPException(status_code=410, detail="Missing")
    if f.mime.startswith("image/"):
        return FileResponse(path, media_type=f.mime, filename=f.name)
    raise HTTPException(status_code=415, detail="Preview not supported")

@app.get("/files/{file_id}/thumb")
def thumb(file_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.get(File, file_id)
    if not f or f.state != "ready": raise HTTPException(status_code=404, detail="File not found")
    if f.owner_id != current.id: raise HTTPException(status_code=403, detail="Forbidden")
    tpath = os.path.join(settings.STORAGE_DIR, f.key + ".thumb.png")
    if not os.path.exists(tpath): raise HTTPException(status_code=404, detail="No thumb")
    return FileResponse(tpath, media_type="image/png", filename=f.name + ".thumb.png")

@app.delete("/files/{file_id}")
def soft_delete(file_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.get(File, file_id)
    if not f or f.owner_id != current.id or f.state == "deleted": raise HTTPException(status_code=404, detail="Not found")
    from datetime import datetime, timezone
    f.state = "deleted"; f.deleted_at = datetime.now(timezone.utc)
    db.add(f); db.commit(); db.refresh(f); return {"ok": True}

@app.post("/files/{file_id}/restore")
def restore(file_id: int, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.get(File, file_id)
    if not f or f.owner_id != current.id or f.state != "deleted": raise HTTPException(status_code=404, detail="Not found")
    f.state = "ready"; f.deleted_at = None
    db.add(f); db.commit(); db.refresh(f); return {"ok": True}

@app.post("/files/{file_id}/visibility")
def visibility(file_id: int, body: VisibilityIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Public access disabled: always keep files private
    f = db.get(File, file_id)
    if not f or f.owner_id != current.id or f.state != "ready": raise HTTPException(status_code=404, detail="Not found")
    if f.is_public:
        f.is_public = False
        db.add(f); db.commit(); db.refresh(f)
    return {"file": to_file_out(f)}

@app.patch("/files/{file_id}")
def patch_meta(file_id: int, body: FileMetaPatchIn, current: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f = db.get(File, file_id)
    if not f or f.owner_id != current.id: raise HTTPException(status_code=404, detail="Not found")
    changed = False
    if body.name is not None and body.name.strip():
        f.name = body.name.strip(); changed = True
    if body.tags is not None:
        f.tags = json.dumps(list(body.tags)); changed = True
    if changed: db.add(f); db.commit(); db.refresh(f)
    return {"file": to_file_out(f)}
