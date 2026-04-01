# AI Visual Product Search

> Instantly identify and match products using AI-powered image analysis.

---

## Overview

**AI Visual Product Search** lets users upload or capture a product image and automatically find the most similar products from a catalog. The system uses **Azure AI Vision** to extract tags, detect objects, and perform OCR — then ranks results using a weighted similarity score.

## Business Use Cases

- 🛒 Retail product lookup
- 🏭 Warehouse inventory checking
- 📦 Distributor product verification
- 🧑‍💼 Field sales product identification

## Tech Stack

| Layer      | Technology                         |
| ---------- | ---------------------------------- |
| Frontend   | Power Apps (Canvas App)            |
| Backend    | FastAPI / Node.js                  |
| AI Service | Azure AI Vision                    |
| Storage    | Azure Blob Storage                 |
| Automation | Azure Functions / Power Automate   |
| Database   | Azure SQL / SharePoint / Dataverse |

## Core Features

### 1. Image Upload

Upload or capture a product image and store it in Azure Blob Storage.

### 2. Image Analysis

- Detect objects
- Extract tags
- Perform OCR (text extraction)

### 3. Product Matching

Compare extracted tags and OCR text against the product catalog, then rank results using similarity scoring.

### 4. Result Display

Show the **top 3** similar products with confidence scores.

### 5. Search History

Store images and results for future reference and audit trails.

## Matching Logic

```
Score = (0.4 × tag similarity) + (0.3 × OCR similarity) + (0.3 × brand match)
```

## Project Structure

```
ai-visual-product-search/
│
├── backend/              # API (FastAPI / Node.js)
├── azure-functions/      # Blob trigger processing
├── frontend/             # Power App / UI
├── database/             # Product dataset
├── docs/                 # Documentation
└── README.md
```

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/phallymakara/ai-visual-product-search.git
cd ai-visual-product-search
```

### 2. Set Up the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Configure Azure

Create the following Azure resources:

- Azure Blob Storage
- Azure AI Vision resource
- Azure Function _(optional, for blob trigger)_

Then set your environment variables:

```env
AZURE_STORAGE_CONNECTION=your_connection_string
VISION_ENDPOINT=your_endpoint
VISION_KEY=your_key
```

### 4. Run the Application

1. Start the backend server
2. Upload an image via the API or Power App
3. View results at `/result/{imageId}`

## Author

**PHALLY MAKARA**

---

## License

Copyright © 2026 PHALLY MAKARA. All rights reserved.

This project and all associated files are the intellectual property of PHALLY MAKARA and team members. Unauthorized use, reproduction, or distribution is **strictly prohibited** and may result in legal action.

For permission requests, contact: phallymakara01@gmail.com
