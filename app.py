from __future__ import annotations

import calendar
from datetime import date
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

TABLE_HEADERS = [
    "\u65e5\u4ed8",
    "\u5185\u5bb9",
    "\u91d1\u984d",
    "\u30ab\u30c6\u30b4\u30ea\u30fc",
]

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


def initialize_state() -> None:
    if "categories" not in st.session_state:
        st.session_state.categories = DEFAULT_CATEGORIES.copy()
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = CAT_FOOD


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
    existing_headers = worksheet.row_values(1)[:4]
    if not any(existing_headers):
        worksheet.update("A1:D1", [TABLE_HEADERS])

    existing_rows = worksheet.get("A2:D")
    used_row_count = sum(1 for row in existing_rows if any(str(cell).strip() for cell in row))
    next_row = used_row_count + 2

    worksheet.update(
        f"A{next_row}:D{next_row}",
        [[entry_date.isoformat(), item, amount, category]],
        value_input_option="USER_ENTERED",
    )


def parse_amount(value: str) -> int:
    cleaned_value = (
        str(value)
        .replace(",", "")
        .replace("\uffe5", "")
        .replace("\u00a5", "")
        .strip()
    )
    if not cleaned_value:
        return 0
    return int(float(cleaned_value))


def load_expense_dataframe() -> pd.DataFrame:
    worksheet = get_google_sheet()
    rows = worksheet.get("A2:D")
    records = []

    for row in rows:
        values = [*row, "", "", "", ""][:4]
        entry_date, item, amount, category = values
        if not any(str(value).strip() for value in values):
            continue

        try:
            parsed_date = date.fromisoformat(str(entry_date).strip())
            parsed_amount = parse_amount(amount)
        except ValueError:
            continue

        records.append(
            {
                "\u65e5\u4ed8": parsed_date,
                "\u5185\u5bb9": item,
                "\u91d1\u984d": parsed_amount,
                "\u30ab\u30c6\u30b4\u30ea\u30fc": category,
            }
        )

    return pd.DataFrame(records, columns=TABLE_HEADERS)


def render_date_picker(
    section_title: str = "#### A. \u65e5\u4ed8",
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
            "\u5e74",
            years,
            index=years.index(target_date.year),
            format_func=lambda value: f"{value}\u5e74",
            key=f"{key_prefix}_year",
        )

    with month_col:
        selected_month = st.selectbox(
            "\u6708",
            months,
            index=target_date.month - 1,
            format_func=lambda value: f"{value}\u6708",
            key=f"{key_prefix}_month",
        )

    last_day = calendar.monthrange(selected_year, selected_month)[1]
    days = list(range(1, last_day + 1))
    default_day = min(target_date.day, last_day)

    with day_col:
        selected_day = st.selectbox(
            "\u65e5",
            days,
            index=days.index(default_day),
            format_func=lambda value: f"{value}\u65e5",
            key=f"{key_prefix}_day",
        )

    return date(selected_year, selected_month, selected_day)


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
                st.session_state.selected_category = cleaned_category
                st.success(f"{cleaned_category}\u3092\u8ffd\u52a0\u3057\u307e\u3057\u305f\u3002")
                st.rerun()

    return st.session_state.selected_category


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


