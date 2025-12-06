"""
FamilyDocs Intelligence Hub - FastAPI Backend
Main application entry point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging

from config import settings
from api.routes import boards, documents, chat, modules, rag
from database.connection import init_db, close_db

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    # Startup
    logger.info("🚀 Starting FamilyDocs Intelligence Hub...")
    await init_db()
    logger.info("✅ Database connection established")
    logger.info(f"✅ vLLM endpoint: {settings.vllm_api_url}")
    logger.info(f"✅ PC Sync root: {settings.pc_sync_root}")

    yield

    # Shutdown
    logger.info("🛑 Shutting down FamilyDocs...")
    await close_db()
    logger.info("✅ Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="FamilyDocs Intelligence Hub",
    description="Board + Chat Hybrid System for Family Document Management",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Health Check
# ============================================================================


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "familydocs-backend",
            "version": "1.0.0",
        }
    )


@app.get("/api/status")
async def status():
    """Detailed status check"""
    return JSONResponse(
        content={
            "status": "operational",
            "services": {
                "database": "connected",  # TODO: Check actual DB connection
                "vllm": "connected",  # TODO: Check vLLM health
                "redis": "connected",  # TODO: Check Redis connection
            },
            "config": {
                "vllm_model": settings.vllm_model_name,
                "rag_enabled": settings.rag_enabled,
                "pc_sync_root": settings.pc_sync_root,
            },
        }
    )


# ============================================================================
# API Routes
# ============================================================================

# Board Management
app.include_router(boards.router, prefix="/api/boards", tags=["Boards"])

# Document Management
app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])

# Chat System
app.include_router(chat.router, prefix="/api/chat", tags=["Chat"])

# Smart Modules
app.include_router(modules.router, prefix="/api/modules", tags=["Modules"])

# RAG System
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"])


# ============================================================================
# Root Endpoint
# ============================================================================


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "FamilyDocs Intelligence Hub",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/health",
    }


# ============================================================================
# Error Handlers
# ============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower(),
    )
