# 家計簿入力アプリ

Streamlitで作った、4項目だけの家計簿入力アプリです。

- A. 日付: 年、月、日の順にドラムロール風UIで選択
- B. 購入品: 自由記述
- C. 金額: 記述式
- D. カテゴリー: 食費、日用品、交通費、スーパーを初期表示し、追加も可能

## 起動方法

```powershell
pip install -r requirements.txt
streamlit run app.py --global.developmentMode false --server.headless true --server.port 8501
```

PowerShellから起動する場合は、同梱のスクリプトも使えます。

```powershell
.\run_app.ps1
```

## Googleスプレッドシート保存の設定

1. Google Cloudでサービスアカウントを作成します。
2. サービスアカウントのJSONキーを発行します。
3. 記録先のGoogleスプレッドシートを作成します。
4. スプレッドシートをサービスアカウントのメールアドレスに共有します。
5. `.streamlit/secrets.toml.example` を `.streamlit/secrets.toml` にコピーします。
6. `sheet_id` とサービスアカウントJSONの内容を `secrets.toml` に設定します。

スプレッドシートの列は以下の順で追記されます。

```text
日付, 購入品, 金額, カテゴリー
```
