from fastapi import FastAPI, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import os
import subprocess
import shutil
import uuid
from pathlib import Path
from processor.audio_processor import AudioProcessor

app = FastAPI(title="Sur API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "Content-Length", "Content-Type"]
)

BASE_DIR = Path(__file__).parent.absolute()
UPLOAD_DIR = BASE_DIR / "uploads"
PROCESSED_DIR = BASE_DIR / "processed"
DEMUCS_OUTPUT_DIR = BASE_DIR / "separated"

# Initialize the audio processor
audio_processor = AudioProcessor()

for dir_path in [UPLOAD_DIR, PROCESSED_DIR, DEMUCS_OUTPUT_DIR]:
    dir_path.mkdir(exist_ok=True, parents=True, mode=0o755)
    print(f"Directory created/verified: {dir_path}")

app.mount("/stems", StaticFiles(directory=str(PROCESSED_DIR)), name="stems")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.post("/upload")
async def upload_file(file: UploadFile):
    if not file.filename.lower().endswith(('.mp3', '.wav', '.flac', '.m4a', '.ogg')):
        raise HTTPException(400, "Unsupported file format")
    
    try:
        job_id = str(uuid.uuid4())
        job_dir = PROCESSED_DIR / job_id
        job_dir.mkdir(exist_ok=True, mode=0o755)
        print(f"Created job directory: {job_dir}")
        
        safe_filename = file.filename.replace(" ", "_")
        file_path = UPLOAD_DIR / safe_filename
        
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                buffer.write(content)
            print(f"Saved uploaded file to: {file_path}")
            
            # First pass: Split vocals/instrumental
            subprocess.run([
                "python3", "-m", "demucs.separate",
                "--two-stems=vocals",
                "-n", "htdemucs",
                str(file_path)
            ], check=True)
            
            # Second pass: Split drums/bass/other
            subprocess.run([
                "python3", "-m", "demucs.separate",
                "-n", "htdemucs",
                str(file_path)
            ], check=True)
            
            # Move and rename stems
            source_dir = DEMUCS_OUTPUT_DIR / "htdemucs" / file_path.stem
            
            stems = {}
            stem_mapping = {
                'vocals': 'vocals',    # Keep as vocals
                'drums': 'tabla',      # Indian drums
                'bass': 'bass',        # Keep as bass
                'other': 'other'       # Keep other and use for additional stems
            }
            
            # Process main stems
            for stem_file in source_dir.glob("*.wav"):
                stem_name = stem_file.stem.lower()
                if stem_name in stem_mapping:
                    new_name = stem_mapping[stem_name]
                    new_path = job_dir / f"{new_name}.wav"
                    shutil.copy(str(stem_file), str(new_path))
                    stems[new_name] = f"/stems/{job_id}/{new_name}.wav"
            
            # Create additional stems from 'other'
            if 'other' in stems:
                other_path = job_dir / "other.wav"
                
                # Map additional Indian instruments
                additional_stems = {
                    'sitar': 'sitar.wav',
                    'sarangi': 'sarangi.wav',  # Bowed string instrument
                    'tanpura': 'tanpura.wav',  # Drone instrument
                }
                
                # Process stems through AudioProcessor
                for stem_name, filename in additional_stems.items():
                    # Process through AudioProcessor with specific stem type
                    stem_path = job_dir / filename
                    shutil.copy(other_path, stem_path)  # Create initial copy
                    await audio_processor.process_audio(stem_path, job_dir, stem_type=stem_name)
                    stems[stem_name] = f"/stems/{job_id}/{filename}"
            
            if not stems:
                raise HTTPException(500, "No stems were generated")
            
            # Cleanup
            if file_path.exists():
                os.remove(file_path)
            if source_dir.exists():
                shutil.rmtree(source_dir)
            
            return {
                "status": "success",
                "job_id": job_id,
                "stems": stems,
                "message": "Processing complete"
            }
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Processing failed: {str(e)}"
            print(error_msg)
            raise HTTPException(500, error_msg)
            
    except Exception as e:
        error_msg = f"Upload failed: {str(e)}"
        print(error_msg)
        if 'file_path' in locals() and file_path.exists():
            os.remove(file_path)
        raise HTTPException(500, error_msg)
    finally:
        # Cleanup temporary files
        if 'source_dir' in locals() and source_dir.exists():
            shutil.rmtree(source_dir)
        if 'file_path' in locals() and file_path.exists():
            os.remove(file_path)