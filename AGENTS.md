# AGENTS.md

## Project Structure

```
ai-image-product-search/
├── backend/              # FastAPI backend (Python)
├── ai-product-frontend/  # React frontend (Vite)
└── azure-functions/      # Azure Functions blob trigger processor
```

## Dev Commands

**Backend:**
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend:**
```bash
cd ai-product-frontend
npm install
npm run dev
```

## Configuration

- Backend loads `.env` from `backend/.env` (see `.env.example`)
- Required env vars: `AZURE_STORAGE_CONNECTION`, `VISION_ENDPOINT`, `VISION_KEY`, `COSMOS_ENDPOINT`, `COSMOS_KEY`
- Frontend dev server proxies `/api/*` to `http://127.0.0.1:8000`

## Architecture Notes

- Backend uses **async** Cosmos DB client (`azure.cosmos.aio`) - all container operations are async
- **Partition keys**: Products use `/category`, SearchHistory uses `/userId`
- Search scoring: `0.4 * tag_score + 0.3 * brand_score + 0.3 * ocr_score` (adjusts weights dynamically if brands/OCR are missing)
- Azure Function (`azure-functions/process_image/`) is a separate blob trigger processor that auto-analyzes uploaded images

## Important Quirks

- Cosmos client has `connection_verify=False` to bypass macOS SSL certificate issues in dev
- Vision API v3.2 endpoint used: `/vision/v3.2/analyze?visualFeatures=Tags,Objects,Categories,Description,Brands`
- Image upload duplicates detected via SHA256 hash
- No test suite exists in this repo
