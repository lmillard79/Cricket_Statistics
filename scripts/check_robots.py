"""Check ESPNcricinfo robots.txt for scraping permissions."""
import requests

r = requests.get(
    "https://www.espncricinfo.com/robots.txt",
    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    timeout=15,
)
print("Status:", r.status_code)
print(r.text[:3000])
