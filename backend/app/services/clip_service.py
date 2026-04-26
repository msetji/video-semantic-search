from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
import torch
from PIL import Image
from transformers import CLIPModel, CLIPProcessor

from app.config import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

_CLIP: "CLIPService | None" = None


class CLIPService:
    def __init__(self, model_id: str | None = None) -> None:
        mid = model_id or settings.clip_model_id
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info("Loading CLIP model %s on %s", mid, self.device)
        if self.device.type != "cuda":
            logger.warning("CUDA not available — CLIP running on CPU, performance will be slower.")
        self.processor = CLIPProcessor.from_pretrained(mid)
        self.model = CLIPModel.from_pretrained(mid, use_safetensors=True).to(self.device)
        self.model.eval()
        hidden = self.model.config.projection_dim
        self.embedding_dim: int = int(hidden)
        fp16 = self.device.type == "cuda"
        logger.info(
            "CLIP ready — model=%s embedding_dim=%d device=%s fp16_autocast=%s",
            mid, self.embedding_dim, self.device, fp16,
        )

    @torch.inference_mode()
    def encode_preprocessed(self, inputs: dict[str, "torch.Tensor"]) -> np.ndarray:
        inputs = {k: v.to(self.device, non_blocking=True) for k, v in inputs.items()}
        with torch.autocast(self.device.type, dtype=torch.float16, enabled=self.device.type == "cuda"):
            feats = self.model.get_image_features(**inputs)
        if not isinstance(feats, torch.Tensor):
            feats = getattr(feats, "pooler_output", feats)
            if not isinstance(feats, torch.Tensor):
                feats = feats[1]
        feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.cpu().numpy().astype(np.float32)

    @torch.inference_mode()
    def encode_images(self, images: list[Image.Image], batch_size: int = 8) -> np.ndarray:
        out: list[np.ndarray] = []
        for i in range(0, len(images), batch_size):
            batch = images[i : i + batch_size]
            inputs = self.processor(images=batch, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            feats = self.model.get_image_features(**inputs)
            if not isinstance(feats, torch.Tensor):
                feats = getattr(feats, "pooler_output", feats)
                if not isinstance(feats, torch.Tensor):
                    feats = feats[1] # tuple fallback
            feats = feats / feats.norm(dim=-1, keepdim=True)
            out.append(feats.cpu().numpy().astype(np.float32))
        if not out:
            return np.zeros((0, self.embedding_dim), dtype=np.float32)
        return np.vstack(out)

    @torch.inference_mode()
    def encode_text(self, texts: list[str]) -> np.ndarray:
        inputs = self.processor(text=texts, return_tensors="pt", padding=True)
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        feats = self.model.get_text_features(**inputs)
        if not isinstance(feats, torch.Tensor):
            feats = getattr(feats, "pooler_output", feats)
            if not isinstance(feats, torch.Tensor):
                feats = feats[1] # tuple fallback
        feats = feats / feats.norm(dim=-1, keepdim=True)
        return feats.cpu().numpy().astype(np.float32)


def get_clip_service() -> CLIPService:
    global _CLIP
    if _CLIP is None:
        _CLIP = CLIPService()
    return _CLIP
