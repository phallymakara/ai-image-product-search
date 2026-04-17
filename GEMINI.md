# GEMINI.md

## Project Overview
**AI Visual Product Search** is a full-stack application that enables users to identify and match products using AI-powered image analysis. It leverages Azure AI Vision for object detection, tag extraction, and OCR, providing a weighted similarity score to rank product matches from a catalog.

### Tech Stack
- **Frontend:** React (Vite) with TanStack Query and Axios.
- **Backend:** FastAPI (Python) with Pydantic for settings and data validation.
- **AI Services:** Azure AI Vision (Analyze & OCR).
- **Storage:** Azure Blob Storage for image hosting.
- **Database:** Azure Cosmos DB for product metadata and search history.
- **Background Processing:** Azure Functions (Python) for asynchronous image enhancement.

## Directory Structure
- `ai-product-frontend/`: React application.
- `backend/`: FastAPI application.
    - `core/`: Configuration and settings.
    - `database/`: Cosmos DB client and initialization.
    - `routers/`: API endpoints (Upload, Search, Products).
    - `services/`: Business logic (Matching, Vision, Storage).
- `azure-functions/`: Blob-triggered function for processing uploaded images.

## Building and Running

### Prerequisites
- Python 3.9+
- Node.js & npm
- Azure Account (Blob Storage, Cosmos DB, AI Vision)

### Backend Setup
1. Navigate to the `backend/` directory.
2. Create a virtual environment: `python -m venv venv`.
3. Activate the environment: `source venv/bin/activate` (macOS/Linux) or `venv\Scripts\activate` (Windows).
4. Install dependencies: `pip install -r requirements.txt`.
5. Configure `.env` file (see `backend/core/config.py` for required variables).
6. Run the server: `uvicorn main:app --reload`.

### Frontend Setup
1. Navigate to the `ai-product-frontend/` directory.
2. Install dependencies: `npm install`.
3. Run the development server: `npm run dev`.
4. The frontend proxies API calls to `http://127.0.0.1:8000` by default.

### Azure Functions Setup
1. Navigate to the `azure-functions/` directory.
2. Install dependencies: `pip install -r requirements.txt`.
3. Configure `.env` file with Azure credentials.
4. Run locally using Azure Functions Core Tools: `func start`.

## Development Conventions
- **API Architecture:** RESTful endpoints using FastAPI routers.
- **State Management:** React Query for server-state synchronization.
- **Matching Logic:** Uses fuzzy string matching (`thefuzz`) with a weighted scoring system:
    - `Score = (Tag Similarity) + (OCR Similarity) + (Brand Match)`.
    - Weights are adjusted dynamically based on available data (e.g., if no OCR text is detected).
- **Naming Conventions:** 
    - Python: `snake_case` for functions and variables, `PascalCase` for classes.
    - JavaScript/React: `camelCase` for variables and functions, `PascalCase` for components.
- **Error Handling:** Centralized logging and appropriate HTTP status codes in the backend.

## Key Files
- `backend/main.py`: Main entry point and lifecycle management.
- `backend/services/matching.py`: Core similarity scoring algorithms.
- `backend/routers/search.py`: Implementation of image and text-based search.
- `ai-product-frontend/src/api/searchApi.js`: Frontend hooks for interacting with search endpoints.
- `azure-functions/process_image/__init__.py`: Background logic for AI-driven product metadata enhancement.
