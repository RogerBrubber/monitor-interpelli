import json
import os
import hashlib
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


URL = "https://servizi.istruzionipiemonte.it/interpello2026/ric_interpello_ambito_al.php"

SEEN_FILE = "seen.json"

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/140 Safari/537.36"
    )
}


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()

    try:
        with open(SEEN_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def send_telegram(message):
    telegram_url = (
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    )

    response = requests.post(
        telegram_url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False,
        },
        timeout=30,
    )

    response.raise_for_status()


def create_id(text, href):
    value = f"{text}|{href}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def scrape():
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    results = []

    for link in soup.find_all("a", href=True):

        text = " ".join(link.stripped_strings)

        if not text:
            continue

        href = urljoin(URL, link["href"])

        # Per ora consideriamo tutti i link della pagina.
        # Dopo aver verificato l'HTML reale possiamo restringere
        # il filtro agli interpelli veri e propri.

        item_id = create_id(text, href)

        results.append({
            "id": item_id,
            "text": text,
            "url": href,
        })

    return results


def main():

    print("Controllo interpelli...")

    seen = load_seen()

    items = scrape()

    print(f"Elementi trovati: {len(items)}")

    new_items = [
        item
        for item in items
        if item["id"] not in seen
    ]

    # Prima esecuzione:
    # memorizziamo quello che esiste già senza bombardarti
    # di notifiche per tutti gli interpelli storici.
    if not seen:

        print("Prima esecuzione.")
        print(f"Memorizzo {len(items)} elementi esistenti.")

        for item in items:
            seen.add(item["id"])

        save_seen(seen)

        return

    for item in new_items:

        message = (
            "🚨 NUOVO INTERPELLO\n\n"
            f"{item['text']}\n\n"
            f"🔗 {item['url']}"
        )

        send_telegram(message)

        print(f"Notificato: {item['text']}")

        seen.add(item["id"])

    save_seen(seen)

    print(f"Nuovi elementi: {len(new_items)}")


if __name__ == "__main__":
    main()