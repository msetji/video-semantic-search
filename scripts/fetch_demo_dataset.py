"""
Download a small, diverse image + video corpus for testing semantic search.

- Images: Wikimedia Commons, resolved with the site API (reliable 640px thumbnails).
- Video: short, widely used test clips (Google GTV public samples).

From the repo root, with your conda env active:
  python scripts/fetch_demo_dataset.py

Default output: data/demo_corpus/  (this tree is gitignored; only this script is committed.)
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote

import requests

# Repo root: scripts/ -> project root
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "data" / "demo_corpus"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "video-semantic-search-demo-fetch/1.0 (educational; +https://github.com/)"


# Direct URLs hand-checked with this script's User-Agent. CLIP still embeds raw pixels; text is for
# your report and the suggested_queries file.
_IMAGES: list[dict[str, Any]] = [
    {
        "relpath": "images/00_cat.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3a/Cat03.jpg/480px-Cat03.jpg",
        "description": "A tabby cat lying down",
        "suggested_queries": ["a cat resting", "tabby feline on furniture"],
    },
    {
        "relpath": "images/01_dog.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/26/YellowLabradorLooking_new.jpg/500px-YellowLabradorLooking_new.jpg",
        "description": "A yellow Labrador retriever",
        "suggested_queries": ["a yellow dog", "labrador retriever portrait"],
    },
    {
        "relpath": "images/02_apple.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Red_Apple.jpg/400px-Red_Apple.jpg",
        "description": "A red apple on a white background",
        "suggested_queries": ["red apple", "fresh fruit"],
    },
    {
        "relpath": "images/03_beach.jpg",
        "commons_file": "Rügen, Beach at Sellin -- 2009 -- 1173.jpg",
        "description": "Baltic beach: pier and water at Sellin, Rügen",
        "suggested_queries": ["beach and sea", "wooden pier and waves on the shore"],
    },
    {
        "relpath": "images/04_car.jpg",
        "commons_file": "BMW G60 520d 1X7A1585.jpg",
        "description": "A modern BMW 5 Series sedan (front three-quarter view)",
        "suggested_queries": ["BMW car front view on asphalt", "silver executive sedan"],
    },
    {
        "relpath": "images/05_airplane.jpg",
        "commons_file": "Airbus A380-800 Takeoff (7234017116) (5).jpg",
        "description": "A large jet (Airbus A380) during takeoff",
        "suggested_queries": ["airplane takeoff on runway", "large passenger jet lifting off"],
    },
    {
        "relpath": "images/06_city.jpg",
        "commons_file": "View of Empire State Building from Rockefeller Center New York City dllu.jpg",
        "description": "New York City view with the Empire State Building",
        "suggested_queries": ["empire state building and city skyline", "new york skyscrapers"],
    },
    {
        "relpath": "images/07_flower.jpg",
        "commons_file": "Bee on a tulip biene auf einer tulpe.jpg",
        "description": "A bee on a red tulip flower",
        "suggested_queries": ["tulip and bee on petals", "red spring flower with insect"],
    },
    {
        "relpath": "images/08_sushi.jpg",
        "commons_file": "Nigiri Sushi (26478725732).jpg",
        "description": "Nigiri sushi on a plate",
        "suggested_queries": ["sushi nigiri on a plate", "japanese food rice and fish"],
    },
    {
        "relpath": "images/09_football.jpg",
        "commons_file": "American Football EM 2014 - AUT-DEU - 401.JPG",
        "description": "American football match action (tackle near the end zone)",
        "suggested_queries": ["American football game tackle", "players in red and white uniforms on a field"],
    },
    {
        "relpath": "images/10_laptop.jpg",
        "commons_file": "Dell laptop keyboard.jpg",
        "description": "A laptop keyboard close-up (Dell)",
        "suggested_queries": ["laptop keyboard close-up", "black notebook computer keys"],
    },
    {
        "relpath": "images/11_mountain.jpg",
        "commons_file": "Helvellyn Striding Edge 360 Panorama, Lake District - June 09.jpg",
        "description": "Striding Edge ridge on Helvellyn, Lake District, UK",
        "suggested_queries": ["mountain ridge path with clouds", "rocky arête hiking trail in Britain"],
    },
    {
        "relpath": "images/12_bicycle.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/41/Left_side_of_Flying_Pigeon.jpg/640px-Left_side_of_Flying_Pigeon.jpg",
        "description": "A bicycle in an urban setting",
        "suggested_queries": ["a bicycle on the street", "biking in the city"],
    },
]
_VIDEOS: list[dict[str, Any]] = [
    {
        "relpath": "videos/sample_5s.mp4",
        "url": "https://download.samplelib.com/mp4/sample-5s.mp4",
        "description": "Short 5s stock MP4 (samplelib public test file)",
        "suggested_queries": ["short test video clip", "colorful video sample"],
    },
    {
        "relpath": "videos/sample_10s.mp4",
        "url": "https://download.samplelib.com/mp4/sample-10s.mp4",
        "description": "Short 10s stock MP4 (samplelib public test file)",
        "suggested_queries": ["ten second video sample", "motion and video test pattern"],
    },
]

_ASSETS: list[dict[str, Any]] = _IMAGES + _VIDEOS

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": USER_AGENT})


def _commons_thumb_url(commons_file: str, width: int = 640) -> str:
    """Resolve File: on Commons to a scaled image URL (small download)."""
    title = f"File:{commons_file}" if not commons_file.startswith("File:") else commons_file
    r = _SESSION.get(
        COMMONS_API,
        params={
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|mime",
            "iiurlwidth": str(width),
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    for _pid, p in pages.items():
        if p.get("missing"):
            raise RuntimeError(
                f"Commons has no file for title {title!r}. Check spelling and rename if needed."
            )
        for ii in p.get("imageinfo") or ():
            tu = ii.get("thumburl")
            if tu:
                return unquote(tu)  # use decoded URL for local paths; server accepts both
    raise RuntimeError(f"Could not get thumb URL for {title!r}")


def _download_one(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    r = _SESSION.get(url, stream=True, timeout=120)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 16):
            if chunk:
                f.write(chunk)


def _image_url_for_entry(item: dict[str, Any]) -> str:
    if "url" in item and "commons_file" in item:
        raise ValueError(f"Item has both url and commons_file: {item.get('relpath')}")
    if "url" in item:
        return item["url"]
    if "commons_file" in item:
        return _commons_thumb_url(item["commons_file"])
    raise ValueError(f"No url or commons_file: {item.get('relpath')}")


def main() -> int:
    out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, Any] = {
        "note": "Paths are relative to the folder you pass to index (e.g. data/demo_corpus).",
        "for_ui": "Use suggested_queries in the app search box; see demo_manifest.json for ground-truth text.",
        "downloaded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "items": [],
    }
    for item in _ASSETS:
        rel = item["relpath"]
        dest = out / rel
        url = _image_url_for_entry(item)
        print(f"GET {url}\n  -> {dest}")
        _download_one(url, dest)
        entry: dict[str, Any] = {
            "path": rel.replace("\\", "/"),
            "url": url,
            "description": item["description"],
            "suggested_queries": item["suggested_queries"],
        }
        if "commons_file" in item:
            entry["commons_file"] = item["commons_file"]
        manifest["items"].append(entry)

    manifest_path = out / "demo_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    lines = [
        "Suggested text queries (copy a phrase into the search box):",
        "",
    ]
    for it in manifest["items"]:
        for q in it["suggested_queries"]:
            lines.append(f"- {q}  # {it['path']}")
    (out / "suggested_queries.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nWrote {manifest_path.name} and suggested_queries.txt under:\n  {out}")
    print("Next: run the API and index this directory (absolute path to demo_corpus).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
