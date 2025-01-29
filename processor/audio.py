from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from pathlib import Path
from processor.audio import AudioProcessor

app = FastAPI(title="Sur API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create required directories
UPLOAD_DIR = Path("uploads")
PROCESSED_DIR = Path("processed")
UPLOAD_DIR.mkdir(exist_ok=True)
PROCESSED_DIR.mkdir(exist_ok=True)

# Initialize audio processor
processor = AudioProcessor()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Sur API is running"}

@app.post("/upload")
async def upload_file(file: UploadFile):
    # Validate file type
    if not file.filename.lower().endswith(('.mp3', '.wav', '.flac', '.m4a', '.ogg')):
        raise HTTPException(400, "Unsupported file format")
    
    try:
        # Save the uploaded file
        file_path = UPLOAD_DIR / file.filename
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Process the audio file
        result = await processor.process_audio(file_path, PROCESSED_DIR)
        
        # Clean up upload
        os.remove(file_path)
        
        return {
            "filename": file.filename,
            "status": "success",
            "job_id": result["id"],
            "stems": result["stems"]
        }
    except Exception as e:
        raise HTTPException(500, f"Processing failed: {str(e)}")

@app.get("/download/{job_id}/{stem}")
async def download_stem(job_id: str, stem: str):
    stem_path = PROCESSED_DIR / job_id / f"{stem}.wav"
    if not stem_path.exists():
        raise HTTPException(404, "Stem file not found")
    return FileResponse(stem_path)