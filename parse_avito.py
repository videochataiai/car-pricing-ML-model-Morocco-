from bs4 import BeautifulSoup

with open("avito_dump.html", "r") as f:
    soup = BeautifulSoup(f, "html.parser")

links = soup.find_all("a")
for link in links:
    href = link.get("href", "")
    if "https://www.avito.ma/fr/" in href and "/voitures/" in href and len(href) > 40:
        print(f"HREF: {href}")
        print(f"CLASS: {link.get('class')}")
        parent = link.parent
        print(f"PARENT CLASS: {parent.get('class')}")
        break
