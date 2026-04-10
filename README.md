# RAG Knowledge Assistant — HPS Frontend 🤖

A React-based frontend for an AI-powered internal knowledge assistant 
built during my internship at **HPS (Hightech Payment Systems)**.

## What It Does

Provides a clean chat interface for employees to query internal 
documentation using a Retrieval-Augmented Generation (RAG) system. 
Instead of searching through manuals manually, employees ask questions 
in natural language and get instant, accurate answers sourced from 
internal documents.

## Architecture
User (React UI)  →  FastAPI Backend  →  Ollama (LLM)
↓
Vector Database
(Document Embeddings)

## Tech Stack

**Frontend (this repo)**
- React.js
- JavaScript / CSS
- REST API integration

**Backend (separate repo)**
- FastAPI
- Ollama (local LLM)
- Docker
- Python

## Getting Started

### Prerequisites
- Node.js 16+
- Backend service running (FastAPI + Ollama)

### Installation

```bash
# Clone the repo
git clone https://github.com/mamdouh-abdelmoughit/RAG_hps.git
cd RAG_hps

# Install dependencies
npm install

# Start development server
npm start
```

Open [http://localhost:3000](http://localhost:3000) to view in browser.

### Build for Production

```bash
npm run build
```

## Context

Built as part of my end-of-study internship at HPS to solve a real 
internal problem: engineers spending too much time searching through 
technical documentation. The RAG system indexes internal docs and 
makes them queryable through a simple chat interface.

## Related
- [BioSwitch — Biometric Payment System](https://github.com/mamdouh-abdelmoughit/bioswitch)
- [Click-to-Pay Solution](https://github.com/mamdouh-abdelmoughit/clicktopay)
