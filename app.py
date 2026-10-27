"""쇼핑 리스트 Streamlit 앱."""

import functools
import html
import re
import threading
import uuid
from datetime import datetime

import streamlit as st

from storage import load_items, save_items

MAX_NAME_LEN = 50
MIN_QTY, MAX_QTY = 1, 999
QTY_WIDTH = 72  # 모바일 폭에서 이름 입력칸이 충분히 남도록 좁게

st.set_page_config(page_title="쇼핑 리스트", page_icon="🛒")


# ---------- 상태 / 데이터 헬퍼 ----------

def normalize(item: dict) -> dict | None:
    """저장소에서 읽은 아이템을 데이터 모델에 맞게 보정한다. 쓸 수 없는 항목은 None."""
    name = str(item.get("name", "")).strip()[:MAX_NAME_LEN]
    if not name:
        return None
    try:
        qty = int(item.get("quantity", MIN_QTY))
    except (TypeError, ValueError):
        qty = MIN_QTY
    return {
        "id": str(item.get("id") or uuid.uuid4()),
        "name": name,
        "quantity": min(max(qty, MIN_QTY), MAX_QTY),
        "checked": bool(item.get("checked", False)),
        "created_at": str(item.get("created_at") or datetime.now().isoformat()),
    }


@st.cache_resource
def write_lock() -> threading.Lock:
    """모든 세션(탭·접속자)이 공유하는 저장 잠금."""
    return threading.Lock()


def reload_items() -> None:
    """저장소를 기준으로 세션 목록을 갱신한다.

    세션마다 처음 한 번만 읽으면, 다른 탭/접속자가 저장한 내용을 이 세션이 덮어써 지워 버린다.
    보정이 일어난 경우(id 누락 등) 바로 저장해 매 실행마다 id가 새로 생기지 않게 한다.
    """
    raw = load_items()
    items = [item for item in map(normalize, raw) if item]
    if items != raw:
        save_items(items)
    st.session_state["items"] = items


def mutation(callback):
    """저장소 최신 상태를 다시 읽은 뒤 변경하도록, 잠금 안에서 콜백을 실행한다."""
    @functools.wraps(callback)
    def wrapper(*args, **kwargs):
        with write_lock():
            reload_items()
            callback(*args, **kwargs)
    return wrapper


def init_state() -> None:
    """매 실행마다 저장소에서 목록을 다시 읽는다 (다른 탭의 변경 반영)."""
    with write_lock():
        reload_items()
    st.session_state.setdefault("editing_id", None)
    st.session_state.setdefault("new_qty", MIN_QTY)
    st.session_state.setdefault("add_error", None)
    st.session_state.setdefault("edit_error", None)


def get_items() -> list[dict]:
    return st.session_state["items"]


def find_item(item_id: str) -> dict | None:
    return next((item for item in get_items() if item["id"] == item_id), None)


def persist() -> None:
    save_items(get_items())


def validate_name(raw: str) -> tuple[str, str | None]:
    """(정리된 이름, 오류 메시지) 반환. 오류가 없으면 메시지는 None."""
    name = (raw or "").strip()
    if not name:
        return name, "아이템 이름을 입력해 주세요."
    if len(name) > MAX_NAME_LEN:
        return name, f"아이템 이름은 {MAX_NAME_LEN}자 이하로 입력해 주세요."
    return name, None


def md_escape(text: str) -> str:
    """toast처럼 Markdown으로 렌더링되는 곳에 이름을 넣을 때 서식 문자를 이스케이프한다."""
    return re.sub(r"([\\`*_{}\[\]()#+\-.!|~<>$:])", r"\\\1", text)


def clear_widget_keys(item_id: str) -> None:
    for prefix in ("chk", "edit", "del", "name", "qty", "save", "cancel"):
        st.session_state.pop(f"{prefix}_{item_id}", None)


# ---------- 콜백 (상태 변경은 모두 여기서) ----------

@mutation
def add_item() -> None:
    name, error = validate_name(st.session_state.get("new_name", ""))
    st.session_state["add_error"] = error
    if error:
        return
    get_items().append({
        "id": str(uuid.uuid4()),
        "name": name,
        "quantity": int(st.session_state.get("new_qty", MIN_QTY)),
        "checked": False,
        "created_at": datetime.now().isoformat(),
    })
    persist()
    # 성공했을 때만 입력창을 비운다 (검증 실패 시에는 입력 내용을 남겨 두기 위해 clear_on_submit을 쓰지 않음)
    st.session_state["new_name"] = ""
    st.session_state["new_qty"] = MIN_QTY
    st.toast(f"'{md_escape(name)}' 추가했어요", icon="🛒")


@mutation
def toggle_item(item_id: str) -> None:
    item = find_item(item_id)
    if item:
        item["checked"] = bool(st.session_state.get(f"chk_{item_id}", False))
        persist()


def start_edit(item_id: str) -> None:
    item = find_item(item_id)
    if not item:
        return
    st.session_state["editing_id"] = item_id
    st.session_state["edit_error"] = None
    st.session_state[f"name_{item_id}"] = item["name"]
    st.session_state[f"qty_{item_id}"] = item["quantity"]


