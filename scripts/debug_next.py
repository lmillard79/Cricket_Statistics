"""Check how the Next page link appears in the Statsguru response."""
import re
from bs4 import BeautifulSoup

with open("data/statsguru_response.html", encoding="utf-8") as f:
    soup = BeautifulSoup(f.read(), "html.parser")

# Try various ways to find Next
print("--- find by string 'Next' ---")
for a in soup.find_all("a", string=re.compile(r"Next", re.IGNORECASE)):
    print(" ", a)

print("\n--- all links containing 'next' in href or text ---")
for a in soup.find_all("a"):
    text = a.get_text(strip=True)
    href = a.get("href", "")
    if "next" in text.lower() or "next" in href.lower():
        print(f"  text={text!r}  href={href!r}")
