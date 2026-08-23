from __future__ import annotations

import calendar
import html
import uuid
from datetime import date, timedelta
from typing import Any

import altair as alt
import pandas as pd
import streamlit as st


CAT_FOOD = "\u98df\u8cbb"
CAT_DAILY = "\u65e5\u7528\u54c1"
CAT_TRANSIT = "\u4ea4\u901a\u8cbb"
CAT_SUPER = "\u30b9\u30fc\u30d1\u30fc"

DEFAULT_CATEGORIES = {
    CAT_FOOD: "\U0001f359",
    CAT_DAILY: "\U0001f9f4",
    CAT_TRANSIT: "\U0001f683",
    CAT_SUPER: "\U0001f6d2",
}

DEFAULT_CATEGORY_COLORS = {
    CAT_FOOD: "#ffb97c",
    CAT_TRANSIT: "#eb7979",
    CAT_DAILY: "#6be080",
    CAT_SUPER: "#bfe1f6",
    "\u5a2f\u697d": "#ffe5a0",
}

EXPENSE_HEADERS = ["record_id", "日付", "内容", "金額", "カテゴリー"]

CATEGORY_ICONS = [
    "\U0001f3f7\ufe0f",
    "\U0001f359",
    "\U0001f35c",
    "\U0001f37d\ufe0f",
    "\U0001f375",
    "\U0001f9f4",
    "\U0001f9fb",
    "\U0001f48a",
    "\U0001f683",
    "\U0001f697",
    "\U0001f6b2",
    "\U0001f6d2",
    "\U0001f3e0",
    "\U0001f4a1",
    "\U0001f4f1",
    "\U0001f4da",
    "\U0001f3ac",
    "\U0001f3ae",
    "\U0001f381",
    "\U0001f4b0",
    "\U0001f4b3",
    "\U0001f4bc",
    "\U0001f4c8",
]

ICON_LABELS = {
    "\U0001f3f7\ufe0f": "\U0001f3f7\ufe0f \u305d\u306e\u4ed6",
    "\U0001f359": "\U0001f359 \u98df\u8cbb",
    "\U0001f35c": "\U0001f35c \u5916\u98df",
    "\U0001f37d\ufe0f": "\U0001f37d\ufe0f \u98df\u4e8b",
    "\U0001f375": "\U0001f375 \u30ab\u30d5\u30a7",
    "\U0001f9f4": "\U0001f9f4 \u65e5\u7528\u54c1",
    "\U0001f9fb": "\U0001f9fb \u7f8e\u5bb9\u30fb\u885b\u751f",
    "\U0001f48a": "\U0001f48a \u533b\u7642",
    "\U0001f683": "\U0001f683 \u96fb\u8eca",
    "\U0001f697": "\U0001f697 \u8eca",
    "\U0001f6b2": "\U0001f6b2 \u81ea\u8ee2\u8eca",
    "\U0001f6d2": "\U0001f6d2 \u30b9\u30fc\u30d1\u30fc",
    "\U0001f3e0": "\U0001f3e0 \u4f4f\u5c45",
    "\U0001f4a1": "\U0001f4a1 \u5149\u71b1\u8cbb",
    "\U0001f4f1": "\U0001f4f1 \u901a\u4fe1",
    "\U0001f4da": "\U0001f4da \u5b66\u7fd2",
    "\U0001f3ac": "\U0001f3ac \u6620\u753b",
    "\U0001f3ae": "\U0001f3ae \u5a2f\u697d",
    "\U0001f381": "\U0001f381 \u30ae\u30d5\u30c8",
    "\U0001f4b0": "\U0001f4b0 \u8caf\u91d1",
    "\U0001f4b3": "\U0001f4b3 \u30ab\u30fc\u30c9",
    "\U0001f4bc": "\U0001f4bc \u4ed5\u4e8b",
    "\U0001f4c8": "\U0001f4c8 \u6295\u8cc7",
}


class GoogleSheetsConfigError(RuntimeError):
    pass


#期間集計
def period_for(anchor):
    """指定日を含む、16日から翌15日までの期間を返す。"""
    if anchor.day >= 16:
        start = anchor.replace(day=16)
    else:
        previous_month = anchor.replace(day=1) - timedelta(days=1)
        start = previous_month.replace(day=16)

    next_month = (start.replace(day=1) + timedelta(days=32)).replace(day=1)
    return start, next_month.replace(day=15)


