import sqlite3
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st


APP_TITLE = "매입가 변동 관리"
DB_PATH = Path("purchase_records.db")

ITEM_CATEGORIES = [
    "쌀",
    "엿기름",
    "설탕",
    "아이스팩 비닐",
    "아이스박스",
    "200ml 파우치",
    "테이프",
]

ITEM_ICONS = {
    "쌀": "🌾",
    "엿기름": "🌱",
    "설탕": "🧂",
    "아이스팩 비닐": "🧊",
    "아이스박스": "📦",
    "200ml 파우치": "🥤",
    "테이프": "📌",
}

STATUS_ICON = {
    "상승": "🔴 상승",
    "하락": "🔵 하락",
    "동일": "⚪ 동일",
    "신규": "🟢 신규",
}


# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="📦",
    layout="wide",
)

st.markdown("""
<style>
:root {
    --bg: #f6f8fb;
    --card: #ffffff;
    --border: #e6eaf0;
    --text: #182230;
    --muted: #667085;
    --primary: #1f6feb;
    --soft-primary: #eef5ff;
    --red: #d92d20;
    --blue: #1570ef;
    --green: #12b76a;
}

.stApp {
    background: linear-gradient(180deg, #f7f9fc 0%, #ffffff 35%, #f8fafc 100%);
}

.block-container {
    padding-top: 3.2rem;
    padding-bottom: 3rem;
    max-width: 1500px;
}

[data-testid="stHeader"] {
    background: rgba(255,255,255,0.78);
    backdrop-filter: blur(10px);
}

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}

.hero {
    background: linear-gradient(135deg, #102a43 0%, #1f6feb 58%, #53b1fd 100%);
    border-radius: 24px;
    padding: 28px 32px;
    color: white;
    box-shadow: 0 18px 50px rgba(16, 42, 67, 0.18);
    margin-bottom: 22px;
}

.hero-title {
    font-size: 2.05rem;
    font-weight: 900;
    letter-spacing: -0.04em;
    margin-bottom: 8px;
}

.hero-subtitle {
    font-size: 1rem;
    color: rgba(255,255,255,0.86);
}

.hero-badges {
    margin-top: 16px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.badge {
    display: inline-block;
    background: rgba(255,255,255,0.14);
    border: 1px solid rgba(255,255,255,0.22);
    padding: 7px 11px;
    border-radius: 999px;
    font-size: 0.86rem;
    color: white;
}

.section-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 22px;
    padding: 22px;
    box-shadow: 0 10px 28px rgba(16, 24, 40, 0.055);
    margin-bottom: 18px;
}

.mini-card {
    background: white;
    border: 1px solid #edf0f5;
    border-radius: 18px;
    padding: 16px;
    box-shadow: 0 8px 22px rgba(16, 24, 40, 0.04);
}

.item-chip {
    display: inline-block;
    padding: 6px 10px;
    margin: 0 6px 8px 0;
    border-radius: 999px;
    background: #f2f4f7;
    color: #344054;
    font-size: 0.86rem;
    border: 1px solid #eaecf0;
}

.small-muted {
    color: var(--muted);
    font-size: 0.88rem;
}

.card-title {
    font-weight: 800;
    font-size: 1.16rem;
    margin-bottom: 8px;
    color: var(--text);
}

.card-subtitle {
    color: var(--muted);
    font-size: 0.9rem;
    margin-bottom: 15px;
}

.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    border-bottom: 1px solid #eaecf0;
}

.stTabs [data-baseweb="tab"] {
    height: 42px;
    padding: 0 14px;
    border-radius: 12px 12px 0 0;
    font-weight: 700;
}

.stTabs [aria-selected="true"] {
    background: #eef5ff;
    color: #1f6feb;
}

div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #edf0f5;
    border-radius: 18px;
    padding: 15px 16px;
    box-shadow: 0 8px 22px rgba(16, 24, 40, 0.04);
}

div[data-testid="stMetricLabel"] {
    color: #667085;
}

div[data-testid="stMetricValue"] {
    font-weight: 850;
    letter-spacing: -0.04em;
}

.stButton > button {
    border-radius: 14px;
    font-weight: 800;
    height: 45px;
}

.stDownloadButton > button {
    border-radius: 14px;
    font-weight: 800;
    height: 43px;
}

[data-testid="stDataFrame"] {
    border-radius: 18px;
    overflow: hidden;
    border: 1px solid #eaecf0;
}

hr {
    margin: 1.4rem 0;
}

@media (max-width: 900px) {
    .hero {
        padding: 22px;
        border-radius: 18px;
    }
    .hero-title {
        font-size: 1.55rem;
    }
    .block-container {
        padding-top: 2.2rem;
    }
}
</style>
""", unsafe_allow_html=True)


