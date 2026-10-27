# 🛒 쇼핑 리스트

아이템 추가 · 수정 · 삭제 · 체크 기능을 갖춘 가벼운 웹 쇼핑 리스트 앱입니다.
Python + Streamlit으로 만들었으며 Streamlit Community Cloud에 배포합니다.
자세한 요구사항은 [PRD.md](PRD.md)를 참고하세요.

## 로컬 실행

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

브라우저에서 http://localhost:8501 로 접속합니다.

## 프로젝트 구조

| 파일 | 설명 |
|---|---|
| `app.py` | Streamlit 메인 앱 (화면 · 상태 관리) |
| `storage.py` | 데이터 로드/저장 (`load_items`, `save_items`) |
| `data/items.json` | 로컬 저장 파일 (자동 생성, git 제외) |

## 배포 (Streamlit Community Cloud)

1. GitHub 저장소를 만들고 코드를 push합니다 (`app.py`, `storage.py`, `requirements.txt`, `.streamlit/config.toml` 포함).
2. https://share.streamlit.io 에서 GitHub 계정을 연동합니다.
3. **New app** → 저장소 / 브랜치 / 메인 파일(`app.py`)을 선택하고 **Deploy**를 누릅니다.
   Python 버전은 3.10 이상이어야 합니다 (기본값이면 충분합니다).
4. 발급된 `https://<앱이름>.streamlit.app` 주소로 접속해 확인합니다.

## ⚠️ 데이터 저장에 관한 한계 (꼭 읽어 주세요)

이 앱은 목록을 **서버의 `data/items.json` 파일**에 저장합니다. 로컬에서는 문제가 없지만,
Streamlit Community Cloud에 배포하면 다음과 같이 동작합니다.

| 상황 | 결과 |
|---|---|
| 앱 재배포 (GitHub에 새 커밋 push) | **목록이 초기화됩니다.** |
| 일정 시간 접속이 없어 앱이 잠들었다가 다시 깨어남 | **목록이 초기화될 수 있습니다.** |
| Streamlit Cloud 쪽 서버 재시작·이전 | **목록이 초기화될 수 있습니다.** |
| 여러 사람·여러 기기가 같은 URL로 접속 | 모두 **하나의 목록을 함께** 보고 수정합니다 (개인별 목록 아님). |
| 휴대폰과 PC에서 동시에 수정 | 서로의 변경이 반영됩니다 (덮어쓰기로 사라지지 않음). |

따라서 지금 상태는 **개인 테스트나 짧은 기간 사용**에 적합합니다.
URL을 아는 사람은 누구나 목록을 보고 고칠 수 있으니, 개인 정보는 적지 마세요.

### 영구 저장이 필요해지면

`app.py`는 저장소에 `storage.py`의 `load_items()` / `save_items()` 두 함수로만 접근합니다.
아래 방법 중 하나로 **`storage.py`만 바꾸면** 앱의 나머지 코드는 그대로 쓸 수 있습니다 (PRD 7장 참고).

- **외부 DB (예: Supabase, Google Sheets):** 영구 저장되고 기기 간 공유됩니다. 접속 정보는 `.streamlit/secrets.toml`(Cloud에서는 앱 설정의 Secrets)에 넣습니다.
- **브라우저 localStorage:** 설정이 필요 없고 사용자별 목록이 됩니다. 대신 기기 간 공유는 되지 않습니다.

## 테스트

E2E 검토 결과와 테스트 다시 실행하는 법은 [REVIEW.md](REVIEW.md)를 참고하세요.
