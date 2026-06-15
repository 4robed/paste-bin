# Pastebin – FastAPI Code Sharing Platform

## Overview
A lightweight code-sharing web app where users paste code, get a short shareable link, and optionally protect it with a password.

---

## Tech Stack

| Layer | Choice | Reason |
|---|---|---|
| Backend | FastAPI | Async, fast, auto docs |
| Database | SQLite + SQLAlchemy | Zero-setup, easy to swap to Postgres later |
| Templates | Jinja2 | Server-rendered, no JS framework needed |
| Short IDs | `nanoid` (via `nanoid` pypi) | URL-safe, short, collision-resistant |
| Password hashing | `passlib[bcrypt]` | Industry standard |
| Syntax highlight | `highlight.js` (CDN) | Client-side, 190+ languages, no build step |
| Styling | Tailwind CSS (CDN) | Utility-first, no build step |

---

## Project Structure

```
pastebin/
├── main.py                  # FastAPI app entrypoint
├── database.py              # SQLAlchemy engine + session
├── models.py                # ORM model: Paste
├── schemas.py               # Pydantic request/response models
├── crud.py                  # DB operations
├── utils.py                 # Short code generation, password helpers
├── routers/
│   └── pastes.py            # All paste routes
├── templates/
│   ├── base.html            # Layout shell
│   ├── index.html           # Create paste form
│   ├── paste.html           # View paste
│   └── password.html        # Password gate
├── static/
│   └── style.css            # Custom overrides (minimal)
├── requirements.txt
└── .env                     # SECRET_KEY, DATABASE_URL
```

---

## Data Model

```python
class Paste(Base):
    id           : int          # PK, autoincrement
    short_code   : str          # 8-char nanoid, unique, indexed
    title        : str | None   # optional display title
    content      : str          # raw code text
    language     : str          # e.g. "python", "javascript", "plain"
    password_hash: str | None   # bcrypt hash, None = public
    views        : int          # hit counter
    created_at   : datetime
    expires_at   : datetime | None  # None = never expires
```

---

## Routes

### HTML (browser)

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Create-paste form |
| `POST` | `/` | Submit paste → redirect to `/{code}` |
| `GET` | `/{code}` | View paste (or password gate if protected) |
| `POST` | `/{code}/unlock` | Submit password, set session cookie, redirect to `/{code}` |

### API (JSON, prefix `/api`)

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/pastes` | Create paste, returns `{short_code, url}` |
| `GET` | `/api/pastes/{code}` | Get paste metadata + content (if unlocked) |

---

## Page Designs

### `/` – Create Paste
- Title field (optional)
- Language dropdown (Python, JS, TS, Go, Rust, SQL, HTML, Plain Text, …)
- Large textarea for code
- Password field (optional, placeholder: "Leave blank for public")
- Expiry dropdown: Never / 1 hour / 1 day / 7 days / 30 days
- **Submit** button → POST → redirect

### `/{code}` – View Paste
- Paste title + language badge
- Copy-to-clipboard button
- View counter
- `highlight.js` rendered code block
- "New Paste" button

### `/{code}` (password-protected, not unlocked)
- Simple centered card
- Password input + **Unlock** button
- Wrong password → inline error

---

## Key Implementation Details

### Short Code Generation
```python
# utils.py
from nanoid import generate
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

def make_short_code() -> str:
    return generate(ALPHABET, 8)  # ~218 trillion combinations
```

### Password Flow
- On create: `passlib` hashes the password, stored in `password_hash`
- On view: if `password_hash` is set, show gate; check session cookie for prior unlock
- On unlock: verify with `passlib.verify`, set signed session cookie (`itsdangerous`)

### Session Cookie (no login/accounts needed)
- Use `itsdangerous.URLSafeTimedSerializer` signed with `SECRET_KEY`
- Cookie value: `{short_code}:unlocked`, expires with browser session

---

## Dependencies (`requirements.txt`)

```
fastapi
uvicorn[standard]
sqlalchemy
jinja2
python-multipart      # form parsing
passlib[bcrypt]
nanoid
itsdangerous          # signed cookies
python-dotenv
```

---

## Implementation Order

1. [ ] Project scaffold + `requirements.txt`
2. [ ] `database.py` + `models.py` — SQLite setup, table creation
3. [ ] `utils.py` — short code + password helpers
4. [ ] `crud.py` — create / get paste operations
5. [ ] `routers/pastes.py` — HTML routes
6. [ ] Jinja2 templates — index, paste, password
7. [ ] `/api` JSON routes
8. [ ] Expiry enforcement (delete or 410 on expired pastes)
9. [ ] Polish: copy button, view counter, language auto-detect hint

---

## Out of Scope (v1)
- User accounts / auth
- Edit / delete own paste
- Paste listing / search
- Rate limiting
- File uploads
