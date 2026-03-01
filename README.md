# MCP Hisyo Server

天気予報と鉄道情報を提供する MCP (Model Context Protocol) サーバーです。

## 提供ツール

| ツール名 | 説明 |
|---|---|
| `get_weather_forecast` | 指定した地域・日付の天気予報を取得（5日先まで） |
| `get_areas` | 日本の鉄道エリア一覧を取得 |
| `get_prefectures` | 指定エリアの都道府県一覧を取得 |
| `get_lines` | 指定都道府県の鉄道路線一覧を取得 |
| `get_stations` | 路線名または駅名で駅情報を検索 |
| `get_nearest_stations` | 緯度経度から最寄り駅を検索 |

## 必要なもの

- Python 3.13+
- [OpenWeatherMap API キー](https://openweathermap.org/api)（無料プランで取得可能）

## セットアップ

### 1. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 2. 環境変数の設定

`.env.example` をコピーして `.env` を作成し、API キーを設定します。

```bash
cp .env.example .env
```

```
OPENWEATHERMAP_API_KEY=your_api_key_here
```

## 稼働方法

### ローカルで実行

```bash
python mcp_myhisyo.py
```

ポート `8000` で Streamable HTTP トランスポートとして起動します。

### Docker で実行

```bash
docker build -t mcp-hisyo .
docker run -p 8000:8000 -e OPENWEATHERMAP_API_KEY=your_api_key_here mcp-hisyo
```

## MCP クライアントの設定

### VS Code (stdio)

`.vscode/mcp.json` に以下を追加します（[サンプル](.vscode/mcp.sample.json)を参照）。

```json
{
  "servers": {
    "mcp_hisyo": {
      "command": "python3",
      "args": ["/path/to/mcp_myhisyo.py"]
    }
  }
}
```

### VS Code (Streamable HTTP / コンテナー利用時)

サーバーを起動した状態で、`.vscode/mcp.json` に以下を設定します。

```json
{
  "servers": {
    "mcp_hisyo": {
      "type": "http",
      "url": "http://localhost:8000/mcp/"
    }
  }
}
```

## Azure Container Apps へのデプロイ

[`feature/aca-deploy`](https://github.com/mihohoi0322/shoten20-mcp_hisyo/tree/feature/aca-deploy) ブランチでは、Azure Container Apps (ACA) へのデプロイに対応しています。

- `src/` 配下にソースコード・Dockerfile を整理
- `infra/` に Bicep テンプレート（Container Registry、Container Apps Environment、Container App）を追加
- `azure.yaml` で [Azure Developer CLI (azd)](https://learn.microsoft.com/ja-jp/azure/developer/azure-developer-cli/) によるプロビジョニング・デプロイに対応
- `OPENWEATHERMAP_API_KEY` は azd の環境変数として設定し、デプロイ時に Container App のシークレットとして注入

### デプロイ手順

```bash
git checkout feature/aca-deploy
azd auth login
azd env set OPENWEATHERMAP_API_KEY your_api_key_here
azd up
```

### リモート MCP サーバーとしての接続

デプロイ後、`.vscode/mcp.json` に以下を設定すると、Azure 上の MCP サーバーに接続できます。

```json
{
  "servers": {
    "hisyo": {
      "type": "http",
      "url": "https://<your-container-app-url>/mcp"
    }
  }
}
```

## 利用 API

- [OpenWeatherMap API](https://openweathermap.org/api) — 天気予報
- [HeartRails Express API](https://express.heartrails.com/) — 鉄道路線・駅情報
