import json
import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


URL = "https://servizi.istruzionepiemonte.it/interpello2026/ric_interpello_ambito_al.php"
SEEN_FILE = "seen.json"

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()

    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_seen(seen):
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(seen), f, ensure_ascii=False, indent=2)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": False
        },
        timeout=30
    )

    response.raise_for_status()


def scrape():
    response = requests.get(
        URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    soup = BeautifulSoup(
        response.text,
        "html.parser"
    )

    interpelli = []

    for table in soup.find_all("table"):

        rows = table.find_all("tr")

        # Saltiamo l'header
        for row in rows[1:]:

            cells = row.find_all("td")

            if len(cells) < 12:
                continue

            # ID progressivo
            hidden = row.find("input", {
                "type": "hidden",
                "name": "progr"
            })

            if not hidden:
                # Interpello cancellato
                continue

            progr = hidden.get("value")

            values = [
                cell.get_text(" ", strip=True)
                for cell in cells
            ]

            scuola_codice = values[0]
            scuola = values[1]
            classe = values[2]
            tipo_cattedra = values[3]
            corso = values[4]
            durata = values[5]
            data_interpello = values[6]
            stato = values[8]
            scadenza = values[9]

            # Consideriamo solo interpelli aperti
            if stato.lower() != "aperto":
                continue

            interpelli.append({
                "id": progr,
                "scuola_codice": scuola_codice,
                "scuola": scuola,
                "classe": classe,
                "tipo_cattedra": tipo_cattedra,
                "corso": corso,
                "durata": durata,
                "data_interpello": data_interpello,
                "scadenza": scadenza,
                "url": URL
            })

    return interpelli


def main():

    print("Controllo interpelli...")

    seen = load_seen()

    interpelli = scrape()

    print(f"Interpelli aperti trovati: {len(interpelli)}")

    # Prima esecuzione:
    # salviamo tutti quelli già presenti senza notificare nulla.
    if not seen:

        print("Prima esecuzione: inizializzazione.")

        for interpello in interpelli:
            seen.add(interpello["id"])

        save_seen(seen)

        print("Inizializzazione completata.")
        return

    nuovi = []

    for interpello in interpelli:

        if interpello["id"] not in seen:
            nuovi.append(interpello)

    for interpello in nuovi:

        message = (
            "🚨 NUOVO INTERPELLO\n\n"
            f"🏫 {interpello['scuola']}\n"
            f"📚 {interpello['classe']}\n"
            f"📝 {interpello['tipo_cattedra']}\n"
            f"🌞 {interpello['corso']}\n"
            f"📅 Durata: {interpello['durata']}\n"
            f"📆 Pubblicato: {interpello['data_interpello']}\n"
            f"⏰ Scadenza: {interpello['scadenza']}\n\n"
            f"🔗 {interpello['url']}"
        )

        send_telegram(message)

        print(
            f"Nuovo interpello notificato: "
            f"{interpello['id']} - {interpello['classe']}"
        )

        seen.add(interpello["id"])

    save_seen(seen)

    print(f"Nuovi interpelli: {len(nuovi)}")


if __name__ == "__main__":
    main()
