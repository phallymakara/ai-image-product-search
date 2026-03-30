# AI Visual Product Search

## Overview

AI Visual Product Search is an application that allows users to upload or capture product images and automatically find similar products using AI.

The system leverages **Azure AI Vision** to analyze images (tags, objects, OCR) and matches them against a product catalog to return the top results.

---

## Objective

- Analyze uploaded product images
- Extract features (tags, objects, text)
- Match against product database
- Return top 3 similar products

## Business Use Cases

- Retail product lookup
- Warehouse inventory checking
- Distributor product verification
- Field sales product identification

## Tech Stack

- Frontend: Power Apps (Canvas App)
- Backend: FastAPI / Node.js
- AI Service: Azure AI Vision
- Storage: Azure Blob Storage
- Automation: Azure Function / Power Automate
- Database: Azure SQL / SharePoint / Dataverse

## Core Features

### 1. Image Upload

- Upload or capture product image
- Store in Azure Blob Storage

### 2. Image Analysis

- Detect objects
- Extract tags
- Perform OCR (text extraction)

### 3. Product Matching

- Compare tags + OCR with product catalog
- Rank results using similarity scoring

### 4. Result Display

- Show Top 3 similar products
- Display confidence score

### 5. Search History

- Store image + results for future reference

## Project Structure

```text
ai-visual-product-search/
│
├── backend/              # API (FastAPI / Node)
├── azure-functions/      # Blob trigger processing
├── frontend/             # Power App / UI
├── database/             # Product dataset
├── docs/                 # Documentation
└── README.md
```

## Getting Started

### 1. Clone Repository

```bash
git clone https://github.com/phallymakara/ai-visual-product-search.git
cd ai-visual-product-search
```

### 2. Setup Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 3. Configure Azure

- Create Azure Blob Storage
- Create Azure AI Vision resource
- (Optional) Create Azure Function for trigger

Update environment variables:

```env
AZURE_STORAGE_CONNECTION=your_connection_string
VISION_ENDPOINT=your_endpoint
VISION_KEY=your_key
```

### 4. Run Application

- Start backend server
- Upload image via API or Power App
- View results from `/result/{imageId}`

## Matching Logic (Simplified)

```text
Score =
  0.4 × tag similarity + 0.3 × OCR similarity + 0.3 × brand match
```

---

## Author

- PHALLY MAKARA

## All rights reserved.

Copyright (c) 2026 PHALLY MAKARA

- This project and all associated files are the intellectual property of PHALLY MAKARA and Team Member.
- Unauthorized use, reproduction, or distribution of this project is **strictly prohibited** and may result in legal action.
- For permission requests, please contact the author directly. Contact: phallymakara01@example.com
