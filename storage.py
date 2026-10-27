"""쇼핑 리스트 데이터 저장소.

app.py는 load_items() / save_items()만 사용한다.
저장 방식(JSON 파일 → localStorage, DB 등)을 바꿀 때는 이 파일만 수정하면 된다.

Item = {
    "id": str,          # uuid4 문자열
    "name": str,        # 1~50자
    "quantity": int,    # 1~999
    "checked": bool,
    "created_at": str,  # ISO 8601
}
"""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

DATA_FILE = Path(__file__).parent / "data" / "items.json"


def load_items() -> list[dict]:
    """저장된 아이템 목록을 읽는다. 파일이 없거나 손상된 경우 빈 리스트를 반환한다."""
    try:
        with DATA_FILE.open(encoding="utf-8") as f:
            items = json.load(f)
    except (json.JSONDecodeError, UnicodeDecodeError):
        # 손상된 파일은 다음 저장 때 덮어써지지 않도록 백업해 둔다 (수동 복구용)
        backup = DATA_FILE.with_name(f"items.corrupt-{datetime.now():%Y%m%d-%H%M%S}.json")
        try:
            os.replace(DATA_FILE, backup)
        except OSError:
            pass
        return []
    except OSError:  # 파일 없음 포함
        return []
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def save_items(items: list[dict]) -> None:
    """아이템 목록을 저장한다. 임시 파일에 쓴 뒤 교체해 저장 중 실패해도 기존 파일이 깨지지 않는다."""
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=DATA_FILE.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, DATA_FILE)
    except BaseException:
        Path(tmp_path).unlink(missing_ok=True)
        raise