# -----------------------------
# DB
# -----------------------------
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS purchase_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        unit TEXT,
        price INTEGER NOT NULL,
        purchase_date TEXT NOT NULL,
        vendor_name TEXT,
        vendor_phone TEXT,
        memo TEXT,
        previous_price INTEGER,
        change_amount INTEGER,
        change_percent REAL,
        change_status TEXT,
        created_at TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()


def normalize_text(value: str) -> str:
    if value is None:
        return ""
    return str(value).strip()


def calculate_change(current_price, previous_price):
    if previous_price is None:
        return None, None, "신규"

    change_amount = int(current_price) - int(previous_price)

    if previous_price == 0:
        change_percent = None
    else:
        change_percent = (change_amount / previous_price) * 100

    if change_amount > 0:
        status = "상승"
    elif change_amount < 0:
        status = "하락"
    else:
        status = "동일"

    return change_amount, change_percent, status


def find_previous_price(item_name, purchase_date):
    """
    같은 품목명 기준으로 직전 매입가를 비교합니다.
    """
    conn = get_conn()
    cur = conn.cursor()

    item_name = normalize_text(item_name)

    cur.execute("""
        SELECT price
        FROM purchase_records
        WHERE item_name = ?
          AND purchase_date <= ?
        ORDER BY purchase_date DESC, id DESC
        LIMIT 1
    """, (item_name, purchase_date))

    row = cur.fetchone()
    conn.close()

    return row[0] if row else None


