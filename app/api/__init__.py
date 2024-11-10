from app.api.movies import router as movies_router
from app.api.reviews import router as reviews_router
from app.api.scraping import router as scraping_router

__all__ = ["movies_router", "reviews_router", "scraping_router"]