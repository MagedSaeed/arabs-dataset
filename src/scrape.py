import requests
from pathlib import Path
from bs4 import BeautifulSoup
import re
import os
import time
import json
from tqdm.auto import tqdm
from requests.exceptions import RequestException


def clean_and_truncate_filename(title, max_length=100):
    # Clean the title by replacing multiple spaces with a single space
    cleaned_title = re.sub(r"\s+", " ", title.strip())

    # Replace any characters that are not allowed in filenames
    cleaned_title = re.sub(r'[<>:"/\\|?*]', "_", cleaned_title)

    # Truncate the title if it's too long, preserving the file extension
    name, ext = os.path.splitext(cleaned_title)
    if len(name) > max_length - len(ext):
        name = name[: max_length - len(ext) - 3] + "..."
    return name + ext


def make_request_with_retry(url, max_retries=5, delay=30):
    for attempt in range(max_retries):
        try:
            response = requests.get(url)
            if 400 <= response.status_code < 500:
                # return None on 4xx status codes
                return None
            response.raise_for_status()  # Raises an HTTPError for bad responses
            return response
        except RequestException as e:
            print(f"Error accessing {url}: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                print(f"Max retries reached for {url}")
                return None


articles_folder = Path("articles")
articles_folder.mkdir(parents=True, exist_ok=True)

for i in range(0, 1000):
    journal_url = f"https://www.asjp.cerist.dz/en/Articles/{i}"
    response = make_request_with_retry(journal_url)
    if response is None:
        continue

    soup = BeautifulSoup(response.content, "html.parser")
    if not soup.find("aside"):
        continue

    # Get the journal title
    journal_title = soup.find("aside").find("a").text.strip()

    arabic_letters = [
        "ا",
        "ب",
        "ت",
        "ث",
        "ج",
        "ح",
        "خ",
        "د",
        "ذ",
        "ر",
        "ز",
        "س",
        "ش",
        "ص",
        "ض",
        "ط",
        "ظ",
        "ع",
        "غ",
        "ف",
        "ق",
        "ك",
        "ل",
        "م",
        "ن",
        "ه",
        "و",
        "ي",
    ]
    if len(set(journal_title).intersection(set(arabic_letters))) == 0:
        continue

    print("processing journal:", i, "-", journal_title)
    asjp_folder = articles_folder / clean_and_truncate_filename(
        f"asjp-{i}-{journal_title}"
    )
    asjp_folder.mkdir(exist_ok=True)
    volumes_divs = soup.find("aside").find("div").find_all("div", recursive=False)
    volumes_headers = soup.find("aside").find("div").find_all("h2", recursive=False)
    for volume_div, volume_header in zip(volumes_divs, volumes_headers):
        _, volume_number, volume_year = list(filter(None, volume_header.text.split()))
        volume_folder = asjp_folder / f"volume-{volume_number}-year-{volume_year}"
        volume_folder.mkdir(parents=True, exist_ok=True)

        issues_divs, issues_headers = (
            volume_div.find_all("div", recursive=False),
            volume_div.find_all("h3", recursive=False),
        )
        for issues_div, issue_header in zip(issues_divs, issues_headers):
            _, issue_number, issue_date, *_ = list(
                filter(None, issue_header.text.strip().split())
            )
            print("- Volume:", volume_number, "Issue:", issue_number)
            issue_folder = volume_folder / f"issue-{issue_number}-date-{issue_date}"
            issue_folder.mkdir(parents=True, exist_ok=True)
            articles_elements = issues_div.find_all("h4")
            for article_div in tqdm(articles_elements):
                article_element = article_div.find("a")
                article_title = article_element.text.strip()
                article_link = article_element["href"]

                # Clean and truncate the article title
                cleaned_title = clean_and_truncate_filename(article_title)
                pdf_file = issue_folder / f"{cleaned_title}.pdf"
                json_file = issue_folder / f"{cleaned_title}.json"
                pdf_already_downloaded = False
                try:
                    # Check if the file already exists
                    if pdf_file.exists():
                        pdf_already_downloaded = True
                    if json_file.exists() and pdf_already_downloaded:
                        continue
                    article_response = make_request_with_retry(article_link)
                    if article_response is None:
                        continue
                    article_soup = BeautifulSoup(
                        article_response.content,
                        "html.parser",
                    )
                    pdf_button = article_soup.find("button", string="Article en ligne")
                    if pdf_button and pdf_button.parent and not pdf_already_downloaded:
                        pdf_link = pdf_button.parent["href"]
                        pdf_response = make_request_with_retry(pdf_link)
                        if pdf_response is None:
                            continue
                        with open(pdf_file, "wb") as f:
                            f.write(pdf_response.content)
                    # Find abstract
                    abstract_element = article_soup.find(
                        "h3",
                        string=lambda text: text and "الملخص" in text,
                    )
                    abstract_text, keywords_text, authors_text = None, None, None
                    if abstract_element:
                        # Use find_next_sibling to get the next <p> that shares the same parent
                        abstract_text = abstract_element.find_next_sibling(
                            "p"
                        ).text.strip()

                    # Find keywords
                    keywords_element = article_soup.find(
                        "h3",
                        string=lambda text: text and "الكلمات المفتاحية" in text,
                    )
                    if keywords_element:
                        keywords_text = keywords_element.find_next_sibling(
                            "p"
                        ).text.strip()

                    # Find author
                    author_element = article_soup.select_one(
                        "div.descarticle > div > p > b"
                    )
                    if author_element and "الكاتب" in author_element.text:
                        authors_list = []
                        for author_name_element in author_element.find_next_siblings(
                            "a"
                        ):
                            authors_list.append(author_name_element.text.strip())
                        authors_text = ", ".join(authors_list)
                    article_json_metadata = {
                        "url": article_link,
                        "journal_url": journal_url,
                        "volume": volume_number,
                        "issue": issue_number,
                        "issue_date": issue_date,
                        "title": article_title,
                        "authors": authors_text,
                        "abstract": abstract_text,
                        "keywords": keywords_text,
                    }
                    json.dump(
                        article_json_metadata,
                        json_file.open("w"),
                        ensure_ascii=False,
                        indent=4,
                    )
                except Exception as e:
                    print(f"Error downloading article: {e}")
                time.sleep(1)
