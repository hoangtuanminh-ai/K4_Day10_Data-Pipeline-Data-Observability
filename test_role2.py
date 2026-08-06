import sys
import os
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path("src").resolve()))

from core.config import load_settings
from ingestion.crossref import fetch_source_records

def main():
    print("Khởi tạo cấu hình settings...")
    settings = load_settings()
    
    print("\nTiến hành gọi hàm fetch_source_records (ROLE 2)...")
    records = fetch_source_records(settings)
    
    print(f"\n✅ Đã tải và parse thành công {len(records)} records!")
    print("\n--- MỘT SỐ BẢN GHI VÍ DỤ ---")
    for i, r in enumerate(records[:3]):
        print(f"[{i+1}] ID: {r.paper_id}")
        print(f"    Title: {r.title}")
        print(f"    Authors: {', '.join(r.authors)}")
        print(f"    Published: {r.published}")
        print(f"    Abstract snippet: {r.summary[:80]}...\n")
        
if __name__ == "__main__":
    main()
