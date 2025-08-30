from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional

class TokenOut(BaseModel):
    token: str

class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class FileCreateOut(BaseModel):
    id: int
    name: str
    mime: str
    size: int
    tags: List[str] = []
    is_public: bool
    state: str
    path: str | None = None
    thumb_available: bool = False

class FileOut(FileCreateOut):
    created_at: str
    updated_at: str

class FileListOut(BaseModel):
    items: List[FileOut]
    total: int
    page: int
    page_size: int

class VisibilityIn(BaseModel):
    is_public: bool

class FileMetaPatchIn(BaseModel):
    name: Optional[str] = None
    tags: Optional[List[str]] = None
