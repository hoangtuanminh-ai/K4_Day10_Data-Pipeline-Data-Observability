from __future__ import annotations

import json
import time
import re
from dataclasses import asdict, dataclass
from pathlib import Path
import requests

from core.config import Settings
from core.utils import safe_slug

@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str

def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse JSON trả về từ Crossref REST API thành danh sách PaperRecord."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []

    for item in items:
        doi = item.get("DOI", "").strip()
        if not doi:
            continue

        paper_id = f"crossref_{safe_slug(doi)}"

        titles = item.get("title", [])
        title = titles[0].strip() if titles else "Untitled"

        abstract = item.get("abstract", "")
        # Làm sạch HTML tags trong abstract
        abstract_clean = re.sub(r"<[^>]+>", "", abstract).strip() if abstract else "No summary available."

        authors = []
        for a in item.get("author", []):
            given = a.get("given", "").strip()
            family = a.get("family", "").strip()
            full_name = f"{given} {family}".strip()
            if full_name:
                authors.append(full_name)
        if not authors:
            authors = ["Unknown Author"]

        subjects = item.get("subject", [])
        categories = subjects if subjects else ["General"]
        primary_category = categories[0]

        created_date = item.get("created", {}).get("date-parts", [[2024, 1, 1]])[0]
        published_str = f"{created_date[0]:04d}-{created_date[1]:02d}-{created_date[2]:02d}" if len(created_date) >= 3 else f"{created_date[0]:04d}-01-01"

        abs_url = item.get("URL", f"https://doi.org/{doi}")

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=abstract_clean,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published_str,
                updated=published_str,
                abs_url=abs_url,
                pdf_url=abs_url,
                comment="Fetched from Crossref API",
            )
        )
    return records

def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Gọi API Crossref, lưu raw API response và raw records JSON."""
    url = "https://api.crossref.org/works"
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    headers = {"User-Agent": "DataPipelineLab/1.0 (mailto:student@lab.edu)"}

    print(f"[ROLE 2] Fetching from Crossref API: {url}")
    
    max_retries = 3
    response_data = None
    for attempt in range(max_retries):
        try:
            res = requests.get(url, params=params, headers=headers, timeout=15)
            if res.status_code == 200:
                response_data = res.json()
                break
            print(f"[WARNING] Attempt {attempt+1}: Received status {res.status_code}. Retrying...")
            time.sleep(2)
        except Exception as err:
            print(f"[TEST LỖI] Request error: {err}")
            time.sleep(2)

    if not response_data:
        raise RuntimeError("[TEST LỖI] Không thể kết nối hoặc tải dữ liệu từ Crossref API!")

    # 1. Lưu Raw API Response (JSON thô)
    settings.paths.raw_api_response.parent.mkdir(parents=True, exist_ok=True)
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)
    print(f"[ROLE 2] Saved Raw API Response to: {settings.paths.raw_api_response}")

    # 2. Parse Raw Payload thành danh sách PaperRecord
    records = parse_crossref_payload(response_data)

    # 3. Lưu Raw Records JSON
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)
    print(f"[ROLE 2] Saved Raw Records to: {settings.paths.raw_records_json} ({len(records)} records)")

    return records

def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load dữ liệu snapshot từ đĩa đệm."""
    print(f"[ROLE 2] Loading raw records from snapshot: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [PaperRecord(**item) for item in data]
