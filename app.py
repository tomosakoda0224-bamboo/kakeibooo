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
    CAT_FOOD: "\U0001F359",
    CAT_DAILY: "\U0001F9F4",
    CAT_TRANSIT: "\U0001F683",
    CAT_SUPER: "\U0001F6D2",
}

CATEGORY_ICONS = [
    "\U0001F3F7\U0000FE0F",
    "\U0001F359",
    "\U0001F9F4",
    "\U0001F683",
    "\U0001F6D2",
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
            ".streamlit/secrets.toml が見つかりません。secrets.toml.example をコピーして設定してください。"
        ) from exc

    if not value:
        raise GoogleSheetsConfigError(f"secrets.toml に [{name}] セクションがありません。")
    return value


def get_google_sheet() -> Any:
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError as exc:
        raise GoogleSheetsConfigError(
            "必要なライブラリが未インストールです。pip install -r requirements.txt を実行してください。"
        ) from exc

    google_config = get_secret_section("google")
    service_account_info = dict(get_secret_section("gcp_service_account"))

    sheet_id = str(google_config.get("sheet_id", "")).strip()
    worksheet_name = str(google_config.get("worksheet_name", "Sheet1")).strip() or "Sheet1"

    if not sheet_id or sheet_id == "YOUR_SPREADSHEET_ID":
        raise GoogleSheetsConfigError("secrets.toml の sheet_id を実際のスプレッドシートIDに変更してください。")

    private_key = service_account_info.get("private_key")
    client_email = service_account_info.get("client_email")
    if not private_key or "YOUR_PRIVATE_KEY" in private_key:
        raise GoogleSheetsConfigError("サービスアカウントJSONの private_key を secrets.toml に設定してください。")
    if not client_email or "YOUR_SERVICE_ACCOUNT_EMAIL" in client_email:
        raise GoogleSheetsConfigError("サービスアカウントJSONの client_email を secrets.toml に設定してください。")

    # TOMLに貼り付けた秘密鍵の改行が \n のまま残っている場合に備えます。
    service_account_info["private_key"] = private_key.replace("\\n", "\n")

    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    credentials = Credentials.from_service_account_info(service_account_info, scopes=scopes)
    client = gspread.authorize(credentials)

    try:
        spreadsheet = client.open_by_key(sheet_id)
    except Exception as exc:
        raise GoogleSheetsConfigError(
            "スプレッドシートを開けません。sheet_id が正しいか、サービスアカウントのメールアドレスにシートを共有しているか確認してください。"
        ) from exc

    try:
        return spreadsheet.worksheet(worksheet_name)
    except Exception as exc:
        raise GoogleSheetsConfigError(
            f"ワークシート '{worksheet_name}' が見つかりません。シート下部のタブ名と secrets.toml の worksheet_name を合わせてください。"
        ) from exc


def save_to_google_sheet(entry_date: date, item: str, amount: str, category: str) -> None:
    worksheet = get_google_sheet()
    worksheet.append_row(
        [entry_date.isoformat(), item, amount, category],
        value_input_option="USER_ENTERED",
    )


def render_date_picker() -> date:
    today = date.today()
    current_year = today.year
    years = list(range(current_year - 5, current_year + 2))
    months = list(range(1, 13))

    st.markdown("#### A. 日付")
    year_col, month_col, day_col = st.columns(3)

    with year_col:
        selected_year = st.selectbox(
            "年",
            years,
            index=years.index(current_year),
            format_func=lambda value: f"{value}年",
        )

    with month_col:
        selected_month = st.selectbox(
            "月",
            months,
            index=today.month - 1,
            format_func=lambda value: f"{value}月",
        )

    last_day = calendar.monthrange(selected_year, selected_month)[1]
    days = list(range(1, last_day + 1))
    default_day = min(today.day, last_day)

    with day_col:
        selected_day = st.selectbox(
            "日",
            days,
            index=days.index(default_day),
            format_func=lambda value: f"{value}日",
        )

    return date(selected_year, selected_month, selected_day)


def render_category_picker() -> str:
    st.markdown("#### D. カテゴリー")
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

    with st.expander("カテゴリーを追加"):
        icon = st.selectbox("アイコン", CATEGORY_ICONS)
        new_category = st.text_input("カテゴリー名", placeholder="例: 医療費")
        if st.button("追加", use_container_width=True):
            cleaned_category = new_category.strip()
            if not cleaned_category:
                st.warning("カテゴリー名を入力してください。")
            elif cleaned_category in st.session_state.categories:
                st.warning("同じカテゴリーがすでにあります。")
            else:
                st.session_state.categories[cleaned_category] = icon
                st.session_state.selected_category = cleaned_category
                st.success(f"{cleaned_category}を追加しました。")
                st.rerun()

    return st.session_state.selected_category


def render_google_setup_hint() -> None:
    with st.expander("Googleスプレッドシート連携の確認"):
        st.write("保存できない場合は、次の4点を確認してください。")
        st.write("1. `.streamlit/secrets.toml` がある")
        st.write("2. `sheet_id` がスプレッドシートURL内のIDになっている")
        st.write("3. `worksheet_name` がシート下部のタブ名と一致している")
        st.write("4. サービスアカウントの `client_email` にスプレッドシートを共有している")
        if st.button("接続をテスト"):
            try:
                worksheet = get_google_sheet()
            except GoogleSheetsConfigError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"接続テスト中にエラーが発生しました: {exc}")
            else:
                st.success(f"接続できました: {worksheet.title}")


def main() -> None:
    st.set_page_config(page_title="家計簿入力", page_icon="\U0001F4B4", layout="centered")
    initialize_state()

    st.title("家計簿入力")
    st.caption("日付、購入品、金額、カテゴリーだけをGoogleスプレッドシートに記録します。")
    render_google_setup_hint()

    entry_date = render_date_picker()

    st.markdown("#### B. 購入品")
    item = st.text_input("購入品", placeholder="例: 牛乳、ノート、電車代")

    st.markdown("#### C. 金額")
    amount = st.text_input("金額", placeholder="例: 1280")

    category = render_category_picker()

    if st.button("Googleスプレッドシートに記録", use_container_width=True, type="primary"):
        if not item.strip():
            st.error("購入品を入力してください。")
        elif not amount.strip():
            st.error("金額を入力してください。")
        else:
            try:
                save_to_google_sheet(entry_date, item.strip(), amount.strip(), category)
            except GoogleSheetsConfigError as exc:
                st.error(str(exc))
            except Exception as exc:
                st.error(f"保存中にエラーが発生しました: {exc}")
            else:
                st.success("記録しました。")
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
