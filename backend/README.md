# Sur Backend

Basic FastAPI server for audio processing.

## Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the server:
```bash
uvicorn main:app --reload --port 5000
```

## API Endpoints

- GET /health - Health check
- POST /upload - Upload audio file
- GET /status/{job_id} - Check processing status