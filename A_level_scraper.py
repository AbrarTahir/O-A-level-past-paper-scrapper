import os
import time
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://pastpapers.papacambridge.com"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

AS_SUBJECTS = ["physics-9702", "chemistry-9701", "biology-9700"]
A_SUBJECTS = ["physics-9702", "chemistry-9701", "biology-9700"]

AS_PAPERS = ["Paper 1", "Paper 2"]
A_PAPERS = ["Paper 4"]

START_YEAR = 2017
END_YEAR = 2025

def get_soup(url):
    for i in range(3):
        try:
            res = requests.get(url, headers=HEADERS, timeout=10)
            res.raise_for_status()
            return BeautifulSoup(res.text, "html.parser")
        except requests.RequestException as e:
            print(f"⚠️ Request error ({i+1}/3) for {url}: {e}")
            time.sleep(2)
    return None

def download_file(url, folder, filename):
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        return
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        with open(file_path, "wb") as f:
            f.write(r.content)
        print(f"⬇️ Downloaded: {filename}")
    except Exception as e:
        print(f"❌ Failed to download {filename}: {e}")

def extract_year(session_name):
    """Try to extract a 4-digit year from the session name."""
    import re
    match = re.search(r'\b(20\d{2})\b', session_name)
    if match:
        return int(match.group(1))
    return None

def scrape_subject(level, subjects, papers_allowed):
    for subj in subjects:
        print(f"\n📘 Scraping {level}/{subj} ...")
        subj_url = f"{BASE_URL}/papers/caie/as-and-a-level-{subj}"
        soup = get_soup(subj_url)
        if not soup:
            print(f"⚠️ Skipping {subj_url}: could not fetch page")
            continue

        session_divs = soup.select("div.kt-widget4__item.item-folder-type a")
        if not session_divs:
            print(f"⚠️ No sessions found for {subj}")
            continue

        for sess in session_divs:
            session_name = sess.select_one("span.wraptext").get_text(strip=True)

            # Skip irrelevant sessions
            if "Topical" in session_name or "Tropical" in session_name:
                continue

            # Filter by year
            year = extract_year(session_name)
            if year and (year < START_YEAR or year > END_YEAR):
                continue

            session_url = BASE_URL + "/" + sess['href'].lstrip("/")
            print(f"📂 Session: {session_name}")

            session_soup = get_soup(session_url)
            if not session_soup:
                print(f"⚠️ No PDFs found in {session_name}")
                continue

            pdf_divs = session_soup.select("div.item-pdf-type")
            if not pdf_divs:
                print(f"⚠️ No PDFs found in {session_name}")
                continue

            for pdf in pdf_divs:
                paper_tag = pdf.select_one("span.badge-success, span.badge-danger")
                if not paper_tag:
                    continue
                paper_name = paper_tag.get_text(strip=True)
                if paper_name not in papers_allowed:
                    continue

                title_span = pdf.select_one("span.wraptext")
                if not title_span or "Question" not in title_span.get_text(strip=True):
                    continue

                download_link_tag = pdf.select_one("a.badge-info")
                if not download_link_tag:
                    continue
                file_url = download_link_tag['href']

                if "download_file.php?files=" in file_url:
                    import urllib.parse
                    parsed = urllib.parse.urlparse(file_url)
                    file_url = urllib.parse.parse_qs(parsed.query)['files'][0]

                filename = file_url.split("/")[-1]
                filename = requests.utils.unquote(filename)

                # Create session-level subfolder
                folder = os.path.join(level, subj, session_name)
                download_file(file_url, folder, filename)

def main():
    scrape_subject("AS_Level", AS_SUBJECTS, AS_PAPERS)
    scrape_subject("A_Level", A_SUBJECTS, A_PAPERS)
    print("\n🎉 All done!")

if __name__ == "__main__":
    main()
