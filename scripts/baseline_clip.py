#!/usr/bin/env python3
"""
Smoke-test CLIP on GPU (or CPU): embed one image and compare to a fixed text query.
Run from repo root after activating the conda env:

  python scripts/baseline_clip.py path/to/image.jpg
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

MODEL_ID = "openai/clip-vit-base-patch32"
TEXT_QUERY = "a photo of a dog"


def main() -> None:
    parser = argparse.ArgumentParser(description="CLIP baseline GPU/CPU check")
    parser.add_argument("image", type=Path, help="Path to an image file")
    args = parser.parse_args()
    if not args.image.is_file():
        raise SystemExit(f"Not a file: {args.image}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device.type != "cuda":
        print("Warning: CUDA not available; using CPU.")

    processor = CLIPProcessor.from_pretrained(MODEL_ID)
    model = CLIPModel.from_pretrained(MODEL_ID).to(device)
    model.eval()

    image = Image.open(args.image).convert("RGB")

    t0 = time.perf_counter()
    with torch.inference_mode():
        img_in = processor(images=[image], return_tensors="pt", padding=True)
        img_in = {k: v.to(device) for k, v in img_in.items()}
        txt_in = processor(text=[TEXT_QUERY], return_tensors="pt", padding=True)
        txt_in = {k: v.to(device) for k, v in txt_in.items()}
        img_feat = model.get_image_features(**img_in)
        txt_feat = model.get_text_features(**txt_in)
        img_feat = img_feat / img_feat.norm(dim=-1, keepdim=True)
        txt_feat = txt_feat / txt_feat.norm(dim=-1, keepdim=True)
        sim = (img_feat @ txt_feat.T).squeeze().item()
    elapsed = time.perf_counter() - t0

    print(f"Device: {device}")
    print(f"Model: {MODEL_ID}")
    print(f"Text:  {TEXT_QUERY!r}")
    print(f"Cosine similarity (image vs text): {sim:.4f}")
    print(f"Wall time (single pair, incl. preprocess): {elapsed*1000:.1f} ms")


if __name__ == "__main__":
    main()