def recalculate_all_changes():
    """
    기존 저장된 기록도 같은 품목 기준으로 자동 재계산합니다.
    """
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, item_name, price, purchase_date
        FROM purchase_records
        ORDER BY item_name ASC, purchase_date ASC, id ASC
    """)
    rows = cur.fetchall()

    last_price_by_item = {}

    for record_id, item_name, price, purchase_date in rows:
        previous_price = last_price_by_item.get(item_name)
        change_amount, change_percent, change_status = calculate_change(price, previous_price)

        cur.execute("""
            UPDATE purchase_records
            SET previous_price = ?,
                change_amount = ?,
                change_percent = ?,
                change_status = ?
            WHERE id = ?
        """, (previous_price, change_amount, change_percent, change_status, record_id))

        last_price_by_item[item_name] = price

    conn.commit()
    conn.close()


def insert_record(data):
    previous_price = find_previous_price(
        data["item_name"],
        data["purchase_date"]
    )

    change_amount, change_percent, change_status = calculate_change(
        data["price"],
        previous_price
    )

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO purchase_records (
            item_name,
            unit,
            price,
            purchase_date,
            vendor_name,
            vendor_phone,
            memo,
            previous_price,
            change_amount,
            change_percent,
            change_status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        normalize_text(data["item_name"]),
        normalize_text(data["unit"]),
        int(data["price"]),
        data["purchase_date"],
        normalize_text(data["vendor_name"]),
        normalize_text(data["vendor_phone"]),
        normalize_text(data["memo"]),
        previous_price,
        change_amount,
        change_percent,
        change_status,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()
    recalculate_all_changes()

    return previous_price, change_amount, change_percent, change_status


def load_records():
    conn = get_conn()
    df = pd.read_sql_query("""
        SELECT
            id,
            purchase_date AS 매입일,
            item_name AS 품목명,
            unit AS 규격단위,
            price AS 매입가,
            vendor_name AS 거래처명,
            vendor_phone AS 연락처,
            previous_price AS 직전매입가,
            change_amount AS 변동금액,
            change_percent AS 변동률,
            change_status AS 상태,
            memo AS 메모,
            created_at AS 입력일시
        FROM purchase_records
        ORDER BY purchase_date DESC, id DESC
    """, conn)
    conn.close()
    return df


def delete_record(record_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM purchase_records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()
    recalculate_all_changes()


def format_money(x):
    if pd.isna(x) or x is None:
        return "-"
    return f"{int(x):,}원"


def format_change_money(x):
    if pd.isna(x) or x is None:
        return "-"
    return f"{int(x):+,}원"


def format_percent(x):
    if pd.isna(x) or x is None:
        return "-"
    return f"{float(x):+.2f}%"


def sort_records(df, sort_option):
    if sort_option == "가격 높은순":
        return df.sort_values("매입가", ascending=False)
    if sort_option == "상승률 높은순":
        return df.sort_values("변동률", ascending=False, na_position="last")
    if sort_option == "하락률 높은순":
        return df.sort_values("변동률", ascending=True, na_position="last")
    return df.sort_values(["매입일", "id"], ascending=[False, False])


def make_display_df(df):
    show_df = df.copy()
    show_df["품목"] = show_df["품목명"].apply(lambda x: f"{ITEM_ICONS.get(x, '•')} {x}")
    show_df["매입가"] = show_df["매입가"].apply(format_money)
    show_df["직전매입가"] = show_df["직전매입가"].apply(format_money)
    show_df["변동금액"] = show_df["변동금액"].apply(format_change_money)
    show_df["변동률"] = show_df["변동률"].apply(format_percent)
    show_df["상태"] = show_df["상태"].map(STATUS_ICON).fillna(show_df["상태"])

    cols = [
        "매입일", "품목", "규격단위", "매입가", "직전매입가",
        "변동금액", "변동률", "상태", "거래처명", "연락처", "메모", "입력일시"
    ]
    return show_df[cols]


def latest_by_item(df):
    rows = []
    for item in ITEM_CATEGORIES:
        item_df = df[df["품목명"] == item].copy()
        if item_df.empty:
            rows.append({
                "품목": f"{ITEM_ICONS.get(item, '•')} {item}",
                "최근 매입일": "-",
                "최근 매입가": "-",
                "직전 대비": "-",
                "상태": "-",
                "거래처명": "-",
            })
        else:
            item_df = item_df.sort_values(["매입일", "id"], ascending=[False, False])
            row = item_df.iloc[0]
            rows.append({
                "품목": f"{ITEM_ICONS.get(item, '•')} {item}",
                "최근 매입일": row["매입일"],
                "최근 매입가": format_money(row["매입가"]),
                "직전 대비": format_percent(row["변동률"]),
                "상태": STATUS_ICON.get(row["상태"], row["상태"]),
                "거래처명": row["거래처명"] if row["거래처명"] else "-",
            })
    return pd.DataFrame(rows)


def render_record_table(source_df, tab_key, fixed_item=None):
    filtered = source_df.copy()

    if fixed_item and fixed_item != "전체":
        filtered = filtered[filtered["품목명"] == fixed_item]

    with st.container(border=True):
        f1, f2, f3 = st.columns([1.2, 1, 1])

        with f1:
            vendor_keyword = st.text_input(
                "거래처 검색",
                placeholder="예: 농산",
                key=f"vendor_{tab_key}"
            )

        with f2:
            status_filter = st.selectbox(
                "상태",
                ["전체", "상승", "하락", "동일", "신규"],
                key=f"status_{tab_key}"
            )

        with f3:
            sort_option = st.selectbox(
                "정렬",
                ["최근 매입일순", "가격 높은순", "상승률 높은순", "하락률 높은순"],
                key=f"sort_{tab_key}"
            )

    if vendor_keyword:
        filtered = filtered[
            filtered["거래처명"].fillna("").str.contains(vendor_keyword, case=False, na=False)
        ]

    if status_filter != "전체":
        filtered = filtered[filtered["상태"] == status_filter]

    filtered = sort_records(filtered, sort_option)

    if filtered.empty:
        st.info("해당 조건의 기록이 없습니다.")
        return

    summary1, summary2, summary3, summary4 = st.columns(4)
    summary1.metric("기록 수", f"{len(filtered):,}건")
    summary2.metric("상승", f"{int((filtered['상태'] == '상승').sum()):,}건")
    summary3.metric("하락", f"{int((filtered['상태'] == '하락').sum()):,}건")
    summary4.metric("최근 매입가", format_money(filtered.iloc[0]["매입가"]))

    st.dataframe(
        make_display_df(filtered),
        use_container_width=True,
        hide_index=True,
        column_config={
            "메모": st.column_config.TextColumn(width="large"),
            "매입가": st.column_config.TextColumn(width="small"),
            "직전매입가": st.column_config.TextColumn(width="small"),
            "변동률": st.column_config.TextColumn(width="small"),
        }
    )

    csv_name_item = fixed_item if fixed_item and fixed_item != "전체" else "전체"
    csv = filtered.drop(columns=["id"]).to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        f"{csv_name_item} CSV 다운로드",
        data=csv,
        file_name=f"매입가_기록_{csv_name_item}_{date.today().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
        key=f"csv_{tab_key}"
    )


# -----------------------------
# 앱 시작
# -----------------------------
init_db()
recalculate_all_changes()
df = load_records()


# -----------------------------
# 사이드바
# -----------------------------
with st.sidebar:
    st.markdown("## 📦 매입 관리")
    st.caption("원재료·부자재 단가 변동 추적")

    st.divider()

    st.markdown("#### 관리 품목")
    for item in ITEM_CATEGORIES:
        st.markdown(f"- {ITEM_ICONS.get(item, '•')} {item}")

    st.divider()

    st.markdown("#### 비교 기준")
    st.info("같은 품목명 기준으로 직전 매입가와 비교합니다.")

    st.markdown("#### 사용 순서")
    st.caption("1. 매입 기록 입력 → 2. 품목별 조회 → 3. 가격 분석 확인")


# -----------------------------
# 헤더
# -----------------------------
st.markdown(
    """
    <div class="hero">
        <div class="hero-title">매입가 변동 관리</div>
        <div class="hero-subtitle">쌀·엿기름·설탕·포장자재 매입가를 품목별로 기록하고 상승/하락률을 자동 계산합니다.</div>
        <div class="hero-badges">
            <span class="badge">품목별 탭 분리</span>
            <span class="badge">직전가 자동 비교</span>
            <span class="badge">CSV 다운로드</span>
            <span class="badge">가격 흐름 분석</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

