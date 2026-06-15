import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import Base, engine
from routers.pastes import router

os.makedirs("data", exist_ok=True)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Pastebin", docs_url="/api/docs", redoc_url=None)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)


@app.exception_handler(404)
async def not_found(request: Request, exc):
    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status": 404, "detail": exc.detail},
        status_code=404,
    )


@app.exception_handler(403)
async def forbidden(request: Request, exc):
    templates = Jinja2Templates(directory="templates")
    return templates.TemplateResponse(
        "error.html",
        {"request": request, "status": 403, "detail": exc.detail},
        status_code=403,
    )
