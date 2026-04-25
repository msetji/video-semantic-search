import os
import sys

print("Loading CLIP...")
from app.services.clip_service import get_clip_service
print("Calling get_clip_service()...")
clip = get_clip_service()
print("CLIP loaded successfully!")

print("Loading FAISS store...")
from app.services.faiss_store import get_faiss_store
print("Calling get_faiss_store()...")
store = get_faiss_store()
print("FAISS loaded successfully!")

print("All done!")