@mutation
def save_edit(item_id: str) -> None:
    item = find_item(item_id)
    if not item:
        cancel_edit()
        return
    name, error = validate_name(st.session_state.get(f"name_{item_id}", ""))
    st.session_state["edit_error"] = error
    if error:
        return
    item["name"] = name
    item["quantity"] = int(st.session_state.get(f"qty_{item_id}", item["quantity"]))
    st.session_state["editing_id"] = None
    persist()


def cancel_edit() -> None:
    st.session_state["editing_id"] = None
    st.session_state["edit_error"] = None


@mutation
def delete_item(item_id: str) -> None:
    item = find_item(item_id)
    st.session_state["items"] = [item for item in get_items() if item["id"] != item_id]
    if st.session_state["editing_id"] == item_id:
        cancel_edit()
    clear_widget_keys(item_id)
    persist()
    if item:
        st.toast(f"'{md_escape(item['name'])}' 삭제했어요", icon="🗑️")


@mutation
def delete_checked() -> None:
    checked_ids = {item["id"] for item in get_items() if item["checked"]}
    st.session_state["items"] = [item for item in get_items() if not item["checked"]]
    if st.session_state["editing_id"] in checked_ids:
        cancel_edit()
    for item_id in checked_ids:
        clear_widget_keys(item_id)
    persist()
    if checked_ids:
        st.toast(f"완료한 항목 {len(checked_ids)}개를 삭제했어요", icon="🧹")


# ---------- 화면 ----------

CSS = """
<style>
.block-container { max-width: 640px; padding-top: 2.5rem; padding-bottom: 4rem; }
h1 { font-size: 2rem !important; padding-bottom: 0.25rem !important; }

.progress-text { color: var(--muted); font-size: 0.95rem; margin-bottom: -0.5rem; }
.progress-text b { color: var(--ink); }

.item-name { font-size: 1.05rem; line-height: 1.4; word-break: break-all; }
.item-qty { color: var(--muted); font-size: 0.95rem; white-space: nowrap;
            font-variant-numeric: tabular-nums; }
.item-done .item-name { text-decoration: line-through; color: var(--faint); }
.item-done .item-qty { color: var(--faint); }

[class*="st-key-row_"], [class*="st-key-editrow_"] { padding: 0.55rem 0.9rem !important; }
[class*="st-key-row_"] { background: var(--card); }
/* Streamlit 기본 음수 여백 때문에 텍스트가 세로 가운데에서 아래로 밀리는 것을 막는다 */
[class*="st-key-row_"] [data-testid="stMarkdownContainer"] { margin-bottom: 0 !important; }
[class*="st-key-editrow_"] { background: var(--edit-bg); border-color: var(--accent) !important; }
/* 좁은 화면에서 저장/취소 버튼이 이름 입력칸을 밀어내지 않도록 작게 */
[class*="st-key-editrow_"] button { min-height: 2.5rem; padding: 0 0.6rem; }
@media (max-width: 480px) {
  .block-container { padding-left: 0.75rem; padding-right: 0.75rem; }
  [class*="st-key-row_"], [class*="st-key-editrow_"] { padding: 0.5rem 0.6rem !important; }
}

/* 아이콘 버튼: 라벨은 화면 읽기 프로그램용으로만 남기고(시각적으로 숨김), 터치 영역은 36px 이상 */
:is([class*="st-key-edit_"], [class*="st-key-del_"], [class*="st-key-save_"],
    [class*="st-key-cancel_"]) button [data-testid="stMarkdownContainer"] {
  position: absolute; width: 1px; height: 1px; overflow: hidden;
  clip: rect(0 0 0 0); clip-path: inset(50%); white-space: nowrap;
}
:is([class*="st-key-edit_"], [class*="st-key-del_"]) button {
  min-width: 2.25rem; min-height: 2.25rem; justify-content: center;
}

/* 수량이 1~999를 벗어나면 Streamlit은 제출을 막기만 하므로, 브라우저의 :invalid로 안내를 띄운다 */
.qty-hint { color: #b42318; font-size: 0.85rem; }
[data-testid="stElementContainer"]:has(> * .qty-hint) { display: none; }
:is(.st-key-add_box, [class*="st-key-editrow_"]):has(input[type="number"]:invalid)
  [data-testid="stElementContainer"]:has(> * .qty-hint) { display: block; }

.empty { text-align: center; padding: 2.5rem 1rem; color: var(--muted); }
.empty .emoji { font-size: 2.5rem; display: block; margin-bottom: 0.5rem; }

:root { --ink: #1f2937; --muted: #6b7280; --faint: #b0b6bf; --card: #ffffff;
        --edit-bg: #f0fdf4; --accent: #16a34a; }
</style>
"""


def safe_html(text: str) -> str:
    """사용자 입력을 HTML에 넣기 전 이스케이프한다 ($는 수식 렌더링 방지)."""
    return html.escape(text).replace("$", "&#36;")


