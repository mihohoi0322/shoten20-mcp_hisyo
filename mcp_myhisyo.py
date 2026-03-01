import os
from datetime import datetime

import httpx
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

mcp = FastMCP("Hisyo Server")

OPENWEATHERMAP_API_KEY = os.environ.get("OPENWEATHERMAP_API_KEY", "")
BASE_URL = "https://api.openweathermap.org"


@mcp.tool()
async def get_weather_forecast(city: str, date: str) -> str:
    """指定した地域・日付の天気予報を取得します。

    Args:
        city: 地域名（例: 名古屋, 東京, 大阪, New York）
        date: 日付（YYYY-MM-DD形式、例: 2026-03-30）
    """
    if not OPENWEATHERMAP_API_KEY:
        return "エラー: OPENWEATHERMAP_API_KEY が設定されていません。"

    async with httpx.AsyncClient() as client:
        # Geocoding API で都市名から座標を取得
        geo_resp = await client.get(
            f"{BASE_URL}/geo/1.0/direct",
            params={"q": city, "limit": 1, "appid": OPENWEATHERMAP_API_KEY},
        )
        if geo_resp.status_code != 200:
            return f"エラー: 地域の検索に失敗しました（ステータス: {geo_resp.status_code}）"

        geo_data = geo_resp.json()
        if not geo_data:
            return f"エラー: '{city}' が見つかりませんでした。"

        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        city_name = geo_data[0].get("local_names", {}).get(
            "ja", geo_data[0].get("name", city)
        )

        # 5日間/3時間ごとの天気予報を取得
        forecast_resp = await client.get(
            f"{BASE_URL}/data/2.5/forecast",
            params={
                "lat": lat,
                "lon": lon,
                "appid": OPENWEATHERMAP_API_KEY,
                "units": "metric",
                "lang": "ja",
            },
        )
        if forecast_resp.status_code != 200:
            return f"エラー: 天気予報の取得に失敗しました（ステータス: {forecast_resp.status_code}）"

        forecast_data = forecast_resp.json()

    # 指定日付のデータを抽出
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        return "エラー: 日付は YYYY-MM-DD 形式で指定してください（例: 2026-03-30）"

    matching = [
        item
        for item in forecast_data.get("list", [])
        if datetime.fromtimestamp(item["dt"]).date() == target_date
    ]

    if not matching:
        available_dates = sorted(
            {
                datetime.fromtimestamp(item["dt"]).date().isoformat()
                for item in forecast_data.get("list", [])
            }
        )
        return (
            f"'{date}' の天気予報データが見つかりませんでした。\n"
            f"無料プランでは5日先までの予報が取得可能です。\n"
            f"取得可能な日付: {', '.join(available_dates)}"
        )

    # 集計
    temp_min = min(item["main"]["temp_min"] for item in matching)
    temp_max = max(item["main"]["temp_max"] for item in matching)
    humidity_avg = sum(item["main"]["humidity"] for item in matching) / len(matching)
    pop_max = max(item.get("pop", 0) for item in matching) * 100
    total_rain = sum(item.get("rain", {}).get("3h", 0) for item in matching)
    wind_max = max(item.get("wind", {}).get("speed", 0) for item in matching)

    weather_descriptions = []
    seen = set()
    for item in matching:
        for w in item.get("weather", []):
            desc = w["description"]
            if desc not in seen:
                seen.add(desc)
                weather_descriptions.append(desc)

    # 時間帯別の詳細
    timeline_lines = []
    for item in matching:
        item_dt = datetime.fromtimestamp(item["dt"])
        desc = ", ".join(w["description"] for w in item.get("weather", []))
        pop = item.get("pop", 0) * 100
        rain = item.get("rain", {}).get("3h", 0)
        timeline_lines.append(
            f"  {item_dt.strftime('%H:%M')}  {desc} | "
            f"気温 {item['main']['temp']:.1f}°C | "
            f"降水確率 {pop:.0f}% | "
            f"降水量 {rain:.1f}mm"
        )

    return (
        f"📍 {city_name} の天気予報（{date}）\n"
        f"\n"
        f"【概要】\n"
        f"  天気: {', '.join(weather_descriptions)}\n"
        f"  最高気温: {temp_max:.1f}°C\n"
        f"  最低気温: {temp_min:.1f}°C\n"
        f"  平均湿度: {humidity_avg:.0f}%\n"
        f"  最大降水確率: {pop_max:.0f}%\n"
        f"  合計降水量: {total_rain:.1f}mm\n"
        f"  最大風速: {wind_max:.1f}m/s\n"
        f"\n"
        f"【時間帯別】\n" + "\n".join(timeline_lines)
    )


HEARTRAILS_BASE_URL = "https://express.heartrails.com/api/json"


