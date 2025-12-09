import requests
from bs4 import BeautifulSoup
import json
import time
import re

BASE_URL = "https://www.icd10data.com"
CHAPTER_URL = "https://www.icd10data.com/ICD10CM/Codes/O00-O9A"   # Pregnancy, childbirth chapter

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/91.0.4472.124 Safari/537.36"
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
# REQUEST SOUP
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
            text = clean(li.get_text() or "")
            if text.startswith(code):
                return clean(text[len(code):])

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
    header = soup.find(lambda t:
        t.name in ["span","strong","h3"] and
        "clinical information" in t.get_text().lower()
    )
    if not header:
        return []
    ul = header.find_next("ul")
    if not ul:
        return []
    return [clean(li.get_text()) for li in ul.find_all("li")]

# ---------------------------------------------------------
# APPLICABLE TO
# ---------------------------------------------------------
def get_applicable_to(soup):
    header = soup.find(lambda t:
        t.name in ["span","strong","h3"] and
        "applicable to" in t.get_text().lower()
    )
    if not header:
        return []
    ul = header.find_next("ul")
    if not ul:
        return []
    return [clean(li.get_text()) for li in ul.find_all("li")]

# ---------------------------------------------------------
# APPROXIMATE SYNONYMS
# ---------------------------------------------------------
def get_approximate_synonyms(soup):
    header = soup.find(lambda t:
        t.name in ["span","strong","h3"]
        and "approximate synonyms" in t.get_text().lower()
    )
    if not header:
        return []
    ul = header.find_next("ul")
    if not ul:
        return []
    return [clean(li.get_text()) for li in ul.find_all("li")]

# ---------------------------------------------------------
# SCRAPE A CODE + CHILDREN
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

    body = soup.find("div","body-content")
    if not body:
        return node

    seen = set()

    for a in body.find_all("a", href=True):

        t = clean(a.get_text() or "")
        if not t:
            continue

        c_code = t.split(" ")[0]

        # Child/subchild detection
        if (
            c_code.startswith(code)
            and len(c_code) > len(code)
            and "-" not in c_code
            and "/ICD10CM/Codes/" in a["href"]
        ):

            if c_code not in seen:
                seen.add(c_code)
                child_url = BASE_URL + a["href"]

                print(f" → Child: {c_code}")

                child = scrape_code(child_url, c_code)
                if child:
                    node["children"].append(child)

    return node

# ---------------------------------------------------------
# DISCOVER ALL O00–O9A RANGES
# ---------------------------------------------------------
def discover_o_ranges():
    soup = get_soup(CHAPTER_URL)
    if not soup:
        return []

    body = soup.find("div","body-content")
    if not body:
        return []

    ranges = []

    for a in body.find_all("a", href=True):

        href = a["href"]
        txt = clean(a.get_text() or "")

        # Matches:
        # /O00-O08/, /O09-O09/, /O10-O16/, /O20-O29/, /O30-O48/, /O60-O77/, /O80-O82/, /O85-O92/, /O94-O9A/
        if "/ICD10CM/Codes/O00-O9A/" in href:
            if re.search(r"/O\d{2}", href) or txt.startswith("O"):
            # covers O00–O99
                full = BASE_URL + href
                ranges.append(full)

            # special: O9A
            if "O9A" in href:
                full = BASE_URL + href
                ranges.append(full)

    return sorted(list(set(ranges)))

# ---------------------------------------------------------
# MAIN
# ---------------------------------------------------------
def main():

    print("SCRAPING O00–O9A (Applicable To + Synonyms)…")

    start_urls = discover_o_ranges()
    if not start_urls:
        print("❌ Could not discover O ranges!")
        return

    print(f"Discovered {len(start_urls)} O-range pages:")
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

            # Root codes O00–O99 or O9A
            if (
                (code.startswith("O") and len(code) == 3 and code[1:].isdigit())
                or code.startswith("O9A")
            ):
                a = li.find("a")
                if a:
                    categories.append((code, BASE_URL + a["href"]))

    if not categories:
        print("❌ NO ROOT O CODES FOUND!")
        return

    categories = sorted(list(set(categories)))

    data = []

    for code, url in categories:

        print(f"\nROOT → {code}")

        result = scrape_code(url, code)
        if result:
            data.append(result)

    with open("O_Applicable_Approximate.json","w",encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print("\n✔ DONE — Saved O_Applicable_Approximate.json")

if __name__ == "__main__":
    main()
