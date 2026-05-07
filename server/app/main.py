import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.invoice_routes import router as invoice_router
from app.config.settings import UPLOAD_DIR, OUTPUT_DIR

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# Ensure required directories exist
Path(UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Acuron Invoice Intelligence API",
    description=(
        "Processes invoice PDFs using Azure Document Intelligence. "
        "Extracts, validates, applies accounting rules, and exports to Excel."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow Next.js dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://acuron-ai-task.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(invoice_router)


@app.get("/", tags=["root"])
async def root():
    return {
        "message": "Acuron Invoice Intelligence API",
        "docs": "/docs",
        "health": "/api/invoices/health",
    }
