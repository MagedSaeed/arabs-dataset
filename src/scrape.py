import requests
from pathlib import Path
from bs4 import BeautifulSoup
import re
import os


def clean_and_truncate_filename(title, max_length=255):
    # Clean the title by replacing multiple spaces with a single space
    cleaned_title = re.sub(r"\s+", " ", title.strip())

    # Replace any characters that are not allowed in filenames
    cleaned_title = re.sub(r'[<>:"/\\|?*]', "_", cleaned_title)

    # Truncate the title if it's too long, preserving the file extension
    name, ext = os.path.splitext(cleaned_title)
    if len(name) > max_length - len(ext):
        name = name[: max_length - len(ext) - 3] + "..."
    return name + ext


articles_folder = Path("articles")
articles_folder.mkdir(parents=True, exist_ok=True)

for i in range(0, 1000):
    url = f"https://www.asjp.cerist.dz/en/Articles/{i}"
    volumes_page = requests.get(url).content
    soup = BeautifulSoup(volumes_page, "html.parser")
    if not soup.find("aside"):
        continue
    # Get the journal title
    journal_title = soup.find("aside").find("a").text.strip()
    print("processing journal:", i, "-", journal_title)
    asjp_folder = articles_folder / clean_and_truncate_filename(
        f"asjp-{i}-{journal_title}"
    )
    asjp_folder.mkdir(exist_ok=True)
    volumes_divs = soup.find("aside").find_all("div")
    for volume_div in volumes_divs:
        volume_element = volume_div.find("h2").text.strip()
        _, volume_number, volume_year = list(filter(None, volume_element.split()))
        volume_folder = asjp_folder / f"volume-{volume_number}-year-{volume_year}"
        issues_div = volume_div.find("div")
        issue_element = issues_div.find("h3").text
        _, issue_number, issue_date = list(filter(None, issue_element.split()))
        issue_folder = volume_folder / f"issue-{issue_number}-date-{issue_date}"
        issue_folder.mkdir(parents=True, exist_ok=True)
        articles_div = issues_div.find("div")
        for article_div in articles_div.find_all("h4"):
            article_element = article_div.find("a")
            article_title = article_element.text.strip()
            article_link = article_element["href"]
            article_page = requests.get(article_link).content
            article_soup = BeautifulSoup(article_page, "html.parser")
            pdf_link = article_soup.find("button", string="Article en ligne").parent[
                "href"
            ]
            pdf_response = requests.get(pdf_link)

            # Clean and truncate the article title
            cleaned_title = clean_and_truncate_filename(article_title)

            pdf_file = issue_folder / f"{cleaned_title}.pdf"
            with open(pdf_file, "wb") as f:
                f.write(pdf_response.content)
