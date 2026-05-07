# Document Intelligence System

AI-powered invoice processing portal built for Acuron.

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI + Azure Document Intelligence |
| Frontend | Next.js 15 + Tailwind CSS + shadcn/ui |
| AI | Azure prebuilt-invoice model |
| Export | openpyxl (styled Excel) |

## Quick Start

### Option 1: Use the batch file (Windows)
```
start.bat
```

### Option 2: Manual

**Backend:**
```bash
cd server
acuron_env\Scripts\activate
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd client
npm run dev
```

## URLs

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs

## Environment Variables

`server/.env`:
```
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=<your endpoint>
AZURE_DOCUMENT_INTELLIGENCE_KEY=<your key>
```

`client/.env.local`:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Backend Structure

```
server/
├── acuron_env/          # Python virtual environment
├── app/
│   ├── main.py          # FastAPI app + CORS
│   ├── routes/
│   │   └── invoice_routes.py   # /api/invoices/* endpoints
│   ├── services/
│   │   ├── azure_di_service.py # Azure DI integration
│   │   ├── validation_service.py # GSTIN, GST, duplicate checks
│   │   ├── rules_engine.py     # GL codes, vendor mapping, TDS
│   │   └── excel_service.py    # Styled Excel export
│   ├── schemas/
│   │   └── invoice.py          # Pydantic models
│   └── config/
│       └── settings.py         # Env-based config
├── uploads/             # Uploaded invoice files
├── outputs/             # Generated outputs
├── requirements.txt
└── .env
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/invoices/upload` | Process invoices, return JSON |
| POST | `/api/invoices/export-excel` | Process + download Excel |
| GET | `/api/invoices/health` | Health check |