def shift_period(start, months):
    """集計期間を指定月数だけ前後へ移動する。"""
    month_index = start.year * 12 + start.month - 1 + months
    shifted = date(month_index // 12, month_index % 12 + 1, 16)
    next_month = (shifted.replace(day=1) + timedelta(days=32)).replace(day=1)
    return shifted, next_month.replace(day=15)


def money(value):
    return f"¥{int(value):,}"


#アプリで使う状態を初期化する関数
def initialize_state() -> None:
    if "categories" not in st.session_state:
        st.session_state.categories = DEFAULT_CATEGORIES.copy()
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = CAT_FOOD
    if "category_colors" not in st.session_state:
        st.session_state.category_colors = DEFAULT_CATEGORY_COLORS.copy()
    st.session_state.category_colors.update(DEFAULT_CATEGORY_COLORS)
    if "summary_has_run" not in st.session_state:
        st.session_state.summary_has_run = False


#tomlファイルから情報を参照する関数
def get_secret_section(name: str) -> Any:
    try:
        value = st.secrets.get(name)
    except Exception as exc:
        raise GoogleSheetsConfigError(
            "\u002e\u0073\u0074\u0072\u0065\u0061\u006d\u006c\u0069\u0074\u002f\u0073\u0065\u0063\u0072\u0065\u0074\u0073\u002e\u0074\u006f\u006d\u006c \u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3002"
        ) from exc

    if not value:
        raise GoogleSheetsConfigError(f"secrets.toml \u306b [{name}] \u30bb\u30af\u30b7\u30e7\u30f3\u304c\u3042\u308a\u307e\u305b\u3093\u3002")
    return value


def get_sheet_id(google_config: Any) -> str:
    sheet_id = str(
        google_config.get("sheet_id")
        or google_config.get("spreadsheet_id")
        or ""
    ).strip()

    if not sheet_id or sheet_id == "YOUR_SPREADSHEET_ID":
        raise GoogleSheetsConfigError(
            "secrets.toml \u306e [google] \u306b sheet_id \u307e\u305f\u306f spreadsheet_id \u3092\u8a2d\u5b9a\u3057\u3066\u304f\u3060\u3055\u3044\u3002"
        )
    return sheet_id


#スプレッドシートとの連携
def get_google_sheet() -> Any:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise GoogleSheetsConfigError(
            "\u5fc5\u8981\u306a\u30e9\u30a4\u30d6\u30e9\u30ea\u304c\u672a\u30a4\u30f3\u30b9\u30c8\u30fc\u30eb\u3067\u3059\u3002pip install -r requirements.txt \u3092\u5b9f\u884c\u3057\u3066\u304f\u3060\u3055\u3044\u3002"
        ) from exc

    google_config = get_secret_section("google")
    service_account_info = dict(get_secret_section("gcp_service_account"))

    sheet_id = get_sheet_id(google_config)
    worksheet_name = str(google_config.get("worksheet_name", "Sheet1")).strip() or "Sheet1"

    private_key = str(service_account_info.get("private_key", ""))
    client_email = str(service_account_info.get("client_email", ""))
    if not private_key or "YOUR_PRIVATE_KEY" in private_key:
        raise GoogleSheetsConfigError("service account JSON \u306e private_key \u3092 secrets.toml \u306b\u8a2d\u5b9a\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
    if not client_email or "YOUR_SERVICE_ACCOUNT_EMAIL" in client_email:
        raise GoogleSheetsConfigError("service account JSON \u306e client_email \u3092 secrets.toml \u306b\u8a2d\u5b9a\u3057\u3066\u304f\u3060\u3055\u3044\u3002")

    service_account_info["private_key"] = private_key.replace("\\n", "\n")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(credentials)

    try:
        spreadsheet = client.open_by_key(sheet_id)
    except Exception as exc:
        raise GoogleSheetsConfigError(
            "\u30b9\u30d7\u30ec\u30c3\u30c9\u30b7\u30fc\u30c8\u3092\u958b\u3051\u307e\u305b\u3093\u3002ID\u304c\u6b63\u3057\u3044\u304b\u3001service account \u306e client_email \u306b\u30b7\u30fc\u30c8\u3092\u5171\u6709\u3057\u3066\u3044\u308b\u304b\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002"
        ) from exc

    try:
        return spreadsheet.worksheet(worksheet_name)
    except Exception as exc:
        raise GoogleSheetsConfigError(
            f"\u30ef\u30fc\u30af\u30b7\u30fc\u30c8 '{worksheet_name}' \u304c\u898b\u3064\u304b\u308a\u307e\u305b\u3093\u3002Google Sheets \u4e0b\u90e8\u306e\u30bf\u30d6\u540d\u3068 worksheet_name \u3092\u5408\u308f\u305b\u3066\u304f\u3060\u3055\u3044\u3002"
        ) from exc


def save_to_google_sheet(entry_date: date, item: str, amount: str, category: str) -> None:
    worksheet = get_google_sheet()
    existing_headers = worksheet.row_values(1)[:5]

    if not any(existing_headers):
        worksheet.update(
            range_name="A1:E1",
            values=[EXPENSE_HEADERS],
        )
    elif existing_headers != EXPENSE_HEADERS:
        raise GoogleSheetsConfigError(
            "スプレッドシートの1行目を「record_id、日付、内容、金額、カテゴリー」"
            "の順にしてください。既存の4列シートを移行する場合は、先頭に列を追加して"
            "A1へ record_id を設定し、既存行のA列には重複しないUUIDを設定してください。"
        )

    worksheet.append_row(
        [
            str(uuid.uuid4()),
            entry_date.isoformat(),
            item,
            int(amount),
            category,
        ],
        value_input_option="USER_ENTERED",
    )


#def parse_amount(value: str) -> int:
#    cleaned_value = (
#        str(value)
#        .replace(",", "")
#        .replace("\uffe5", "")
#        .replace("\u00a5", "")
#        .strip()
#    )
#    if not cleaned_value:
#        return 0
#    return int(float(cleaned_value))


#期間別集計用のデータ読み込み
def delete_expense(expense_sheet: Any, record_id: str) -> bool:
    """record_idが一致する支出行を1行削除する。"""
    ids = expense_sheet.col_values(1)

    try:
        row_number = ids.index(record_id) + 1
    except ValueError:
        return False

    # ヘッダー行を誤って削除しないための防御。
    if row_number <= 1:
        return False

    expense_sheet.delete_rows(row_number)
    return True


def load_expenses(expense_sheet, start, end):
    """対象期間内のすべての支出を新しい順で返す。"""
    rows = expense_sheet.get_all_records()
    if not rows:
        return pd.DataFrame(columns=EXPENSE_HEADERS)

    frame = pd.DataFrame(rows)
    missing_headers = [
        header
        for header in EXPENSE_HEADERS
        if header not in frame.columns
    ]
    if missing_headers:
        raise GoogleSheetsConfigError(
            "スプレッドシートに必要な列がありません: "
            + ", ".join(missing_headers)
        )

    frame["日付"] = pd.to_datetime(frame["日付"], errors="coerce")
    frame["金額"] = (
        pd.to_numeric(frame["金額"], errors="coerce").fillna(0).astype(int)
    )
    frame = frame[
        frame["日付"].between(
            pd.Timestamp(start),
            pd.Timestamp(end),
            inclusive="both",
        )
    ].copy()
    frame["日付"] = frame["日付"].dt.strftime("%Y-%m-%d")
    return frame.sort_values(["日付"], ascending=False)


#日付を入力する画面
def render_date_picker(
    section_title: str = "#### A. 日付",
    key_prefix: str = "entry",
    default_date: date | None = None,
) -> date:
    today = date.today()
    target_date = default_date or today
    current_year = today.year
    min_year = min(current_year - 5, target_date.year)
    max_year = max(current_year + 2, target_date.year)
    years = list(range(min_year, max_year + 1))
    months = list(range(1, 13))

    st.markdown(section_title)
    year_col, month_col, day_col = st.columns(3)

    with year_col:
        selected_year = st.selectbox(
            "年",
            years,
            index=years.index(target_date.year),
            format_func=lambda value: f"{value}年",
            key=f"{key_prefix}_year",
        )

    with month_col:
        selected_month = st.selectbox(
            "月",
            months,
            index=target_date.month - 1,
            format_func=lambda value: f"{value}月",
            key=f"{key_prefix}_month",
        )

    last_day = calendar.monthrange(selected_year, selected_month)[1]
    days = list(range(1, last_day + 1))
    default_day = min(target_date.day, last_day)

    with day_col:
        selected_day = st.selectbox(
            "日",
            days,
            index=days.index(default_day),
            format_func=lambda value: f"{value}日",
            key=f"{key_prefix}_day",
        )

    return date(selected_year, selected_month, selected_day)


#カレンダー表示関数
def render_app_styles() -> None:
    st.markdown(
        """
        <style>
        .calendar-shell {
            margin: 0.5rem 0 1.25rem;
            padding: 1rem;
            border: 1px solid rgba(100, 116, 139, 0.22);
            border-radius: 16px;
            background: rgba(248, 250, 252, 0.55);
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
        }

        .calendar-grid {
            display: grid;
            grid-template-columns: repeat(7, minmax(0, 1fr));
            gap: 8px;
        }

        .cal-weekday {
            padding: 0.3rem 0;
            color: #64748b;
            font-size: 0.78rem;
            font-weight: 700;
            text-align: center;
        }

        .cal-weekday.sunday {
            color: #dc2626;
        }

        .cal-weekday.saturday {
            color: #2563eb;
        }

        .cal-empty {
            min-height: 82px;
        }

        .cal-cell {
            min-width: 0;
            min-height: 82px;
            padding: 9px;
            border: 1px solid rgba(100, 116, 139, 0.18);
            border-radius: 10px;
            color: #1f2937;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            gap: 8px;
            box-sizing: border-box;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
        }

        .cal-cell:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 14px rgba(15, 23, 42, 0.12);
        }

        .cal-cell.today {
            border-color: #16a34a;
            box-shadow: inset 0 0 0 2px #16a34a;
        }

        .cal-date {
            color: #475569;
            font-size: 0.78rem;
            font-weight: 700;
            line-height: 1;
        }

        .cal-cell.sunday .cal-date {
            color: #dc2626;
        }

        .cal-cell.saturday .cal-date {
            color: #2563eb;
        }

        .cal-amount {
            overflow-wrap: anywhere;
            font-size: 0.98rem;
            font-weight: 800;
            line-height: 1.15;
            text-align: right;
        }

        .cal-no-expense {
            color: #94a3b8;
            font-weight: 600;
        }

        @media (max-width: 700px) {
            .calendar-shell {
                margin-left: -0.4rem;
                margin-right: -0.4rem;
                padding: 0.55rem;
                border-radius: 12px;
            }

            .calendar-grid {
                gap: 4px;
            }

            .cal-empty,
            .cal-cell {
                min-height: 64px;
            }

            .cal-cell {
                padding: 6px 4px;
                border-radius: 7px;
            }

            .cal-date,
            .cal-weekday {
                font-size: 0.68rem;
            }

            .cal-amount {
                font-size: 0.72rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_calendar(start, end, daily_amounts):
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)

    weekday_names = ["月", "火", "水", "木", "金", "土", "日"]
    weekday_cells = []
    for index, weekday_name in enumerate(weekday_names):
        weekday_class = ""
        if index == 5:
            weekday_class = " saturday"
        elif index == 6:
            weekday_class = " sunday"
        weekday_cells.append(
            f'<div class="cal-weekday{weekday_class}">{weekday_name}</div>'
        )

    cells = [
        '<div class="cal-empty" aria-hidden="true"></div>'
        for _ in range(start.weekday())
    ]

    for day in days:
        day_key = day.isoformat()
        has_expense = day_key in daily_amounts
        amount = int(daily_amounts.get(day_key, 0))
        if has_expense and amount >= 501:
            background = "#f9ded8"
        elif has_expense or day <= date.today():
            background = "#e4f4e8"
        else:
            background = "#f7f7f3"
        amount_html = (
            f'<span class="cal-amount">¥{amount:,}</span>'
            if amount
            else '<span class="cal-amount cal-no-expense">—</span>'
        )
        today_class = " today" if day == date.today() else ""
        weekday_class = ""
        if day.weekday() == 5:
            weekday_class = " saturday"
        elif day.weekday() == 6:
            weekday_class = " sunday"
        cells.append(
            f"""<div class="cal-cell{today_class}{weekday_class}"
            style="background:{background}">
            <span class="cal-date">{day.month}/{day.day}</span>
            {amount_html}</div>"""
        )

    st.markdown(
        '<div class="calendar-shell"><div class="calendar-grid">'
        + "".join(weekday_cells)
        + "".join(cells)
        + "</div></div>",
        unsafe_allow_html=True,
    )


#カテゴリーの追加・削除関数
def render_category_picker() -> str:
    st.markdown("#### D. \u30ab\u30c6\u30b4\u30ea\u30fc")
    category_items = list(st.session_state.categories.items())

    columns = st.columns(4)
    for index, (category_name, icon) in enumerate(category_items):
        with columns[index % 4]:
            is_selected = st.session_state.selected_category == category_name
            if st.button(
                f"{icon} {category_name}",
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.selected_category = category_name
                st.rerun()

    with st.expander("\u30ab\u30c6\u30b4\u30ea\u30fc\u3092\u8ffd\u52a0"):
        icon = st.selectbox(
            "\u30a2\u30a4\u30b3\u30f3",
            CATEGORY_ICONS,
            format_func=lambda value: ICON_LABELS.get(value, value),
        )
        new_category = st.text_input("\u30ab\u30c6\u30b4\u30ea\u30fc\u540d", placeholder="\u4f8b: \u533b\u7642\u8cbb")
        if st.button("\u8ffd\u52a0", use_container_width=True):
            cleaned_category = new_category.strip()
            if not cleaned_category:
                st.warning("\u30ab\u30c6\u30b4\u30ea\u30fc\u540d\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
            elif cleaned_category in st.session_state.categories:
                st.warning("\u540c\u3058\u30ab\u30c6\u30b4\u30ea\u30fc\u304c\u3059\u3067\u306b\u3042\u308a\u307e\u3059\u3002")
            else:
                st.session_state.categories[cleaned_category] = icon
                st.session_state.category_colors.setdefault(cleaned_category, "#64748B")
                st.session_state.selected_category = cleaned_category
                st.success(f"{cleaned_category}\u3092\u8ffd\u52a0\u3057\u307e\u3057\u305f\u3002")
                st.rerun()

    custom_categories = [
        category_name
        for category_name in st.session_state.categories
        if category_name not in DEFAULT_CATEGORIES
    ]
    with st.expander("\u8ffd\u52a0\u3057\u305f\u30ab\u30c6\u30b4\u30ea\u30fc\u3092\u524a\u9664"):
        if not custom_categories:
            st.caption("\u524a\u9664\u3067\u304d\u308b\u8ffd\u52a0\u30ab\u30c6\u30b4\u30ea\u30fc\u306f\u307e\u3060\u3042\u308a\u307e\u305b\u3093\u3002")
        else:
            delete_category = st.selectbox(
                "\u524a\u9664\u3059\u308b\u30ab\u30c6\u30b4\u30ea\u30fc",
                custom_categories,
                key="delete_category",
            )
            if st.button("\u30ab\u30c6\u30b4\u30ea\u30fc\u3092\u524a\u9664", use_container_width=True):
                st.session_state.categories.pop(delete_category, None)
                st.session_state.category_colors.pop(delete_category, None)
                if st.session_state.selected_category == delete_category:
                    st.session_state.selected_category = CAT_FOOD
                st.success(f"{delete_category}\u3092\u524a\u9664\u3057\u307e\u3057\u305f\u3002")
                st.rerun()

    return st.session_state.selected_category


#スプレッドシートの接続テスト
def render_google_setup_hint() -> None:
    with st.expander("Google\u30b9\u30d7\u30ec\u30c3\u30c9\u30b7\u30fc\u30c8\u9023\u643a\u306e\u78ba\u8a8d"):
        st.write("\u4fdd\u5b58\u3067\u304d\u306a\u3044\u5834\u5408\u306f\u3001\u6b21\u306e4\u70b9\u3092\u78ba\u8a8d\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
        st.write("1. `.streamlit/secrets.toml` \u304c\u3042\u308b")
        st.write("2. `sheet_id` \u307e\u305f\u306f `spreadsheet_id` \u304c\u30b9\u30d7\u30ec\u30c3\u30c9\u30b7\u30fc\u30c8URL\u5185\u306eID\u306b\u306a\u3063\u3066\u3044\u308b")
        st.write("3. `worksheet_name` \u304c\u30b7\u30fc\u30c8\u4e0b\u90e8\u306e\u30bf\u30d6\u540d\u3068\u4e00\u81f4\u3057\u3066\u3044\u308b")
        st.write("4. service account \u306e `client_email` \u306b\u30b9\u30d7\u30ec\u30c3\u30c9\u30b7\u30fc\u30c8\u3092\u5171\u6709\u3057\u3066\u3044\u308b")

        if st.button("\u63a5\u7d9a\u3092\u30c6\u30b9\u30c8"):
            try:
                worksheet = get_google_sheet()
            except GoogleSheetsConfigError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"\u63a5\u7d9a\u30c6\u30b9\u30c8\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f: {exc}")
            else:
                st.success(f"\u63a5\u7d9a\u3067\u304d\u307e\u3057\u305f: {worksheet.title}")


#円グラフや集計表を表示する関数
#def render_summary_section() -> None:
#    st.divider()
#    st.markdown("### \u671f\u9593\u5225\u96c6\u8a08")
#
#    today = date.today()
#    default_start = today.replace(day=1)
#
#    def reset_summary_results() -> None:
#        st.session_state.summary_has_run = False
#
#    period_mode = st.radio(
#        "\u671f\u9593\u306e\u6307\u5b9a\u65b9\u6cd5",
#        ["\u30c9\u30e9\u30e0\u30ed\u30fc\u30eb", "\u30b9\u30e9\u30a4\u30c0\u30fc"],
#        horizontal=True,
#        key="summary_period_mode",
#        on_change=reset_summary_results,
#    )
#
#    if period_mode == "\u30b9\u30e9\u30a4\u30c0\u30fc":
#        start_date, end_date = st.slider(
#            "\u96c6\u8a08\u671f\u9593",
#            min_value=date(today.year - 5, 1, 1),
#            max_value=today,
#            value=(default_start, today),
#            format="YYYY-MM-DD",
#            key="summary_date_slider",
#        )
#    else:
#        start_date = render_date_picker(
#            "\u958b\u59cb\u65e5",
#            "summary_start",
#            default_start,
#        )
#        end_date = render_date_picker(
#            "\u7d42\u4e86\u65e5",
#            "summary_end",
#            today,
#        )
#
#    if start_date > end_date:
#        st.error("\u958b\u59cb\u65e5\u306f\u7d42\u4e86\u65e5\u3088\u308a\u524d\u306b\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
#        return
#
#    if st.button("\u3053\u306e\u671f\u9593\u3067\u96c6\u8a08", use_container_width=True):
#        st.session_state.summary_has_run = True
#
#    if not st.session_state.summary_has_run:
#        return
#
#    try:
#        expenses = load_expense_dataframe()
#    except GoogleSheetsConfigError as exc:
#        st.error(str(exc))
#        return
#    except Exception as exc:
#        st.error(f"\u96c6\u8a08\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f: {exc}")
#        return
#
#    if expenses.empty:
#        st.info("\u307e\u3060\u8a18\u9332\u304c\u3042\u308a\u307e\u305b\u3093\u3002")
#        return
#
#    period_expenses = expenses[
#        (expenses["\u65e5\u4ed8"] >= start_date)
#        & (expenses["\u65e5\u4ed8"] <= end_date)
#    ]
#
#    if period_expenses.empty:
#        st.info("\u6307\u5b9a\u671f\u9593\u306e\u8a18\u9332\u304c\u3042\u308a\u307e\u305b\u3093\u3002")
#        return
#
#    keyword_text = st.text_input(
#        "\u30ad\u30fc\u30ef\u30fc\u30c9\u3067\u7d5e\u308a\u8fbc\u307f",
#        placeholder="\u4f8b: \u30b7\u30fc\u30eb \u65e5\u7528\u54c1",
#        key="summary_keyword_filter",
#    ).strip()
#    if keyword_text:
#        keywords = [keyword.casefold() for keyword in keyword_text.split() if keyword.strip()]
#        searchable_text = (
#            period_expenses["\u5185\u5bb9"].astype(str)
#            + " "
#            + period_expenses["\u30ab\u30c6\u30b4\u30ea\u30fc"].astype(str)
#        ).str.casefold()
#        keyword_mask = searchable_text.apply(
#            lambda value: all(keyword in value for keyword in keywords)
#        )
#        period_expenses = period_expenses[keyword_mask]
#
#    if period_expenses.empty:
#        st.info("\u30ad\u30fc\u30ef\u30fc\u30c9\u306b\u4e00\u81f4\u3059\u308b\u8a18\u9332\u304c\u3042\u308a\u307e\u305b\u3093\u3002")
#        return
#
#    summary = (
#        period_expenses.groupby("\u30ab\u30c6\u30b4\u30ea\u30fc", as_index=False)["\u91d1\u984d"]
#        .sum()
#        .sort_values("\u91d1\u984d", ascending=False)
#    )
#
#    total_amount = int(summary["\u91d1\u984d"].sum())
#    st.metric("\u671f\u9593\u5185\u5408\u8a08", f"{total_amount:,}\u5186")
#
#    display_summary = summary.copy()
#    display_summary["\u91d1\u984d"] = display_summary["\u91d1\u984d"].map(lambda value: f"{int(value):,}\u5186")
#    st.dataframe(display_summary, use_container_width=True, hide_index=True)
#
#    with st.expander("\u5186\u30b0\u30e9\u30d5\u306e\u8272\u3092\u5909\u66f4"):
#        color_columns = st.columns(3)
#        for index, category_name in enumerate(summary["\u30ab\u30c6\u30b4\u30ea\u30fc"].tolist()):
#            current_color = st.session_state.category_colors.get(category_name, "#64748B")
#            with color_columns[index % 3]:
#                if category_name in DEFAULT_CATEGORY_COLORS:
#                    st.session_state.category_colors[category_name] = DEFAULT_CATEGORY_COLORS[category_name]
#                    st.color_picker(
#                        category_name,
#                        DEFAULT_CATEGORY_COLORS[category_name],
#                        key=f"summary_color_{category_name}",
#                        disabled=True,
#                    )
#                else:
#                    st.session_state.category_colors[category_name] = st.color_picker(
#                        category_name,
#                        current_color,
#                        key=f"summary_color_{category_name}",
#                    )
#
#    color_domain = summary["\u30ab\u30c6\u30b4\u30ea\u30fc"].tolist()
#    color_range = [
#        st.session_state.category_colors.get(category_name, "#64748B")
#        for category_name in color_domain
#    ]
#
#    chart = (
#        alt.Chart(summary)
#        .mark_arc(innerRadius=45)
#        .encode(
#            theta=alt.Theta(field="\u91d1\u984d", type="quantitative"),
#            color=alt.Color(
#                field="\u30ab\u30c6\u30b4\u30ea\u30fc",
#                type="nominal",
#                scale=alt.Scale(domain=color_domain, range=color_range),
#            ),
#            tooltip=[
#                alt.Tooltip("\u30ab\u30c6\u30b4\u30ea\u30fc:N", title="\u30ab\u30c6\u30b4\u30ea\u30fc"),
#                alt.Tooltip("\u91d1\u984d:Q", title="\u91d1\u984d", format=","),
#            ],
#        )
#        .properties(height=360)
#    )
#    st.altair_chart(chart, use_container_width=True)
#
#    st.markdown("#### \u8a72\u5f53\u671f\u9593\u306e\u30ec\u30b3\u30fc\u30c9")
#    display_records = period_expenses.sort_values("\u65e5\u4ed8", ascending=False).copy()
#    display_records["\u65e5\u4ed8"] = display_records["\u65e5\u4ed8"].map(lambda value: value.isoformat())
#    display_records["\u91d1\u984d"] = display_records["\u91d1\u984d"].map(lambda value: f"{int(value):,}\u5186")
#    st.dataframe(display_records, use_container_width=True, hide_index=True)


def render_period_report() -> None:
    categories = st.session_state.categories

    try:
        expense_sheet = get_google_sheet()
    except GoogleSheetsConfigError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"データ取得中にエラーが発生しました: {exc}")
        return
    
    if "period_offset" not in st.session_state:
        st.session_state.period_offset = 0

    current_start, _ = period_for(date.today())
    start, end = shift_period(
        current_start,
        st.session_state.period_offset,
    )

    previous, title, following = st.columns([1, 4, 1])

    with previous:
        if st.button(
            "← 前期間",
            key="period-nav-prev",
            use_container_width=True,
        ):
            st.session_state.period_offset -= 1
            st.rerun()

    with title:
        st.markdown(
            f"<h3 style='text-align:center;margin:.35rem 0'>"
            f"{end.year}年{end.month}月</h3>",
            unsafe_allow_html=True,
        )

    with following:
        if st.button(
            "次期間 →",
            key="period-nav-next",
            use_container_width=True,
        ):
            st.session_state.period_offset += 1
            st.rerun()

    try:
        expenses = load_expenses(expense_sheet, start, end)
    except GoogleSheetsConfigError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"支出データの読み込み中にエラーが発生しました: {exc}")
        return
    total = int(expenses["金額"].sum()) if not expenses.empty else 0
    days_used = (
        int(expenses["日付"].nunique()) if not expenses.empty else 0
    )

    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("期間の合計金額", money(total))
    metric2.metric("支出があった日", f"{days_used} 日")
    metric3.metric(
        "使用日の平均",
        money(round(total / days_used) if days_used else 0),
    )

    st.subheader("日ごとの使用金額")
    st.caption(
        "今日以前の500円以下・支出なしの日は薄緑、"
        "501円以上の日は薄赤で表示します。"
        "緑の枠は今日を表します。"
    )
    daily = (
        expenses.groupby("日付")["金額"].sum().to_dict()
        if not expenses.empty
        else {}
    )
    render_calendar(start, end, daily)

    if expenses.empty:
        st.info("この期間の支出はまだありません。")
    else:
        st.subheader("支出一覧")

        for _, row in expenses.iterrows():
            record_id = str(row["record_id"]).strip()

            if not record_id:
                st.warning(
                    f"「{row['内容']}」にはrecord_idがないため削除できません。"
                )
                continue

            with st.container(key=f"expense-row-{record_id}"):
                left, middle, right = st.columns([3, 2, 1])
                icon = categories.get(row["カテゴリー"], "🏷️")

                with left:
                    st.markdown(
                        f"**{html.escape(str(row['内容']))}**  \n"
                        f"<span class='category-chip'>"
                        f"{icon} "
                        f"{html.escape(str(row['カテゴリー']))}"
                        f"</span>",
                        unsafe_allow_html=True,
                    )

                with middle:
                    st.markdown(
                        f"**{money(row['金額'])}**  \n"
                        f"{row['日付']}"
                    )

                with right:
                    if st.button(
                        "🗑️",
                        key=f"delete_{record_id}",
                        help="この支出を削除",
                    ):
                        if delete_expense(
                            expense_sheet,
                            record_id,
                        ):
                            st.rerun()
                        else:
                            st.warning(
                                "対象の記録が見つかりませんでした。"
                            )

#メイン画面
def main() -> None:
    st.set_page_config(page_title="家計簿入力", page_icon="\U0001f4b4", layout="centered")
    render_app_styles()
    initialize_state()

    input_tab, report_tab = st.tabs(
        ["家計簿入力", "期間レポート"]
    )


    with input_tab:
        st.title("家計簿入力")
        st.caption("日付、内容、金額、カテゴリーだけをGoogleスプレッドシートに記録します。")
        render_google_setup_hint()

        entry_date = render_date_picker()

        st.markdown("#### B. 内容")
        item = st.text_input("内容", placeholder="例: 牛乳、ノート、電車代")

        st.markdown("#### C. 金額")
        amount = st.text_input("金額", placeholder="例: 1280")

        category = render_category_picker()

        if st.button("Googleスプレッドシートに記録", use_container_width=True, type="primary"):
            cleaned_item = item.strip()
            cleaned_amount = amount.strip()

            if not cleaned_item:
                st.error("内容を入力してください。")
            elif not cleaned_amount:
                st.error("金額を入力してください。")
            elif not cleaned_amount.isascii() or not cleaned_amount.isdigit():
                st.error("金額は半角数字のみで入力してください。")
            elif int(cleaned_amount) <= 0:
                st.error("金額は1円以上で入力してください。")
            else:
                try:
                    save_to_google_sheet(
                        entry_date,
                        cleaned_item,
                        cleaned_amount,
                        category,
                    )
                except GoogleSheetsConfigError as exc:
                    st.error(str(exc))
                except Exception as exc:
                    st.error(f"保存中にエラーが発生しました: {exc}")
                else:
                    st.success("記録しました。")
                    st.write(
                        {
                            "日付": entry_date.isoformat(),
                            "内容": cleaned_item,
                            "金額": cleaned_amount,
                            "カテゴリー": category,
                        }
                    )

    with report_tab:
        render_period_report()


if __name__ == "__main__":
    main()