@mcp.tool()
async def get_areas() -> str:
    """日本の鉄道エリア一覧を取得します。"""
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{HEARTRAILS_BASE_URL}", params={"method": "getAreas"})
        if resp.status_code != 200:
            return f"エラー: エリア一覧の取得に失敗しました（ステータス: {resp.status_code}）"
        data = resp.json()
    areas = data.get("response", {}).get("area", [])
    if not areas:
        return "エリア情報が見つかりませんでした。"
    return "🗾 エリア一覧\n" + "\n".join(f"  - {area}" for area in areas)


@mcp.tool()
async def get_prefectures(area: str) -> str:
    """指定エリアの都道府県一覧を取得します。

    Args:
        area: エリア名（例: 関東, 近畿, 中部）
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{HEARTRAILS_BASE_URL}",
            params={"method": "getPrefectures", "area": area},
        )
        if resp.status_code != 200:
            return f"エラー: 都道府県一覧の取得に失敗しました（ステータス: {resp.status_code}）"
        data = resp.json()
    prefectures = data.get("response", {}).get("prefecture", [])
    if not prefectures:
        return f"'{area}' に該当する都道府県が見つかりませんでした。"
    return (
        f"🗾 {area} の都道府県一覧\n"
        + "\n".join(f"  - {pref}" for pref in prefectures)
    )


@mcp.tool()
async def get_lines(prefecture: str) -> str:
    """指定都道府県の鉄道路線一覧を取得します。

    Args:
        prefecture: 都道府県名（例: 東京都, 愛知県, 大阪府）
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{HEARTRAILS_BASE_URL}",
            params={"method": "getLines", "prefecture": prefecture},
        )
        if resp.status_code != 200:
            return f"エラー: 路線一覧の取得に失敗しました（ステータス: {resp.status_code}）"
        data = resp.json()
    lines = data.get("response", {}).get("line", [])
    if not lines:
        return f"'{prefecture}' に該当する路線が見つかりませんでした。"
    return (
        f"🚃 {prefecture} の路線一覧（{len(lines)}件）\n"
        + "\n".join(f"  - {line}" for line in lines)
    )


@mcp.tool()
async def get_stations(line: str = "", name: str = "") -> str:
    """鉄道駅の情報を取得します。路線名または駅名で検索できます。

    Args:
        line: 路線名（例: JR東海道本線, 名古屋市営東山線）
        name: 駅名（例: 名古屋, 東京）
    """
    if not line and not name:
        return "エラー: 路線名（line）または駅名（name）のいずれかを指定してください。"

    params: dict[str, str] = {"method": "getStations"}
    if line:
        params["line"] = line
    if name:
        params["name"] = name

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{HEARTRAILS_BASE_URL}", params=params)
        if resp.status_code != 200:
            return f"エラー: 駅情報の取得に失敗しました（ステータス: {resp.status_code}）"
        data = resp.json()

    stations = data.get("response", {}).get("station", [])
    if not stations:
        search_key = line if line else name
        return f"'{search_key}' に該当する駅が見つかりませんでした。"

    header = f"🚉 駅情報（{len(stations)}件）"
    if line:
        header = f"🚉 {line} の駅一覧（{len(stations)}件）"
    elif name:
        header = f"🚉 「{name}」の検索結果（{len(stations)}件）"

    station_lines = []
    for s in stations:
        info = (
            f"  【{s['name']}駅】\n"
            f"    路線: {s.get('line', '不明')}\n"
            f"    都道府県: {s.get('prefecture', '不明')}\n"
            f"    緯度経度: {s.get('y', '?')}, {s.get('x', '?')}"
        )
        if s.get("prev"):
            info += f"\n    前の駅: {s['prev']}"
        if s.get("next"):
            info += f"\n    次の駅: {s['next']}"
        station_lines.append(info)

    return header + "\n" + "\n".join(station_lines)


@mcp.tool()
async def get_nearest_stations(lat: float, lon: float) -> str:
    """緯度経度から最寄り駅を検索します。

    Args:
        lat: 緯度（例: 35.1709）
        lon: 経度（例: 136.8815）
    """
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{HEARTRAILS_BASE_URL}",
            params={"method": "getStations", "x": lon, "y": lat},
        )
        if resp.status_code != 200:
            return f"エラー: 最寄り駅の検索に失敗しました（ステータス: {resp.status_code}）"
        data = resp.json()

    stations = data.get("response", {}).get("station", [])
    if not stations:
        return "指定された座標付近に駅が見つかりませんでした。"

    station_lines = []
    for s in stations:
        distance = s.get("distance", "不明")
        station_lines.append(
            f"  【{s['name']}駅】 {distance}\n"
            f"    路線: {s.get('line', '不明')}\n"
            f"    都道府県: {s.get('prefecture', '不明')}\n"
            f"    緯度経度: {s.get('y', '?')}, {s.get('x', '?')}"
        )

    return (
        f"📍 座標({lat}, {lon}) の最寄り駅（{len(stations)}件）\n"
        + "\n".join(station_lines)
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)