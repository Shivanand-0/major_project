import requests

def test_geo_feed():
    # Test WAQI geo-lookup for exact Nagpur coordinates (21.1458, 79.0882)
    url = "https://api.waqi.info/feed/geo:21.1458;79.0882/?token=demo"
    r = requests.get(url).json()
    print("=== WAQI Geo-lookup for Nagpur (21.1458, 79.0882) ===")
    print("Status:", r.get("status"))
    if r.get("status") == "ok":
        data = r.get("data", {})
        city = data.get("city", {})
        name_safe = city.get("name", "").encode("ascii", "replace").decode("ascii")
        print("Resolved Station Name:", name_safe)
        print("Coordinates:", city.get("geo"))
        print("AQI Value:", data.get("aqi"))
        print("Dominant Pollutant:", data.get("dominentpol"))
        iaqi = data.get("iaqi", {})
        print("IAQI Pollutants:", {k: v.get("v") for k, v in iaqi.items()})

    # Test Chandrapur coordinates (19.9615, 79.2961)
    url_ch = "https://api.waqi.info/feed/geo:19.9615;79.2961/?token=demo"
    r_ch = requests.get(url_ch).json()
    print("\n=== WAQI Geo-lookup for Chandrapur (19.9615, 79.2961) ===")
    if r_ch.get("status") == "ok":
        data_ch = r_ch.get("data", {})
        name_ch = data_ch.get("city", {}).get("name", "").encode("ascii", "replace").decode("ascii")
        print("Resolved Station Name:", name_ch)
        print("AQI Value:", data_ch.get("aqi"))
        print("IAQI Pollutants:", {k: v.get("v") for k, v in data_ch.get("iaqi", {}).items()})

if __name__ == "__main__":
    test_geo_feed()
