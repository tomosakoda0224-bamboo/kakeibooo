from __future__ import annotations

import calendar
from datetime import date
from typing import Any

import streamlit as st


DEFAULT_CATEGORIES = {
    "食費": "\U0001F359",
    "日用品": "\U0001F9F4",
    "交通費": "\U0001F683",
    "スーパー": "\U0001F6D2",
}

CATEGORY_ICONS = {
    "\U0001F3F7\U0000FE0F": "\U0001F3F7\U0000FE0F",
    "\U0001F359": "\U0001F359",
    "\U0001F9F4": "\U0001F9F4",
    "\U0001F683": "\U0001F683",
    "\U0001F6D2": "\U0001F6D2",
}


def initialize_state() -> None:
    if "categories" not in st.session_state:
        st.session_state.categories = DEFAULT_CATEGORIES.copy()
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "食費"


def get_google_sheet() -> Any | None:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return None

    try:
        google_config = st.secrets.get("google", {})
        service_account_info = st.secrets.get("gcp_service_account")
    except Exception:
        return None

    sheet_id = google_config.get("sheet_id")
    worksheet_name = google_config.get("worksheet_name", "Sheet1")

    if not sheet_id or not service_account_info:
        return None

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(
        service_account_info,
        scopes=scopes,
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(sheet_id)
    return spreadsheet.worksheet(worksheet_name)


def save_to_google_sheet(entry_date: date, item: str, amount: str, category: str) -> None:
    worksheet = get_google_sheet()
    if worksheet is None:
        raise RuntimeError(
            "Google Sheets is not configured yet. See README.md and set .streamlit/secrets.toml."
        )

    worksheet.append_row(
        [entry_date.isoformat(), item, amount, category],
        value_input_option="USER_ENTERED",
    )


def render_date_picker() -> date:
    today = date.today()
    current_year = today.year
    years = list(range(current_year - 5, current_year + 2))
    months = list(range(1, 13))

    st.markdown("#### A. Date")
    year_col, month_col, day_col = st.columns(3)

    with year_col:
        selected_year = st.selectbox(
            "Year",
            years,
            index=years.index(current_year),
            format_func=lambda value: f"{value}年",
        )

    with month_col:
        selected_month = st.selectbox(
            "Month",
            months,
            index=today.month - 1,
            format_func=lambda value: f"{value}月",
        )

    last_day = calendar.monthrange(selected_year, selected_month)[1]
    days = list(range(1, last_day + 1))
    default_day = min(today.day, last_day)

    with day_col:
        selected_day = st.selectbox(
            "Day",
            days,
            index=days.index(default_day),
            format_func=lambda value: f"{value}日",
        )

    return date(selected_year, selected_month, selected_day)


def render_category_picker() -> str:
    st.markdown("#### D. Category")
    category_items = list(st.session_state.categories.items())

    columns = st.columns(4)
    for index, (category_name, icon) in enumerate(category_items):
        with columns[index % 4]:
            is_selected = st.session_state.selected_category == category_name
            button_label = f"{icon} {category_name}"
            if st.button(
                button_label,
                use_container_width=True,
                type="primary" if is_selected else "secondary",
            ):
                st.session_state.selected_category = category_name
                st.rerun()

    with st.expander("Add category"):
        icon = st.selectbox(
            "Icon",
            list(CATEGORY_ICONS.keys()),
        )
        new_category = st.text_input("Category name", placeholder="例: 医療費")
        if st.button("Add", use_container_width=True):
            cleaned_category = new_category.strip()
            if not cleaned_category:
                st.warning("Please enter a category name.")
            elif cleaned_category in st.session_state.categories:
                st.warning("This category already exists.")
            else:
                st.session_state.categories[cleaned_category] = icon
                st.session_state.selected_category = cleaned_category
                st.success(f"Added: {cleaned_category}")
                st.rerun()

    return st.session_state.selected_category


def main() -> None:
    st.set_page_config(
        page_title="Kakeibo Input",
        page_icon="\U0001F4B4",
        layout="centered",
    )
    initialize_state()

    st.title("家計簿入力")
    st.caption("Record only date, item, amount, and category.")

    entry_date = render_date_picker()

    st.markdown("#### B. Item")
    item = st.text_input("Item", placeholder="例: 牛乳、ノート、電車代")

    st.markdown("#### C. Amount")
    amount = st.text_input("Amount", placeholder="例: 1280")

    category = render_category_picker()

    submitted = st.button(
        "Save to Google Sheets",
        use_container_width=True,
        type="primary",
    )

    if submitted:
        if not item.strip():
            st.error("Please enter an item.")
        elif not amount.strip():
            st.error("Please enter an amount.")
        else:
            try:
                save_to_google_sheet(entry_date, item.strip(), amount.strip(), category)
            except Exception as exc:
                st.error(str(exc))
            else:
                st.success("Saved.")
                st.write(
                    {
                        "日付": entry_date.isoformat(),
                        "購入品": item.strip(),
                        "金額": amount.strip(),
                        "カテゴリー": category,
                    }
                )


if __name__ == "__main__":
    main()
