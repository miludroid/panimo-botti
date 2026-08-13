#!/usr/bin/env python3
"""
Suomalaisten pienpanimoiden uutuusolutunnistin
Hakee suomenpienpanimot.fi:n some-postaukset Playwrightilla ja
tunnistaa uutuudet Claude API:n avulla. Lähettää löydöt Discordiin.
"""

import os
import re
import sys
import json
import requests
from datetime import datetime
from anthropic import Anthropic
from playwright.sync_api import sync_playwright

BREWERY_URL = "https://suomenpienpanimot.fi/"
DISCORD_WEBHOOK_URL = os.environ["DISCORD_WEBHOOK_URL"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]

client = Anthropic(api_key=ANTHROPIC_API_KEY)


def fetch_brewery_posts() -> str:
    """Hakee suomenpienpanimot.fi etusivun sisällön Playwrightilla."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            locale="fi-FI",
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "fi-FI,fi;q=0.9,en;q=0.8",
            }
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()
        page.goto(BREWERY_URL, wait_until="networkidle", timeout=45000)
        # Odotetaan että some-postaukset latautuvat
        page.wait_for_selector("text=SOMEUUTISET", timeout=15000)
        html = page.content()
        browser.close()
    return html


def extract_posts_from_html(html: str) -> list[dict]:
    """Poimii some-postaukset HTML:stä."""
    posts = []

    soma_start = html.find("SOMEUUTISET")
    if soma_start == -1:
        print("SOMEUUTISET-osiota ei löydy sivulta")
        return posts

    soma_html = html[soma_start:]

    # Rakenne: [teksti](panimo-url) + Julkaistu X sitten @ [Panimo](url)
    pattern = re.compile(
        r'\[([^\]]{20,600}?)\]\(https://suomenpienpanimot\.fi/[^)]+\)\s*'
        r'Julkaistu ([^\n@]{1,40})@ \[([^\]]+)\]',
        re.DOTALL
    )

    for match in pattern.finditer(soma_html):
        teksti = match.group(1).strip()
        aika = match.group(2).strip()
        panimo = match.group(3).strip()

        if len(teksti) < 20:
            continue

        posts.append({
            "panimo": panimo,
            "teksti": teksti[:500],
            "aika": aika
        })

    return posts


def analyze_with_claude(posts: list[dict]) -> list[dict]:
    """Käyttää Claude API:a tunnistamaan uutuusolut postauksista."""
    if not posts:
        return []

    posts_text = ""
    for i, post in enumerate(posts):
        posts_text += f"\n---POSTAUS {i+1}---\n"
        posts_text += f"Panimo: {post['panimo']}\n"
        posts_text += f"Aika: {post['aika']}\n"
        posts_text += f"Teksti: {post['teksti']}\n"

    prompt = f"""Analysoi nämä suomalaisten pienpanimoiden some-postaukset ja tunnista AINOASTAAN ne, joissa julkaistaan uusi olut tai uusi erä.

HYVÄKSY (uutuusolut):
- Uuden oluen julkaisu nimellä, tyylillä ja/tai humalaluettelolla
- Selkeä "uutuus"-ilmoitus nimettynä tuotteena
- "Nyt saatavilla", "juuri tullut", "julkaisemme" + tuotenimi
- Viikon olut tai tuoreolut jota kuvataan yksityiskohtaisesti

HYLKÄÄ (ei uutuusolut):
- Tapahtumat, konsertit, festivaalit
- Aukioloajat
- Lounasmainokset
- Yleinen tunnelmajuttu tai brändimainonta
- Palkinnot jo olemassa olevista oluista
- Teaserviestit ilman tuotenimeä ("tulossa pian...")
- Festarimainonta jossa listataan jo tunnettuja tuotteita

Vastaa AINOASTAAN JSON-muodossa, ei muuta tekstiä:
{{"uutuudet": [{{"panimo": "Panimon nimi", "olut": "Oluen nimi ja tyyli", "kuvaus": "Lyhyt kuvaus max 100 merkkiä", "slug": "panimon-slug-urlista"}}]}}

Jos uutuuksia ei ole, palauta: {{"uutuudet": []}}

POSTAUKSET:
{posts_text}"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}]
    )

    result_text = response.content[0].text.strip()
    result_text = re.sub(r"```json\s*", "", result_text)
    result_text = re.sub(r"```\s*", "", result_text)

    try:
        result = json.loads(result_text)
        return result.get("uutuudet", [])
    except json.JSONDecodeError as e:
        print(f"JSON-parsintavirhe: {e}\nClaude vastasi: {result_text}")
        return []


def send_to_discord(uutuudet: list[dict]) -> None:
    """Lähettää uutuusolut Discord-kanavalle."""
    if not uutuudet:
        print("Ei uutuusoluita tänään — Discord-viestiä ei lähetetä.")
        return

    today = datetime.now().strftime("%-d.%-m.%Y")
    lines = [f"🍺 **Uutuusolut {today}**\n"]

    for u in uutuudet:
        lines.append(f"**{u['panimo']}**")
        lines.append(f"🆕 {u['olut']}")
        if u.get("kuvaus"):
            lines.append(f"_{u['kuvaus']}_")
        if u.get("slug"):
            lines.append(f"https://suomenpienpanimot.fi/{u['slug']}")
        lines.append("")

    message = "\n".join(lines)
    if len(message) > 2000:
        message = message[:1997] + "..."

    response = requests.post(
        DISCORD_WEBHOOK_URL,
        json={"content": message},
        timeout=10
    )
    response.raise_for_status()
    print(f"Discord-viesti lähetetty! ({len(uutuudet)} uutuutta)")


def main():
    print(f"Panimo-botti käynnistyy: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print("Haetaan postaukset Playwrightilla...")
    html = fetch_brewery_posts()

    print("Poimitaan postaukset...")
    posts = extract_posts_from_html(html)
    print(f"Löytyi {len(posts)} postausta")

    if not posts:
        print("Ei postauksia löydetty — lopetetaan.")
        sys.exit(0)

    print("Analysoidaan Claude API:lla...")
    uutuudet = analyze_with_claude(posts)
    print(f"Tunnistettiin {len(uutuudet)} uutuusolutta")

    for u in uutuudet:
        print(f"  ✓ {u['panimo']}: {u['olut']}")

    send_to_discord(uutuudet)
    print("Valmis!")


if __name__ == "__main__":
    main()
