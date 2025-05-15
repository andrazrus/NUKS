from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import uuid, subprocess, os, glob
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./videos.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class Video(Base):
    __tablename__ = "videos"
    id = Column(String, primary_key=True, index=True)
    url = Column(String)
    status = Column(String)
    filename = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

class VideoRequest(BaseModel):
    url: str

@app.post("/download")
def download_video(data: VideoRequest):
    db = SessionLocal()
    video_id = str(uuid.uuid4())
    video = Video(id=video_id, url=data.url, status="processing")
    db.add(video)
    db.commit()
    try:
        # Prenos MP3
        subprocess.run([
            "yt-dlp", "-x", "--audio-format", "mp3",
            "-o", f"/tmp/{video_id}-%(title).200s.%(ext)s", data.url
        ], check=True)

        matches = glob.glob(f"/tmp/{video_id}-*.mp3")
        if not matches:
            raise HTTPException(status_code=500, detail="MP3 not found")

        original_path = matches[0]
        original_filename = os.path.basename(original_path)

        # Odstrani UUID iz imena
        trimmed_filename = original_filename[len(video_id)+1:]  # odreži UUID in "-"
        new_path = f"/tmp/{trimmed_filename}"
        os.rename(original_path, new_path)

        # Posodobi bazo
        video.status = "ready"
        video.filename = trimmed_filename

    except subprocess.CalledProcessError:
        video.status = "error"
        db.commit()
        db.close()
        raise HTTPException(status_code=500, detail="Download failed")

    db.commit()
    db.close()
    return {"file_id": video_id, "filename": trimmed_filename}

@app.get("/status/{file_id}")
def check_status(file_id: str):
    matches = glob.glob(f"/tmp/{file_id}-*.mp3")
    return {"ready": bool(matches)}

@app.get("/download/{file_id}")
def get_file(file_id: str):
    db = SessionLocal()
    video = db.query(Video).filter(Video.id == file_id).first()
    db.close()

    if not video or not video.filename:
        raise HTTPException(status_code=404, detail="File not found")

    path = os.path.join("/tmp", video.filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(path, media_type="audio/mpeg", filename=video.filename)

@app.delete("/delete/{file_id}")
def delete_file(file_id: str):
    db = SessionLocal()
    video = db.query(Video).filter(Video.id == file_id).first()
    if not video:
        db.close()
        raise HTTPException(status_code=404, detail="Video not found")

    path = os.path.join("/tmp", video.filename)
    try:
        if os.path.exists(path):
            os.remove(path)
        db.delete(video)
        db.commit()
        return {"message": "Deleted"}
    finally:
        db.close()

@app.get("/videos")
def list_videos():
    db = SessionLocal()
    videos = db.query(Video).all()
    db.close()
    return [{
        "id": v.id,
        "url": v.url,
        "status": v.status,
        "filename": v.filename,
        "timestamp": v.timestamp.isoformat()
    } for v in videos]
