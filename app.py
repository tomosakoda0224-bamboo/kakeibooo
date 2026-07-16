from __future__ import annotations

import calendar
from datetime import date
from typing import Any

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
    "\U0001f9f4",
    "\U0001f683",
    "\U0001f6d2",
]


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

    worksheet.append_row(
        [entry_date.isoformat(), item, amount, category],
        value_input_option="USER_ENTERED",
        table_range="A:D",
    )


def render_date_picker() -> date:
    today = date.today()
    current_year = today.year
    years = list(range(current_year - 5, current_year + 2))
    months = list(range(1, 13))

    st.markdown("#### A. \u65e5\u4ed8")
    year_col, month_col, day_col = st.columns(3)

    with year_col:
        selected_year = st.selectbox(
            "\u5e74",
            years,
            index=years.index(current_year),
            format_func=lambda value: f"{value}\u5e74",
        )

    with month_col:
        selected_month = st.selectbox(
            "\u6708",
            months,
            index=today.month - 1,
            format_func=lambda value: f"{value}\u6708",
        )

    last_day = calendar.monthrange(selected_year, selected_month)[1]
    days = list(range(1, last_day + 1))
    default_day = min(today.day, last_day)

    with day_col:
        selected_day = st.selectbox(
            "\u65e5",
            days,
            index=days.index(default_day),
            format_func=lambda value: f"{value}\u65e5",
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
        icon = st.selectbox("\u30a2\u30a4\u30b3\u30f3", CATEGORY_ICONS)
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


if __name__ == "__main__":
    main()
