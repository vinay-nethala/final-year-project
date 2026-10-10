from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.db.session import engine, Base
from app.api.endpoints import api_router
from app.services.pricing_service import pricing_service

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create DB tables automatically on startup
    Base.metadata.create_all(bind=engine)
    # Check/load RL policy
    pricing_service.load_model()
    yield

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API and Q-Learning Reinforcement Learning Engine for Perishable Retail Discounting.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Middleware configured strictly for allowed development origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "message": "Welcome to AI-Based Expiry-Aware Dynamic Discount System API",
        "docs": "/docs",
        "health": f"{settings.API_V1_STR}/health"
    }
