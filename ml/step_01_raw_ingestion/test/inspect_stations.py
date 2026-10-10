import requests

def check_live_stations():
    url = "https://api.waqi.info/search/?token=demo&keyword=nagpur"
    r = requests.get(url).json()
    print("=== Live WAQI Search Results for Nagpur ===")
    for item in r.get("data", []):
        uid = item.get("uid")
        name = item.get("station", {}).get("name")
        aqi = item.get("aqi")
        time = item.get("time", {}).get("stime")
        print(f"UID: {uid} | Station: {name} | AQI: {aqi} | Timestamp: {time}")

    print("\n=== Specific Station Feed Details ===")
    # Let's inspect each station in detail
    for item in r.get("data", [])[:3]:
        uid = item.get("uid")
        detail_url = f"https://api.waqi.info/feed/@{uid}/?token=demo"
        d = requests.get(detail_url).json()
        data = d.get("data", {})
        iaqi = data.get("iaqi", {})
        print(f"Station: {data.get('city', {}).get('name')}")
        print(f"  Overall AQI: {data.get('aqi')}")
        print(f"  PM2.5: {iaqi.get('pm25', {}).get('v')}")
        print(f"  PM10: {iaqi.get('pm10', {}).get('v')}")
        print(f"  Dominant Pollutant: {data.get('dominentpol')}")
        print(f"  Attribution: {[a.get('name') for a in data.get('attributions', [])]}")

if __name__ == "__main__":
    check_live_stations()