def render_summary_section() -> None:
    st.divider()
    st.markdown("### \u671f\u9593\u5225\u96c6\u8a08")

    today = date.today()
    default_start = today.replace(day=1)
    period_mode = st.radio(
        "\u671f\u9593\u306e\u6307\u5b9a\u65b9\u6cd5",
        ["\u30c9\u30e9\u30e0\u30ed\u30fc\u30eb", "\u30b9\u30e9\u30a4\u30c0\u30fc"],
        horizontal=True,
        key="summary_period_mode",
    )

    if period_mode == "\u30b9\u30e9\u30a4\u30c0\u30fc":
        start_date, end_date = st.slider(
            "\u96c6\u8a08\u671f\u9593",
            min_value=date(today.year - 5, 1, 1),
            max_value=today,
            value=(default_start, today),
            format="YYYY-MM-DD",
            key="summary_date_slider",
        )
    else:
        start_date = render_date_picker(
            "\u958b\u59cb\u65e5",
            "summary_start",
            default_start,
        )
        end_date = render_date_picker(
            "\u7d42\u4e86\u65e5",
            "summary_end",
            today,
        )

    if start_date > end_date:
        st.error("\u958b\u59cb\u65e5\u306f\u7d42\u4e86\u65e5\u3088\u308a\u524d\u306b\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
        return

    if not st.button("\u3053\u306e\u671f\u9593\u3067\u96c6\u8a08", use_container_width=True):
        return

    try:
        expenses = load_expense_dataframe()
    except GoogleSheetsConfigError as exc:
        st.error(str(exc))
        return
    except Exception as exc:
        st.error(f"\u96c6\u8a08\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f: {exc}")
        return

    if expenses.empty:
        st.info("\u307e\u3060\u8a18\u9332\u304c\u3042\u308a\u307e\u305b\u3093\u3002")
        return

    period_expenses = expenses[
        (expenses["\u65e5\u4ed8"] >= start_date)
        & (expenses["\u65e5\u4ed8"] <= end_date)
    ]

    if period_expenses.empty:
        st.info("\u6307\u5b9a\u671f\u9593\u306e\u8a18\u9332\u304c\u3042\u308a\u307e\u305b\u3093\u3002")
        return

    summary = (
        period_expenses.groupby("\u30ab\u30c6\u30b4\u30ea\u30fc", as_index=False)["\u91d1\u984d"]
        .sum()
        .sort_values("\u91d1\u984d", ascending=False)
    )

    total_amount = int(summary["\u91d1\u984d"].sum())
    st.metric("\u671f\u9593\u5185\u5408\u8a08", f"{total_amount:,}\u5186")

    display_summary = summary.copy()
    display_summary["\u91d1\u984d"] = display_summary["\u91d1\u984d"].map(lambda value: f"{int(value):,}\u5186")
    st.dataframe(display_summary, use_container_width=True, hide_index=True)

    chart = (
        alt.Chart(summary)
        .mark_arc(innerRadius=45)
        .encode(
            theta=alt.Theta(field="\u91d1\u984d", type="quantitative"),
            color=alt.Color(field="\u30ab\u30c6\u30b4\u30ea\u30fc", type="nominal"),
            tooltip=[
                alt.Tooltip("\u30ab\u30c6\u30b4\u30ea\u30fc:N", title="\u30ab\u30c6\u30b4\u30ea\u30fc"),
                alt.Tooltip("\u91d1\u984d:Q", title="\u91d1\u984d", format=","),
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="\u5bb6\u8a08\u7c3f\u5165\u529b", page_icon="\U0001f4b4", layout="centered")
    initialize_state()

    st.title("\u5bb6\u8a08\u7c3f\u5165\u529b")
    st.caption("\u65e5\u4ed8\u3001\u8cfc\u5165\u54c1\u3001\u91d1\u984d\u3001\u30ab\u30c6\u30b4\u30ea\u30fc\u3060\u3051\u3092Google\u30b9\u30d7\u30ec\u30c3\u30c9\u30b7\u30fc\u30c8\u306b\u8a18\u9332\u3057\u307e\u3059\u3002")
    render_google_setup_hint()

    entry_date = render_date_picker()

    st.markdown("#### B. \u8cfc\u5165\u54c1")
    item = st.text_input("\u8cfc\u5165\u54c1", placeholder="\u4f8b: \u725b\u4e73\u3001\u30ce\u30fc\u30c8\u3001\u96fb\u8eca\u4ee3")

    st.markdown("#### C. \u91d1\u984d")
    amount = st.text_input("\u91d1\u984d", placeholder="\u4f8b: 1280")

    category = render_category_picker()

    if st.button("Google\u30b9\u30d7\u30ec\u30c3\u30c9\u30b7\u30fc\u30c8\u306b\u8a18\u9332", use_container_width=True, type="primary"):
        if not item.strip():
            st.error("\u8cfc\u5165\u54c1\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
        elif not amount.strip():
            st.error("\u91d1\u984d\u3092\u5165\u529b\u3057\u3066\u304f\u3060\u3055\u3044\u3002")
        else:
            try:
                save_to_google_sheet(entry_date, item.strip(), amount.strip(), category)
            except GoogleSheetsConfigError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"\u4fdd\u5b58\u4e2d\u306b\u30a8\u30e9\u30fc\u304c\u767a\u751f\u3057\u307e\u3057\u305f: {exc}")
            else:
                st.success("\u8a18\u9332\u3057\u307e\u3057\u305f\u3002")
                st.write(
                    {
                        "\u65e5\u4ed8": entry_date.isoformat(),
                        "\u8cfc\u5165\u54c1": item.strip(),
                        "\u91d1\u984d": amount.strip(),
                        "\u30ab\u30c6\u30b4\u30ea\u30fc": category,
                    }
                )

    render_summary_section()


if __name__ == "__main__":
    main()
