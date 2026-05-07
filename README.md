# Acuron Invoice Intelligence System

A robust, AI-powered invoice processing platform designed to extract, validate, and map accounting data from vendor invoices. This system leverages Azure Document Intelligence with a custom intelligence layer specialized for the Indian market.

## Technology Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python 3.11) |
| Frontend | Next.js 15 (React, TypeScript, Tailwind CSS) |
| AI Engine | Azure Document Intelligence (Prebuilt-Invoice Model) |
| Reporting | ReportLab (Complex PDF Generation) |
| Containerization | Docker |
| Deployment | Railway (Backend), Vercel (Frontend) |

## Advanced Extraction Features

### 1. Indian Numbering System Support
The system is specialized for the Indian market, correctly handling Lakhs and Crores (e.g., 10,93,877.00). It avoids the common truncation errors found in standard AI models by using a format-agnostic extraction layer.

### 2. Math-Based Self-Correction
To ensure 100% data integrity, the backend performs real-time math verification. It scans the entire document OCR for currency values and identifies math triplets (Taxable Amount + GST = Total Amount). This allows the system to override AI mis-mappings or decimal errors.

### 3. Comprehensive Validation
- GSTIN verification (format and entity type).
- GST calculation cross-checks.
- Duplicate invoice detection based on vendor and invoice number.
- Automatic GL Account and Vendor Code mapping.

## Setup and Installation

### Environment Configuration

Create a `server/.env` file:
```text
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=your_endpoint
AZURE_DOCUMENT_INTELLIGENCE_KEY=your_key
```

### Local Development

#### Using Docker (Recommended)
Build and run the backend container:
```bash
cd server
docker build -t acuron-backend .
docker run -p 8000:8000 --env-file .env acuron-backend
```

#### Manual Startup
1. **Backend**:
   ```bash
   cd server
   python -m venv acuron_env
   source acuron_env/bin/activate  # .\acuron_env\Scripts\activate on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

2. **Frontend**:
   ```bash
   cd client
   npm install
   npm run dev
   ```

## Project Structure

### Backend (server/)
- `app/main.py`: Application entry point and CORS configuration.
- `app/services/azure_di_service.py`: Core logic for AI extraction and math verification.
- `app/services/pdf_service.py`: PDF report generation with detailed mapping views.
- `app/services/rules_engine.py`: ERP-specific mapping logic (GL codes, Acc Periods).
- `app/services/validation_service.py`: Logic for GST and duplicate checks.

### Frontend (client/)
- `app/page.tsx`: Unified dashboard for upload and results.
- `components/ResultsTable.tsx`: Detailed UI for viewing extracted and mapped data.
- `services/invoiceApi.ts`: API integration layer.

## Production URLs

- **Frontend**: https://acuron-ai-task.vercel.app/
- **Backend API**: https://acuronaitask-production.up.railway.app/

## API Documentation

Interactive Swagger documentation is available at the `/docs` endpoint of the backend service.
