"""Local-first HTTP API and static JavaScript UI. No secret is sent to the browser."""
from pathlib import Path
from functools import lru_cache
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from .service import ResearchService


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    use_llm: bool = False


def create_app(service=None):
    app = FastAPI(title='Kabyle Atlas — Research Agents', version='0.2.0')
    @lru_cache(maxsize=1)
    def get_service():
        return service or ResearchService()

    @app.get('/health')
    def health():
        get_service()
        return {'status': 'ok'}

    @app.get('/api/status')
    def status():
        return get_service().info()

    @app.post('/api/ask')
    def ask(body: AskRequest):
        try:
            return get_service().ask(body.question, body.use_llm)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    @app.get('/api/fiches/{fiche_id}')
    def fiche(fiche_id: str):
        result = get_service().get_fiche(fiche_id)
        if result is None:
            raise HTTPException(404, 'Fiche not found or not validated')
        return result

    static = Path(__file__).parent / 'static'
    @app.get('/')
    def home():
        return FileResponse(static / 'index.html')
    app.mount('/static', StaticFiles(directory=static), name='static')
    return app


app = create_app()
