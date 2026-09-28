"""Turns a link the editor pasted (a paper, PDF or article) into an Item."""
import hashlib
import re

from bs4 import BeautifulSoup

from .sources import Item, get

ARXIV_RE = re.compile(r"arxiv\.org/(?:abs|pdf)/([\w.\-/]+?)(?:v\d+)?(?:\.pdf)?$")


def item_from_url(url):
    url = url.strip()
    item_id = f"link:{hashlib.sha1(url.encode()).hexdigest()[:16]}"
    arxiv = ARXIV_RE.search(url)
    if arxiv:
        abs_url = f"https://arxiv.org/abs/{arxiv.group(1)}"
        soup = BeautifulSoup(get(abs_url).text, "html.parser")
        title = soup.find("meta", attrs={"name": "citation_title"})
        abstract = soup.find("meta", attrs={"name": "citation_abstract"})
        return Item(
            id=f"arxiv:{arxiv.group(1)}", title=title["content"] if title else abs_url, url=abs_url,
            summary=abstract["content"] if abstract else "", source="arXiv",
            pdf_url=f"https://arxiv.org/pdf/{arxiv.group(1)}", is_paper=True,
        )
    if url.lower().split("?")[0].endswith(".pdf"):
        return Item(id=item_id, title=url.rsplit("/", 1)[-1], url=url, source="PDF", pdf_url=url, is_paper=True)

    soup = BeautifulSoup(get(url).text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
        tag.decompose()
    og = soup.find("meta", property="og:title")
    title = og["content"] if og and og.get("content") else (soup.title.string.strip() if soup.title and soup.title.string else url)
    site = soup.find("meta", property="og:site_name")
    text = " ".join((soup.find("article") or soup.body or soup).get_text(" ").split())
    return Item(id=item_id, title=title, url=url, summary=text[:8000], source=site["content"] if site else "Web")
