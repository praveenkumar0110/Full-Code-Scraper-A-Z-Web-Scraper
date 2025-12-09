import requests
from bs4 import BeautifulSoup
import json
import time
import re

BASE_URL = "https://www.icd10data.com"
CHAPTER_URL = "https://www.icd10data.com/ICD10CM/Codes/S00-T88"   # T codes live inside S00–T88 chapter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# ---------------------------------------------------------
# CLEAN TEXT
# ---------------------------------------------------------
def clean(t):
    if not t:
        return ""
    t = t.replace("\xa0", " ").replace("\n", " ").replace("\r", " ")
    return re.sub(r"\s+", " ", t).strip()

# ---------------------------------------------------------
# HTML SOUP
# ---------------------------------------------------------
def get_soup(url):
    for _ in range(3):
        try:
            time.sleep(0.25)
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                return BeautifulSoup(r.text, "html.parser")
        except:
            time.sleep(1)
    return None

# ---------------------------------------------------------
# DESCRIPTION
# ---------------------------------------------------------
def get_description(soup, code):
    ul = soup.select_one("ul.codeHierarchy")
    if ul:
        for li in ul.find_all("li"):
            tx = clean(li.get_text() or "")
            if tx.startswith(code):
                return clean(tx[len(code):])
    h2 = soup.select_one("h2.codeDescription")
    if h2:
        return clean(h2.get_text().replace(code, "").strip(" -"))
    h1 = soup.find("h1", class_="pageHeading")
    if h1:
        return clean(h1.get_text().replace(code, "").strip(" -"))
    return ""

# ---------------------------------------------------------
# CLINICAL INFORMATION
# ---------------------------------------------------------
def get_clinical_info(soup):
    h = soup.find(lambda t:
        t.name in ["span","strong","h3"]
        and "clinical information" in t.get_text().lower()
    )
    if not h: return []
    ul = h.find_next("ul")
    if not ul: return []
    return [clean(li.get_text()) for li in ul.find_all("li")]

# ---------------------------------------------------------
# APPLICABLE TO
# ---------------------------------------------------------
def get_applicable_to(soup):
    h = soup.find(lambda t:
        t.name in ["span","strong","h3"]
        and "applicable to" in t.get_text().lower()
    )
    if not h: return []
    ul = h.find_next("ul")
    if not ul: return []
    return [clean(li.get_text()) for li in ul.find_all("li")]

# ---------------------------------------------------------
# APPROXIMATE SYNONYMS
# ---------------------------------------------------------
def get_approximate_synonyms(soup):
    h = soup.find(lambda t:
        t.name in ["span","strong","h3"]
        and "approximate synonyms" in t.get_text().lower()
    )
    if not h: return []
    ul = h.find_next("ul")
    if not ul: return []
    return [clean(li.get_text()) for li in ul.find_all("li")]

# ---------------------------------------------------------
# SCRAPE ROOT + CHILDREN
# ---------------------------------------------------------
def scrape_code(url, code):
    soup = get_soup(url)
    if not soup:
        return None

    node = {
        "code": code,
        "description": get_description(soup, code),
        "clinical_information": get_clinical_info(soup),
        "applicable_to": get_applicable_to(soup),
        "approximate_synonyms": get_approximate_synonyms(soup),
        "children": []
    }

    body = soup.find("div", "body-content")
    if not body:
        return node

    seen = set()

    for a in body.find_all("a", href=True):
        t = clean(a.get_text() or "")
        if not t:
            continue

        c_code = t.split(" ")[0]

        if (
            c_code.startswith(code)
            and len(c_code) > len(code)
            and "-" not in c_code
            and "/ICD10CM/Codes/" in a["href"]
        ):
            if c_code not in seen:
                seen.add(c_code)
                print(f" → Child: {c_code}")
                child = scrape_code(BASE_URL + a["href"], c_code)
                if child:
                    node["children"].append(child)

    return node

# ---------------------------------------------------------
# DISCOVER T RANGES
# ---------------------------------------------------------
def discover_t_ranges():

    soup = get_soup(CHAPTER_URL)
    if not soup:
        return []

    body = soup.find("div", "body-content")
    if not body:
        return []

    ranges = []

    for a in body.find_all("a", href=True):

        href = a["href"]
        txt = clean(a.get_text() or "")

        # Example:
        # /ICD10CM/Codes/S00-T88/T15-T19
        # /ICD10CM/Codes/S00-T88/T20-T25
        # /ICD10CM/Codes/S00-T88/T36-T50
        # etc.
        if "/ICD10CM/Codes/S00-T88/" in href:
            if re.search(r"/T\d{2}-T\d{2}", href):
                ranges.append(BASE_URL + href)

    return sorted(list(set(ranges)))

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():

    print("SCRAPING T00–T88 (Applicable To + Synonyms)…")

    start_urls = discover_t_ranges()
    if not start_urls:
        print("❌ Could not discover T-range pages!")
        return

    print(f"Discovered {len(start_urls)} T-range pages:")
    for u in start_urls:
        print("  -", u)

    categories = []

    for URL in start_urls:

        soup = get_soup(URL)
        if not soup:
            continue

        body = soup.find("div","body-content")
        if not body:
            continue

        ul = body.select_one("ul.codeHierarchy")
        if not ul:
            continue

        for li in ul.find_all("li"):

            t = clean(li.get_text() or "")
            if not t:
                continue

            code = t.split(" ")[0]

            # ROOT T CODES: T00..T88
            if code.startswith("T") and len(code)==3 and code[1:].isdigit():

                a = li.find("a")
                if a:
                    categories.append((code, BASE_URL + a["href"]))

    if not categories:
        print("❌ NO ROOT T CODES FOUND!")
        return

    categories = sorted(list(set(categories)))
    data = []

    for code, url in categories:

        print(f"\nROOT → {code}")

        res = scrape_code(url, code)
        if res:
            data.append(res)

    with open("T_Applicable_Approximate.json","w",encoding="utf-8") as f:
        json.dump(data,f,indent=2)

    print("\n✔ DONE — Saved T_Applicable_Approximate.json")

if __name__ == "__main__":
    main()
