import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor

BASE_URL = "https://pastpapers.papacambridge.com/"
HEADERS = {"User-Agent": "Mozilla/5.0"}
SAVE_DIR = "Past_Papers"
MAX_THREADS = 5  # safe number of concurrent downloads

SUBJECTS = {
    "O_Level_Physics": "papers/caie/o-level-physics-5054",
    "O_Level_Chemistry": "papers/caie/o-level-chemistry-5070",
    "O_Level_Biology": "papers/caie/o-level-biology-5090",
}


def get_soup(url):
    res = requests.get(url, headers=HEADERS)
    res.raise_for_status()
    return BeautifulSoup(res.text, "html.parser")


def download_pdf(pdf_url, folder):
    filename = os.path.join(folder, pdf_url.split("/")[-1])
    if os.path.exists(filename):
        return
    try:
        r = requests.get(pdf_url, stream=True, headers=HEADERS)
        if r.status_code == 200:
            with open(filename, "wb") as f:
                for chunk in r.iter_content(1024):
                    f.write(chunk)
            print(f"✅ Downloaded: {filename}")
    except Exception as e:
        print(f"❌ Error downloading {pdf_url}: {e}")


def scrape_pdfs(session_url, session_folder):
    soup = get_soup(session_url)
    pdf_blocks = soup.select(".item-pdf-type")
    tasks = []

    for pdf in pdf_blocks:
        title = pdf.get_text(strip=True).lower()

        # Only Question Papers (QP), Paper 1 & 2, skip MS/inserts/etc.
        if "question paper" not in title:
            continue
        if "mark scheme" in title or "insert" in title or "grade threshold" in title:
            continue
        badges = [b.get_text(strip=True).lower() for b in pdf.select(".badge")]
        if not any("paper 1" in b or "paper 2" in b for b in badges):
            continue

        download_tag = pdf.select_one('a[href*="download_file.php?files="]')
        if download_tag:
            pdf_url = download_tag["href"]
            if not pdf_url.startswith("http"):
                pdf_url = urljoin(BASE_URL, pdf_url)
            tasks.append((pdf_url, session_folder))

    # Multithreaded download
    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        for pdf_url, folder in tasks:
            executor.submit(download_pdf, pdf_url, folder)


def scrape_subject(subject_name, subject_path):
    subject_url = urljoin(BASE_URL, subject_path)
    subject_folder = os.path.join(SAVE_DIR, subject_name)
    os.makedirs(subject_folder, exist_ok=True)

    print(f"\n📘 Scraping {subject_name} from {subject_url}")
    soup = get_soup(subject_url)
    folders = soup.select('.item-folder-type a[href*="o-level-"], .item-folder-type a[href*="a-level-"]')

    if not folders:
        print("⚠️ No year/session folders found.")
        return

    for folder in folders:
        sub_link = folder.get("href")
        session_name = folder.get_text(strip=True).replace("/", "-")

        #Downloading papers range from 2017-2025 (Change as required)
        if not any(str(y) in session_name for y in range(2017, 2026)):
            continue
        session_folder = os.path.join(subject_folder, session_name)
        os.makedirs(session_folder, exist_ok=True)
        full_link = urljoin(BASE_URL, sub_link)
        print(f"\n📂 Opening {session_name}")
        scrape_pdfs(full_link, session_folder)
        time.sleep(0.5)  # small delay


if __name__ == "__main__":
    for subject, url in SUBJECTS.items():
        scrape_subject(subject, url)

    print("\n🎉 All subjects completed successfully (2025–2017, Paper 1 & 2 only).")
