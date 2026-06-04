import sqlite3
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st


APP_TITLE = "매입가 변동 기록장부"
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
.block-container {
    padding-top: 4.5rem;
    padding-bottom: 2rem;
}
.big-title {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.35;
    padding-top: 0.5rem;
    margin-top: 0;
    margin-bottom: 0.4rem;
}
.sub-text {
    color: #666;
    margin-bottom: 1.2rem;
}
.card {
    padding: 1rem;
    border: 1px solid #eee;
    border-radius: 14px;
    background: #fafafa;
}
.up {color:#d92d20; font-weight:700;}
.down {color:#1570ef; font-weight:700;}
.same {color:#667085; font-weight:700;}
.new {color:#12b76a; font-weight:700;}
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


def find_previous_price(item_name, unit, vendor_name, purchase_date):
    conn = get_conn()
    cur = conn.cursor()

    item_name = normalize_text(item_name)
    unit = normalize_text(unit)
    vendor_name = normalize_text(vendor_name)

    cur.execute("""
        SELECT price
        FROM purchase_records
        WHERE item_name = ?
          AND IFNULL(unit, '') = ?
          AND IFNULL(vendor_name, '') = ?
          AND purchase_date <= ?
        ORDER BY purchase_date DESC, id DESC
        LIMIT 1
    """, (item_name, unit, vendor_name, purchase_date))

    row = cur.fetchone()
    conn.close()

    return row[0] if row else None


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


def insert_record(data):
    previous_price = find_previous_price(
        data["item_name"],
        data["unit"],
        data["vendor_name"],
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


def format_money(x):
    if pd.isna(x) or x is None:
        return "-"
    return f"{int(x):,}원"


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


def render_record_table(source_df, tab_key, fixed_item=None):
    filtered = source_df.copy()

    if fixed_item and fixed_item != "전체":
        filtered = filtered[filtered["품목명"] == fixed_item]

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

    latest_price = filtered.iloc[0]["매입가"] if not filtered.empty else None
    summary4.metric("최근 매입가", format_money(latest_price))

    show_df = filtered.copy()
    show_df["매입가"] = show_df["매입가"].apply(format_money)
    show_df["직전매입가"] = show_df["직전매입가"].apply(format_money)
    show_df["변동금액"] = show_df["변동금액"].apply(format_money)
    show_df["변동률"] = show_df["변동률"].apply(format_percent)

    st.dataframe(
        show_df.drop(columns=["id"]),
        use_container_width=True,
        hide_index=True
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


init_db()


# -----------------------------
# 화면
# -----------------------------
st.markdown(f'<div class="big-title">{APP_TITLE}</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-text">품목·거래처별 매입가를 기록하고 직전 매입가 대비 상승/하락률을 자동 계산합니다.</div>',
    unsafe_allow_html=True
)

tab_input, tab_list, tab_dashboard = st.tabs(["➕ 매입 기록", "📋 기록 조회", "📊 가격 분석"])


# -----------------------------
# 입력 탭
# -----------------------------
with tab_input:
    st.subheader("신규 매입 기록")

    with st.form("purchase_form", clear_on_submit=False):
        c1, c2, c3 = st.columns([1.2, 1, 1])

        with c1:
            item_name = st.selectbox(
                "품목명 *",
                ITEM_CATEGORIES,
                help="품목이 섞이지 않도록 고정 항목 중에서 선택합니다."
            )
            unit = st.text_input(
                "규격/단위",
                placeholder="예: 20kg, 1박스, 1포대, 1롤"
            )

        with c2:
            price = st.number_input(
                "매입가 *",
                min_value=0,
                step=100,
                format="%d"
            )
            purchase_date = st.date_input("매입일", value=date.today())

        with c3:
            vendor_name = st.text_input(
                "거래처명",
                placeholder="예: 대구농산"
            )
            vendor_phone = st.text_input(
                "거래처 연락처",
                placeholder="예: 010-0000-0000"
            )

        memo = st.text_area(
            "메모",
            placeholder="예: 이번 달부터 단가 인상, 배송비 포함, 품질 좋음 등"
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
                st.caption("해당 품목·규격·거래처 기준 첫 기록입니다.")


# -----------------------------
# 조회 탭
# -----------------------------
with tab_list:
    st.subheader("매입 기록 조회")

    df = load_records()

    if df.empty:
        st.info("아직 저장된 기록이 없습니다.")
    else:
        tab_names = ["전체"] + ITEM_CATEGORIES
        item_tabs = st.tabs(tab_names)

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
    st.subheader("가격 분석")

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
        latest_rows = []
        for item in ITEM_CATEGORIES:
            item_df = df[df["품목명"] == item].copy()
            if not item_df.empty:
                item_df = item_df.sort_values(["매입일", "id"], ascending=[False, False])
                row = item_df.iloc[0]
                latest_rows.append({
                    "품목명": item,
                    "최근 매입일": row["매입일"],
                    "최근 매입가": row["매입가"],
                    "거래처명": row["거래처명"],
                    "상태": row["상태"],
                    "변동률": row["변동률"],
                    "메모": row["메모"],
                })
            else:
                latest_rows.append({
                    "품목명": item,
                    "최근 매입일": "-",
                    "최근 매입가": None,
                    "거래처명": "-",
                    "상태": "-",
                    "변동률": None,
                    "메모": "",
                })

        latest_df = pd.DataFrame(latest_rows)
        latest_show = latest_df.copy()
        latest_show["최근 매입가"] = latest_show["최근 매입가"].apply(format_money)
        latest_show["변동률"] = latest_show["변동률"].apply(format_percent)

        st.dataframe(latest_show, use_container_width=True, hide_index=True)

        st.divider()

        c1, c2 = st.columns(2)

        with c1:
            st.markdown("#### 상승률 TOP 10")
            top_up = df[df["상태"] == "상승"].sort_values("변동률", ascending=False).head(10)
            if top_up.empty:
                st.caption("상승 기록 없음")
            else:
                st.dataframe(
                    top_up[["매입일", "품목명", "규격단위", "거래처명", "매입가", "직전매입가", "변동률"]],
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
                    top_down[["매입일", "품목명", "규격단위", "거래처명", "매입가", "직전매입가", "변동률"]],
                    use_container_width=True,
                    hide_index=True
                )

        st.divider()

        st.markdown("#### 품목별 가격 흐름")

        selected_item = st.selectbox("품목 선택", ITEM_CATEGORIES)

        item_df = df[df["품목명"] == selected_item].copy()
        item_df["매입일"] = pd.to_datetime(item_df["매입일"])
        item_df = item_df.sort_values("매입일")

        if len(item_df) >= 2:
            chart_df = item_df[["매입일", "매입가"]].set_index("매입일")
            st.line_chart(chart_df)
        else:
            st.caption("그래프를 보려면 같은 품목 기록이 2개 이상 필요합니다.")

        st.dataframe(
            item_df[["매입일", "품목명", "규격단위", "매입가", "거래처명", "변동금액", "변동률", "상태", "메모"]],
            use_container_width=True,
            hide_index=True
        )


st.caption("기준: 같은 품목명 + 같은 규격/단위 + 같은 거래처명 기준으로 직전 매입가와 비교합니다.")