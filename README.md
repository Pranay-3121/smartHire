# Resume Ranker — AI Hiring Platform

Enterprise-grade AI resume ranking system powered by Llama 3, LangGraph, ChromaDB, FastAPI, and React.

---

Group 1 - 
    Pranay
    Niranjan patil
    Adarsh
    Vivek Neharkar
    Omkar Halpatrao
    Nandita 
## Architecture

```
JD Text → JD Reader Agent → Job Profile
Resumes → Resume Parser Agent → Candidate Profiles
                                      ↓
                          Ranking Agent (Weighted Scoring + Semantic)
                                      ↓
                          Reasoning Agent (LLM Explanations)
                                      ↓
                          Ranked Results + Export
```

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- [Ollama](https://ollama.ai) running locally with Llama 3
- Tesseract OCR (optional, for scanned PDFs)

### Install Ollama + Llama 3

```bash
# Install Ollama from https://ollama.ai
ollama pull llama3
ollama serve
```

### Install Tesseract (optional)

- Windows: https://github.com/UB-Mannheim/tesseract/wiki
- macOS: `brew install tesseract`
- Linux: `sudo apt install tesseract-ocr`

---

## Backend Setup

```bash
cd resume_ranker

# Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env .env.local   # Edit as needed

# Run backend
uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8000
```

API docs available at: http://localhost:8000/docs

---

## Frontend Setup

```bash
cd resume_ranker/frontend

npm install
npm run dev
```

Frontend available at: http://localhost:5173

---

## Running Tests

```bash
cd resume_ranker
pytest
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | System health check |
| POST | `/analyze-job` | Parse job description |
| POST | `/upload-resumes?run_id=...` | Upload resume files |
| POST | `/rank` | Run AI ranking pipeline |
| GET | `/results/{run_id}` | Get ranked results |
| GET | `/download/{run_id}?format=csv\|json\|report` | Download exports |

---

## Scoring Weights by Role

| Role | Experience | Projects | Certifications | Education | Soft Skills |
|------|-----------|----------|----------------|-----------|-------------|
| Engineering | 35% | 40% | 10% | 10% | 5% |
| Compliance | 35% | 15% | 35% | 10% | 5% |
| Fresher | 10% | 35% | 15% | 35% | 5% |
| Data Science | 30% | 40% | 15% | 10% | 5% |
| Management | 45% | 20% | 10% | 10% | 15% |
| General | 40% | 30% | 15% | 10% | 5% |

---

## Edge Cases Handled

- Duplicate resumes (SHA-256 hash detection)
- Scanned PDFs (OCR fallback via pytesseract)
- Password-protected PDFs (graceful failure)
- Keyword stuffing (penalty applied)
- Job hopping (penalty applied)
- Career gaps (penalty applied)
- Overqualified candidates (penalty applied)
- Multilingual resumes (flagged)
- Missing sections (partial parse with confidence score)
- Tie-breaking (experience + certifications + projects)

---

## Project Structure

```
resume_ranker/
├── backend/
│   ├── core/          # Config, logging, constants, state
│   ├── schemas/       # Pydantic models
│   ├── tools/         # Parsers, scorer, exporter, edge handler
│   ├── agents/        # JD reader, resume parser, ranker, reasoner
│   ├── workflows/     # LangGraph pipeline
│   ├── services/      # Ollama client, ChromaDB, storage
│   ├── api/           # FastAPI app
│   └── tests/         # pytest test suite
├── frontend/
│   └── src/
│       ├── pages/     # Dashboard, Results, CandidateDetail
│       ├── components/ # Cards, badges, bars, dropzone
│       ├── hooks/     # usePipeline
│       └── services/  # API client
├── requirements.txt
├── .env
└── README.md
```