def render_header() -> None:
    st.html(CSS)
    st.title("🛒 쇼핑 리스트")


def render_progress() -> None:
    items = get_items()
    total = len(items)
    if total == 0:
        return
    done = sum(item["checked"] for item in items)
    st.markdown(
        f'<div class="progress-text">전체 <b>{total}</b>개 중 <b>{done}</b>개 완료 '
        f'· {round(done / total * 100)}%</div>',
        unsafe_allow_html=True,
    )
    st.progress(done / total)


def render_qty_hint() -> None:
    """수량이 범위를 벗어났을 때만 CSS로 보이는 안내 (평소에는 숨김)."""
    st.markdown(f'<div class="qty-hint">⚠️ 수량은 {MIN_QTY}~{MAX_QTY} 사이로 입력해 주세요.</div>',
                unsafe_allow_html=True)


def render_input() -> None:
    with st.container(key="add_box"), st.form("add_form", border=False):
        with st.container(horizontal=True, wrap=False, vertical_alignment="bottom"):
            st.text_input("아이템 이름", key="new_name", max_chars=MAX_NAME_LEN,
                          placeholder="무엇을 살까요?", label_visibility="collapsed",
                          width="stretch")
            st.number_input("수량", key="new_qty", min_value=MIN_QTY, max_value=MAX_QTY,
                            step=1, label_visibility="collapsed", width=QTY_WIDTH)
            st.form_submit_button("추가", on_click=add_item, type="primary", icon=":material/add:")
        render_qty_hint()
    if st.session_state["add_error"]:
        st.warning(st.session_state["add_error"], icon="⚠️")
        st.session_state["add_error"] = None


def render_item(item: dict) -> None:
    item_id = item["id"]
    # 체크 상태는 items가 기준: 재정렬돼도 다른 행으로 옮겨가지 않도록 매번 동기화한다.
    st.session_state[f"chk_{item_id}"] = item["checked"]
    editing = st.session_state["editing_id"] == item_id
    row_key = f"editrow_{item_id}" if editing else f"row_{item_id}"
    label_name = md_escape(item["name"])  # 아이콘 버튼의 숨김 라벨 (화면 읽기 프로그램용)

    with st.container(border=True, key=row_key):
        with st.container(horizontal=True, wrap=False, vertical_alignment="center"):
            st.checkbox(item["name"], key=f"chk_{item_id}", label_visibility="collapsed",
                        on_change=toggle_item, args=(item_id,), width="content")
            if editing:
                st.text_input("이름", key=f"name_{item_id}", max_chars=MAX_NAME_LEN,
                              label_visibility="collapsed", width="stretch")
                st.number_input("수량", key=f"qty_{item_id}", min_value=MIN_QTY,
                                max_value=MAX_QTY, step=1, label_visibility="collapsed",
                                width=QTY_WIDTH)
                st.button(f"{label_name} 저장", key=f"save_{item_id}", on_click=save_edit,
                          args=(item_id,), type="primary", icon=":material/check:", help="저장")
                st.button(f"{label_name} 수정 취소", key=f"cancel_{item_id}", on_click=cancel_edit,
                          icon=":material/close:", help="취소")
            else:
                done = " item-done" if item["checked"] else ""
                st.markdown(
                    f'<div class="{done.strip()}"><span class="item-name">'
                    f'{safe_html(item["name"])}</span></div>',
                    unsafe_allow_html=True, width="stretch",
                )
                st.markdown(
                    f'<div class="{done.strip()}"><span class="item-qty">'
                    f'x{item["quantity"]}</span></div>',
                    unsafe_allow_html=True, width="content",
                )
                st.button(f"{label_name} 수정", key=f"edit_{item_id}", on_click=start_edit,
                          args=(item_id,), type="tertiary", icon=":material/edit:", help="수정")
                st.button(f"{label_name} 삭제", key=f"del_{item_id}", on_click=delete_item,
                          args=(item_id,), type="tertiary", icon=":material/delete:", help="삭제")
        if editing:
            render_qty_hint()
        if editing and st.session_state["edit_error"]:
            st.warning(st.session_state["edit_error"], icon="⚠️")


def render_list() -> None:
    items = get_items()
    if not items:
        st.markdown(
            '<div class="empty"><span class="emoji">🧺</span>'
            '목록이 비어 있습니다. 아이템을 추가해 보세요!</div>',
            unsafe_allow_html=True,
        )
        return
    with st.container(gap="small"):
        for item in sorted(items, key=lambda i: (i["checked"], i["created_at"])):
            render_item(item)


def render_footer() -> None:
    items = get_items()
    if not items:
        return
    has_checked = any(item["checked"] for item in items)
    with st.container(horizontal=True, horizontal_alignment="right"):
        st.button("체크된 항목 모두 삭제", on_click=delete_checked, disabled=not has_checked,
                  icon=":material/delete_sweep:", help="체크된 항목을 한 번에 지워요")


def main() -> None:
    init_state()
    render_header()
    render_progress()
    render_input()
    render_list()
    render_footer()


main()
