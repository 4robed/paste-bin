from fastapi import APIRouter, Depends, Form, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import get_db
from crud import create_paste, get_paste, increment_views
from schemas import PasteCreate, PasteResponse
from utils import (
    EXPIRY_LABELS,
    verify_password,
    make_unlock_cookie,
    verify_unlock_cookie,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")

LANGUAGES = [
    ("plaintext", "Plain Text"),
    ("python", "Python"),
    ("javascript", "JavaScript"),
    ("typescript", "TypeScript"),
    ("html", "HTML"),
    ("css", "CSS"),
    ("json", "JSON"),
    ("bash", "Bash / Shell"),
    ("sql", "SQL"),
    ("go", "Go"),
    ("rust", "Rust"),
    ("java", "Java"),
    ("cpp", "C++"),
    ("c", "C"),
    ("php", "PHP"),
    ("ruby", "Ruby"),
    ("yaml", "YAML"),
    ("toml", "TOML"),
    ("markdown", "Markdown"),
    ("dockerfile", "Dockerfile"),
]

COOKIE_NAME = "paste_unlock"


def _is_unlocked(request: Request, short_code: str) -> bool:
    token = request.cookies.get(f"{COOKIE_NAME}_{short_code}")
    if not token:
        return False
    return verify_unlock_cookie(token, short_code)


# ── HTML routes ────────────────────────────────────────────────────────────────

@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "languages": LANGUAGES, "expiry_labels": EXPIRY_LABELS},
    )


@router.post("/", response_class=RedirectResponse)
async def submit_paste(
    request: Request,
    title: str = Form(default=""),
    content: str = Form(...),
    language: str = Form(default="plaintext"),
    password: str = Form(default=""),
    expiry: str = Form(default="never"),
    db: Session = Depends(get_db),
):
    if not content.strip():
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "languages": LANGUAGES,
                "expiry_labels": EXPIRY_LABELS,
                "error": "Code content cannot be empty.",
                "form": {"title": title, "content": content, "language": language},
            },
            status_code=422,
        )

    paste = create_paste(
        db,
        content=content,
        language=language,
        title=title.strip() or None,
        password=password.strip() or None,
        expiry=expiry if expiry in EXPIRY_LABELS else "never",
    )
    return RedirectResponse(url=f"/{paste.short_code}", status_code=303)


@router.get("/{short_code}", response_class=HTMLResponse)
async def view_paste(short_code: str, request: Request, db: Session = Depends(get_db)):
    paste = get_paste(db, short_code)
    if paste is None:
        raise HTTPException(status_code=404, detail="Paste not found or has expired.")

    if paste.password_hash and not _is_unlocked(request, short_code):
        return templates.TemplateResponse(
            "password.html",
            {"request": request, "short_code": short_code, "error": None},
        )

    increment_views(db, paste)
    return templates.TemplateResponse(
        "paste.html",
        {"request": request, "paste": paste},
    )


@router.post("/{short_code}/unlock", response_class=HTMLResponse)
async def unlock_paste(
    short_code: str,
    request: Request,
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    paste = get_paste(db, short_code)
    if paste is None:
        raise HTTPException(status_code=404, detail="Paste not found or has expired.")

    if not paste.password_hash or not verify_password(password, paste.password_hash):
        return templates.TemplateResponse(
            "password.html",
            {"request": request, "short_code": short_code, "error": "Incorrect password."},
        )

    response = RedirectResponse(url=f"/{short_code}", status_code=303)
    response.set_cookie(
        key=f"{COOKIE_NAME}_{short_code}",
        value=make_unlock_cookie(short_code),
        httponly=True,
        samesite="lax",
    )
    return response


@router.get("/{short_code}/raw", response_class=PlainTextResponse)
async def raw_paste(short_code: str, request: Request, db: Session = Depends(get_db)):
    paste = get_paste(db, short_code)
    if paste is None:
        raise HTTPException(status_code=404, detail="Paste not found or has expired.")
    if paste.password_hash and not _is_unlocked(request, short_code):
        raise HTTPException(status_code=403, detail="Password required.")
    return PlainTextResponse(content=paste.content, media_type="text/plain; charset=utf-8")


@router.get("/{short_code}/download")
async def download_paste(short_code: str, request: Request, db: Session = Depends(get_db)):
    paste = get_paste(db, short_code)
    if paste is None:
        raise HTTPException(status_code=404, detail="Paste not found or has expired.")
    if paste.password_hash and not _is_unlocked(request, short_code):
        raise HTTPException(status_code=403, detail="Password required.")
    ext_map = {
        "python": "py", "javascript": "js", "typescript": "ts", "go": "go",
        "rust": "rs", "java": "java", "cpp": "cpp", "c": "c", "html": "html",
        "css": "css", "json": "json", "bash": "sh", "sql": "sql",
        "yaml": "yaml", "toml": "toml", "markdown": "md", "ruby": "rb", "php": "php",
    }
    ext = ext_map.get(paste.language, "txt")
    filename = f"{short_code}.{ext}"
    return PlainTextResponse(
        content=paste.content,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── JSON API routes ────────────────────────────────────────────────────────────

@router.post("/api/pastes", response_model=PasteResponse)
async def api_create_paste(payload: PasteCreate, request: Request, db: Session = Depends(get_db)):
    paste = create_paste(
        db,
        content=payload.content,
        language=payload.language,
        title=payload.title,
        password=payload.password,
        expiry=payload.expiry if payload.expiry in EXPIRY_LABELS else "never",
    )
    data = PasteResponse(
        short_code=paste.short_code,
        title=paste.title,
        content=paste.content,
        language=paste.language,
        views=paste.views,
        created_at=paste.created_at,
        expires_at=paste.expires_at,
        is_protected=paste.password_hash is not None,
    )
    base = str(request.base_url).rstrip("/")
    return JSONResponse(content={**data.model_dump(mode="json"), "url": f"{base}/{paste.short_code}"})


@router.get("/api/pastes/{short_code}", response_model=PasteResponse)
async def api_get_paste(short_code: str, request: Request, db: Session = Depends(get_db)):
    paste = get_paste(db, short_code)
    if paste is None:
        raise HTTPException(status_code=404, detail="Paste not found or has expired.")
    if paste.password_hash and not _is_unlocked(request, short_code):
        raise HTTPException(status_code=403, detail="Password required.")
    return PasteResponse(
        short_code=paste.short_code,
        title=paste.title,
        content=paste.content,
        language=paste.language,
        views=paste.views,
        created_at=paste.created_at,
        expires_at=paste.expires_at,
        is_protected=paste.password_hash is not None,
    )