tab_input, tab_list, tab_dashboard = st.tabs(["➕ 매입 등록", "📋 품목별 조회", "📊 가격 분석"])


# -----------------------------
# 입력 탭
# -----------------------------
with tab_input:
    c_left, c_right = st.columns([1.35, 0.9], gap="large")

    with c_left:
        st.markdown('<div class="card-title">신규 매입 등록</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-subtitle">품목을 선택하고 매입가를 입력하면 직전 가격과 자동 비교됩니다.</div>', unsafe_allow_html=True)

        with st.form("purchase_form", clear_on_submit=False):
            r1, r2 = st.columns([1, 1])

            with r1:
                item_name = st.selectbox(
                    "품목명",
                    ITEM_CATEGORIES,
                    format_func=lambda x: f"{ITEM_ICONS.get(x, '')} {x}",
                    help="품목이 섞이지 않도록 고정 항목 중에서 선택합니다."
                )
                unit = st.text_input(
                    "규격/단위",
                    placeholder="예: 20kg 1포대, 1박스, 1롤"
                )
                vendor_name = st.text_input(
                    "거래처명",
                    placeholder="예: 수정엿기름"
                )

            with r2:
                price = st.number_input(
                    "매입가",
                    min_value=0,
                    step=100,
                    format="%d"
                )
                purchase_date = st.date_input("매입일", value=date.today())
                vendor_phone = st.text_input(
                    "거래처 연락처",
                    placeholder="예: 010-0000-0000"
                )

            memo = st.text_area(
                "메모",
                placeholder="예: VAT 10% 포함, 다음부터 상승 예정, 배송비 포함 등"
            )

            submitted = st.form_submit_button("저장하기", use_container_width=True)

        if submitted:
            if price <= 0:
                st.error("매입가는 0원보다 커야 합니다.")
            else:
                previous_price, change_amount, change_percent, change_status = insert_record({
                    "item_name": item_name,
                    "unit": unit,
                    "price": price,
                    "purchase_date": purchase_date.strftime("%Y-%m-%d"),
                    "vendor_name": vendor_name,
                    "vendor_phone": vendor_phone,
                    "memo": memo,
                })

                st.success("저장 완료!")
                st.toast("매입 기록이 저장되었습니다.", icon="✅")

                r1, r2, r3, r4 = st.columns(4)
                r1.metric("현재 매입가", f"{int(price):,}원")
                r2.metric("직전 매입가", format_money(previous_price))

                if change_amount is None:
                    r3.metric("변동금액", "-")
                    r4.metric("변동률", "신규")
                else:
                    r3.metric("변동금액", f"{change_amount:+,}원")
                    r4.metric("변동률", format_percent(change_percent))

                if change_status == "상승":
                    st.warning(f"직전 대비 {change_amount:+,}원, {change_percent:+.2f}% 상승했습니다.")
                elif change_status == "하락":
                    st.info(f"직전 대비 {change_amount:+,}원, {change_percent:+.2f}% 하락했습니다.")
                elif change_status == "동일":
                    st.caption("직전 매입가와 동일합니다.")
                else:
                    st.caption("해당 품목 기준 첫 기록입니다.")

    with c_right:
        st.markdown('<div class="card-title">최근 품목별 단가</div>', unsafe_allow_html=True)
        st.markdown('<div class="card-subtitle">현재 가장 최신으로 저장된 매입가입니다.</div>', unsafe_allow_html=True)

        if df.empty:
            st.info("아직 저장된 기록이 없습니다.")
        else:
            st.dataframe(
                latest_by_item(load_records()),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("#### 빠른 확인")
        if df.empty:
            st.caption("기록을 넣으면 상승/하락 현황이 표시됩니다.")
        else:
            today_count = int((pd.to_datetime(df["매입일"]).dt.date == date.today()).sum())
            total_count = len(df)
            up_count = int((df["상태"] == "상승").sum())
            down_count = int((df["상태"] == "하락").sum())

            m1, m2 = st.columns(2)
            m1.metric("오늘 입력", f"{today_count:,}건")
            m2.metric("전체 기록", f"{total_count:,}건")
            m3, m4 = st.columns(2)
            m3.metric("상승 기록", f"{up_count:,}건")
            m4.metric("하락 기록", f"{down_count:,}건")


# -----------------------------
# 조회 탭
# -----------------------------
with tab_list:
    st.markdown('<div class="card-title">품목별 매입 기록 조회</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-subtitle">품목별로 분리해서 보이기 때문에 쌀, 엿기름, 포장자재 기록이 섞이지 않습니다.</div>', unsafe_allow_html=True)

    df = load_records()

    if df.empty:
        st.info("아직 저장된 기록이 없습니다.")
    else:
        tab_names = ["전체"] + ITEM_CATEGORIES
        item_tabs = st.tabs([f"{ITEM_ICONS.get(x, '')} {x}" if x != "전체" else "전체" for x in tab_names])

        for idx, tab_name in enumerate(tab_names):
            with item_tabs[idx]:
                st.markdown(f"### {tab_name} 기록")
                render_record_table(df, tab_key=f"tab_{idx}", fixed_item=tab_name)

        st.divider()

        with st.expander("기록 삭제"):
            st.warning("삭제하면 복구가 어렵습니다. 아래 원본 ID를 확인하고 삭제하세요.")

            delete_id = st.number_input(
                "삭제할 ID 입력",
                min_value=1,
                step=1,
                key="delete_id_input"
            )

            if st.button("선택 ID 삭제", key="delete_button"):
                delete_record(delete_id)
                st.success("삭제 완료. 새로고침하면 반영됩니다.")
                st.rerun()

            st.caption("원본 ID 확인용")
            st.dataframe(
                df[["id", "매입일", "품목명", "규격단위", "매입가", "거래처명", "메모"]],
                hide_index=True,
                use_container_width=True
            )


# -----------------------------
# 분석 탭
# -----------------------------
with tab_dashboard:
    st.markdown('<div class="card-title">가격 분석 대시보드</div>', unsafe_allow_html=True)
    st.markdown('<div class="card-subtitle">최근 단가, 상승/하락 품목, 품목별 가격 흐름을 한눈에 확인합니다.</div>', unsafe_allow_html=True)

    df = load_records()

    if df.empty:
        st.info("분석할 기록이 없습니다.")
    else:
        total_count = len(df)
        up_count = int((df["상태"] == "상승").sum())
        down_count = int((df["상태"] == "하락").sum())
        new_count = int((df["상태"] == "신규").sum())

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("전체 기록", f"{total_count:,}건")
        m2.metric("상승 기록", f"{up_count:,}건")
        m3.metric("하락 기록", f"{down_count:,}건")
        m4.metric("신규 기록", f"{new_count:,}건")

        st.divider()

        st.markdown("#### 품목별 최근 매입가")
        st.dataframe(
            latest_by_item(df),
            use_container_width=True,
            hide_index=True
        )

        st.divider()

        c1, c2 = st.columns(2, gap="large")

        with c1:
            st.markdown("#### 상승률 TOP 10")
            top_up = df[df["상태"] == "상승"].sort_values("변동률", ascending=False).head(10)
            if top_up.empty:
                st.caption("상승 기록 없음")
            else:
                st.dataframe(
                    make_display_df(top_up),
                    use_container_width=True,
                    hide_index=True
                )

        with c2:
            st.markdown("#### 하락률 TOP 10")
            top_down = df[df["상태"] == "하락"].sort_values("변동률", ascending=True).head(10)
            if top_down.empty:
                st.caption("하락 기록 없음")
            else:
                st.dataframe(
                    make_display_df(top_down),
                    use_container_width=True,
                    hide_index=True
                )

        st.divider()

        st.markdown("#### 품목별 가격 흐름")

        selected_item = st.selectbox(
            "품목 선택",
            ITEM_CATEGORIES,
            format_func=lambda x: f"{ITEM_ICONS.get(x, '')} {x}"
        )

        item_df = df[df["품목명"] == selected_item].copy()
        item_df["매입일"] = pd.to_datetime(item_df["매입일"])
        item_df = item_df.sort_values(["매입일", "id"])

        if len(item_df) >= 2:
            chart_df = item_df[["매입일", "매입가"]].set_index("매입일")
            st.line_chart(chart_df)
        else:
            st.caption("그래프를 보려면 같은 품목 기록이 2개 이상 필요합니다.")

        st.dataframe(
            make_display_df(item_df),
            use_container_width=True,
            hide_index=True
        )


st.caption("비교 기준: 같은 품목명 기준으로 직전 매입가와 비교합니다.")