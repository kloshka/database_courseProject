from fastapi import FastAPI
from app.routers import titles, users, library, analytics, batch, reviews

app = FastAPI(
    title="Anime Library API",
    description="",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {
        "message": "Anime Library API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "titles": "/titles",
            "users": "/users",
            "library": "/library",
            "analytics": "/analytics",
            "batch_import": "/api/batch-import/titles",
            "reviews": "/reviews"
        }
    }

app.include_router(titles.router)
app.include_router(users.router)
app.include_router(library.router)
app.include_router(analytics.router)
app.include_router(batch.router)
app.include_router(reviews.router)
