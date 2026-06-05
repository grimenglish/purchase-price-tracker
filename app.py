import sqlite3
from pathlib import Path
from datetime import date, datetime

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


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

.chart-title {
    font-weight: 800;
    font-size: 1.03rem;
    margin-bottom: 2px;
    color: #182230;
}

.chart-subtitle {
    color: #667085;
    font-size: 0.86rem;
    margin-bottom: 10px;
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

    if not df.empty:
        df["매입일_dt"] = pd.to_datetime(df["매입일"], errors="coerce")
        df["월"] = df["매입일_dt"].dt.strftime("%Y-%m")
        df["품목표시"] = df["품목명"].apply(lambda x: f"{ITEM_ICONS.get(x, '•')} {x}")

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


def latest_item_rows(df):
    rows = []
    for item in ITEM_CATEGORIES:
        item_df = df[df["품목명"] == item].copy()
        if item_df.empty:
            continue

        item_df = item_df.sort_values(["매입일", "id"], ascending=[False, False])
        row = item_df.iloc[0]
        rows.append({
            "품목명": item,
            "품목": f"{ITEM_ICONS.get(item, '•')} {item}",
            "최근 매입일": row["매입일"],
            "최근 매입가": row["매입가"],
            "직전매입가": row["직전매입가"],
            "변동금액": row["변동금액"],
            "변동률": row["변동률"],
            "상태": row["상태"],
            "거래처명": row["거래처명"] if row["거래처명"] else "-",
        })

    return pd.DataFrame(rows)


def latest_by_item_display(df):
    rows = []
    latest_df = latest_item_rows(df)

    existing = set(latest_df["품목명"].tolist()) if not latest_df.empty else set()

    for item in ITEM_CATEGORIES:
        if item in existing:
            row = latest_df[latest_df["품목명"] == item].iloc[0]
            rows.append({
                "품목": f"{ITEM_ICONS.get(item, '•')} {item}",
                "최근 매입일": row["최근 매입일"],
                "최근 매입가": format_money(row["최근 매입가"]),
                "직전 대비": format_percent(row["변동률"]),
                "상태": STATUS_ICON.get(row["상태"], row["상태"]),
                "거래처명": row["거래처명"],
            })
        else:
            rows.append({
                "품목": f"{ITEM_ICONS.get(item, '•')} {item}",
                "최근 매입일": "-",
                "최근 매입가": "-",
                "직전 대비": "-",
                "상태": "-",
                "거래처명": "-",
            })
    return pd.DataFrame(rows)


def base_fig_layout(fig, height=360):
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=35, b=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Arial, sans-serif", size=13),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(gridcolor="rgba(16, 24, 40, 0.08)")
    return fig


def render_chart_header(title, subtitle):
    st.markdown(f'<div class="chart-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="chart-subtitle">{subtitle}</div>', unsafe_allow_html=True)


def chart_latest_prices(df):
    latest_df = latest_item_rows(df)
    if latest_df.empty:
        st.info("그래프를 만들 기록이 없습니다.")
        return

    fig = px.bar(
        latest_df,
        x="품목",
        y="최근 매입가",
        text=latest_df["최근 매입가"].apply(lambda x: f"{int(x):,}원"),
        hover_data=["최근 매입일", "거래처명", "상태"],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(title="최근 매입가", tickformat=",")
    fig.update_xaxes(title=None)
    fig = base_fig_layout(fig, height=390)
    st.plotly_chart(fig, use_container_width=True)


def chart_latest_change_rate(df):
    latest_df = latest_item_rows(df)
    latest_df = latest_df.dropna(subset=["변동률"])

    if latest_df.empty:
        st.info("상승/하락 비교를 보려면 같은 품목 기록이 2개 이상 필요합니다.")
        return

    fig = px.bar(
        latest_df,
        x="품목",
        y="변동률",
        color="상태",
        text=latest_df["변동률"].apply(lambda x: f"{x:+.2f}%"),
        hover_data=["최근 매입일", "최근 매입가", "직전매입가", "변동금액"],
        color_discrete_map={
            "상승": "#d92d20",
            "하락": "#1570ef",
            "동일": "#667085",
            "신규": "#12b76a",
        },
    )
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="#98a2b3")
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(title="직전 대비 변동률", ticksuffix="%")
    fig.update_xaxes(title=None)
    fig = base_fig_layout(fig, height=390)
    st.plotly_chart(fig, use_container_width=True)


def chart_status_pie(df):
    status_df = df["상태"].value_counts().reset_index()
    status_df.columns = ["상태", "건수"]
    status_df["상태표시"] = status_df["상태"].map(STATUS_ICON).fillna(status_df["상태"])

    fig = px.pie(
        status_df,
        names="상태표시",
        values="건수",
        hole=0.48,
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig = base_fig_layout(fig, height=340)
    st.plotly_chart(fig, use_container_width=True)


def chart_count_by_item(df):
    count_df = df.groupby("품목명", as_index=False).size()
    count_df["품목"] = count_df["품목명"].apply(lambda x: f"{ITEM_ICONS.get(x, '•')} {x}")
    count_df = count_df.sort_values("size", ascending=False)

    fig = px.bar(
        count_df,
        x="품목",
        y="size",
        text="size",
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_yaxes(title="기록 수")
    fig.update_xaxes(title=None)
    fig = base_fig_layout(fig, height=340)
    st.plotly_chart(fig, use_container_width=True)


def chart_item_trend(df, selected_item):
    item_df = df[df["품목명"] == selected_item].copy()
    item_df = item_df.sort_values(["매입일_dt", "id"])

    if len(item_df) < 2:
        st.info("가격 흐름 그래프를 보려면 같은 품목 기록이 2개 이상 필요합니다.")
        return

    fig = px.line(
        item_df,
        x="매입일_dt",
        y="매입가",
        markers=True,
        hover_data=["거래처명", "규격단위", "변동률", "메모"],
    )
    fig.update_traces(line_width=3, marker_size=9)
    fig.update_xaxes(title="매입일")
    fig.update_yaxes(title="매입가", tickformat=",")
    fig = base_fig_layout(fig, height=390)
    st.plotly_chart(fig, use_container_width=True)


def chart_monthly_average(df, selected_item):
    item_df = df[df["품목명"] == selected_item].copy()

    if item_df.empty:
        st.info("월별 평균을 계산할 기록이 없습니다.")
        return

    monthly = (
        item_df
        .dropna(subset=["월"])
        .groupby("월", as_index=False)
        .agg(평균매입가=("매입가", "mean"), 기록수=("id", "count"))
        .sort_values("월")
    )

    if len(monthly) < 2:
        st.info("월별 추세를 보려면 2개월 이상 기록이 필요합니다.")
        return

    fig = px.line(
        monthly,
        x="월",
        y="평균매입가",
        markers=True,
        hover_data=["기록수"],
    )
    fig.update_traces(line_width=3, marker_size=9)
    fig.update_xaxes(title="월")
    fig.update_yaxes(title="월 평균 매입가", tickformat=",")
    fig = base_fig_layout(fig, height=340)
    st.plotly_chart(fig, use_container_width=True)


def chart_vendor_latest_price(df, selected_item):
    item_df = df[df["품목명"] == selected_item].copy()

    if item_df.empty:
        st.info("거래처별 비교를 만들 기록이 없습니다.")
        return

    item_df["거래처명_clean"] = item_df["거래처명"].fillna("").replace("", "미입력")
    item_df = item_df.sort_values(["거래처명_clean", "매입일_dt", "id"], ascending=[True, False, False])
    latest_vendor = item_df.drop_duplicates(subset=["거래처명_clean"], keep="first")
    latest_vendor = latest_vendor.sort_values("매입가", ascending=False).head(10)

    if latest_vendor.empty:
        st.info("거래처 정보가 부족합니다.")
        return

    fig = px.bar(
        latest_vendor,
        x="거래처명_clean",
        y="매입가",
        text=latest_vendor["매입가"].apply(lambda x: f"{int(x):,}원"),
        hover_data=["매입일", "규격단위", "메모"],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_xaxes(title="거래처")
    fig.update_yaxes(title="최근 매입가", tickformat=",")
    fig = base_fig_layout(fig, height=340)
    st.plotly_chart(fig, use_container_width=True)


def chart_change_amount_waterfall(df, selected_item):
    item_df = df[df["품목명"] == selected_item].copy()
    item_df = item_df.sort_values(["매입일_dt", "id"])
    item_df = item_df.dropna(subset=["변동금액"])

    if item_df.empty:
        st.info("변동금액 그래프를 보려면 같은 품목 기록이 2개 이상 필요합니다.")
        return

    labels = item_df["매입일"].tolist()
    values = item_df["변동금액"].tolist()

    fig = go.Figure(go.Bar(
        x=labels,
        y=values,
        text=[format_change_money(v) for v in values],
        textposition="outside",
        hovertemplate="매입일=%{x}<br>변동금액=%{y:,}원<extra></extra>",
    ))
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="#98a2b3")
    fig.update_xaxes(title="매입일")
    fig.update_yaxes(title="직전 대비 변동금액", tickformat=",")
    fig = base_fig_layout(fig, height=340)
    st.plotly_chart(fig, use_container_width=True)


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
    csv = filtered.drop(columns=["id", "매입일_dt", "월", "품목표시"], errors="ignore").to_csv(index=False).encode("utf-8-sig")
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
    st.caption("1. 매입 등록 → 2. 품목별 조회 → 3. 가격 분석")


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
            <span class="badge">그래프 대시보드</span>
            <span class="badge">CSV 다운로드</span>
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

        current_df = load_records()
        if current_df.empty:
            st.info("아직 저장된 기록이 없습니다.")
        else:
            st.dataframe(
                latest_by_item_display(current_df),
                use_container_width=True,
                hide_index=True
            )

        st.markdown("#### 빠른 확인")
        if current_df.empty:
            st.caption("기록을 넣으면 상승/하락 현황이 표시됩니다.")
        else:
            today_count = int((pd.to_datetime(current_df["매입일"]).dt.date == date.today()).sum())
            total_count = len(current_df)
            up_count = int((current_df["상태"] == "상승").sum())
            down_count = int((current_df["상태"] == "하락").sum())

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
    st.markdown('<div class="card-subtitle">최근 단가, 상승/하락률, 거래처별 가격, 월별 흐름을 그래프로 확인합니다.</div>', unsafe_allow_html=True)

    df = load_records()

    if df.empty:
        st.info("분석할 기록이 없습니다.")
    else:
        total_count = len(df)
        up_count = int((df["상태"] == "상승").sum())
        down_count = int((df["상태"] == "하락").sum())
        same_count = int((df["상태"] == "동일").sum())

        latest_numeric = latest_item_rows(df)
        avg_latest_price = latest_numeric["최근 매입가"].mean() if not latest_numeric.empty else 0
        max_change_row = latest_numeric.dropna(subset=["변동률"]).sort_values("변동률", ascending=False).head(1)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("전체 기록", f"{total_count:,}건")
        m2.metric("상승 기록", f"{up_count:,}건")
        m3.metric("하락 기록", f"{down_count:,}건")
        m4.metric("최근 단가 평균", format_money(avg_latest_price))

        if not max_change_row.empty:
            row = max_change_row.iloc[0]
            st.info(f"현재 가장 많이 오른 품목: {row['품목']} / 직전 대비 {format_percent(row['변동률'])}")

        st.divider()

        st.markdown("#### 한눈에 보는 전체 현황")
        a1, a2 = st.columns([1.25, 1], gap="large")

        with a1:
            render_chart_header("품목별 최근 매입가", "각 품목의 가장 최근 매입가를 비교합니다.")
            chart_latest_prices(df)

        with a2:
            render_chart_header("최근 변동률", "각 품목의 직전 매입가 대비 상승/하락률입니다.")
            chart_latest_change_rate(df)

        st.divider()

        b1, b2 = st.columns([1, 1], gap="large")

        with b1:
            render_chart_header("상태 비중", "전체 기록 중 상승·하락·신규 비중입니다.")
            chart_status_pie(df)

        with b2:
            render_chart_header("품목별 기록 수", "어떤 품목을 가장 자주 기록했는지 보여줍니다.")
            chart_count_by_item(df)

        st.divider()

        st.markdown("#### 품목 상세 분석")
        selected_item = st.selectbox(
            "분석할 품목 선택",
            ITEM_CATEGORIES,
            format_func=lambda x: f"{ITEM_ICONS.get(x, '')} {x}"
        )

        selected_df = df[df["품목명"] == selected_item].copy()
        if selected_df.empty:
            st.info("선택한 품목 기록이 없습니다.")
        else:
            selected_df = selected_df.sort_values(["매입일", "id"], ascending=[False, False])
            latest_row = selected_df.iloc[0]

            s1, s2, s3, s4 = st.columns(4)
            s1.metric("최근 매입가", format_money(latest_row["매입가"]))
            s2.metric("직전 매입가", format_money(latest_row["직전매입가"]))
            s3.metric("변동금액", format_change_money(latest_row["변동금액"]))
            s4.metric("변동률", format_percent(latest_row["변동률"]))

            c1, c2 = st.columns([1.25, 1], gap="large")

            with c1:
                render_chart_header(f"{ITEM_ICONS.get(selected_item, '')} {selected_item} 가격 흐름", "입력한 매입일 순서대로 가격 변화를 보여줍니다.")
                chart_item_trend(df, selected_item)

            with c2:
                render_chart_header("거래처별 최근 매입가", "같은 품목을 거래처별 최근 가격으로 비교합니다.")
                chart_vendor_latest_price(df, selected_item)

            d1, d2 = st.columns([1, 1], gap="large")

            with d1:
                render_chart_header("월별 평균 매입가", "월 단위로 평균 매입가 흐름을 봅니다.")
                chart_monthly_average(df, selected_item)

            with d2:
                render_chart_header("직전 대비 변동금액", "매입 때마다 얼마 올랐고 내렸는지 봅니다.")
                chart_change_amount_waterfall(df, selected_item)

            st.divider()

            st.markdown("#### 선택 품목 상세 기록")
            st.dataframe(
                make_display_df(selected_df),
                use_container_width=True,
                hide_index=True
            )


st.caption("비교 기준: 같은 품목명 기준으로 직전 매입가와 비교합니다.")