#!/usr/bin/env python3
"""
Suomalaisten pienpanimoiden uutuusolutunnistin
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


def fetch_page_html() -> str:
    """Hakee suomenpienpanimot.fi etusivun Playwrightilla."""
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
        )
        context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        page = context.new_page()
        page.goto(BREWERY_URL, wait_until="domcontentloaded", timeout=45000)
        # Odotetaan että SOMEUUTISET-osio latautuu (max 20s)
        page.wait_for_selector("text=SOMEUUTISET", timeout=20000)
        # Pieni lisäodotus että Facebook-postaukset ehtivät renderöityä
        page.wait_for_timeout(4000)
        html = page.content()
        browser.close()
    return html


def extract_posts_from_html(html: str) -> list[dict]:
    """
    Poimii some-postaukset HTML:stä.
    Rakenne:
      <a href="panimo-slug">Postauksen teksti</a>
      Julkaistu <span>X tuntia</span> sitten @ <a ...>Panimon Nimi</a>
    """
    posts = []

    soma_start = html.find("SOMEUUTISET")
    if soma_start == -1:
        print("SOMEUUTISET-osiota ei löydy")
        return posts

    soma_html = html[soma_start:]

    # Rakenne: <a href="slug">teksti</a> ... Julkaistu ... sitten @ panimo
    pattern = re.compile(
        r'<a href="([a-z0-9-]+)"[^>]*>\s*'   # <a href="panimo-slug">
        r'([\s\S]{20,600}?)'                   # postauksen teksti
        r'</a>\s*'                             # </a>
        r'</div>\s*'
        r'<div[^>]*>\s*Julkaistu\s+'          # Julkaistu
        r'<span[^>]*>([^<]+)</span>'           # <span>X tuntia</span>
        r'\s*sitten\s*@\s*'
        r'<a[^>]*>([^<]+)</a>',               # <a>Panimon Nimi</a>
        re.DOTALL
    )

    for match in pattern.finditer(soma_html):
        slug = match.group(1).strip()
        teksti_raw = match.group(2).strip()
        aika = match.group(3).strip()
        panimo = match.group(4).strip()

        # Puhdistetaan HTML-tagit tekstistä
        teksti = re.sub(r'<[^>]+>', '', teksti_raw)
        teksti = re.sub(r'\s+', ' ', teksti).strip()

        # Suodatetaan pois liian lyhyet
        if len(teksti) < 20:
            continue

        posts.append({
            "panimo": panimo,
            "teksti": teksti[:500],
            "aika": aika,
            "slug": slug
        })

    print(f"Pattern löysi {len(posts)} postausta")

    # Jos pattern ei toiminut, kokeillaan löyhempää versiota
    if not posts:
        print("Yritetään löyhempää patternilla...")
        pattern2 = re.compile(
            r'Julkaistu\s+<span[^>]*>([^<]+)</span>\s*sitten\s*@\s*<a[^>]*>([^<]+)</a>',
            re.DOTALL
        )
        # Etsi Julkaistu-kohdat ja poimi teksti edeltä
        for match in pattern2.finditer(soma_html):
            aika = match.group(1).strip()
            panimo = match.group(2).strip()
            # Etsi edeltävä teksti: viimeisin <a href="slug">...</a> ennen tätä
            before = soma_html[:match.start()]
            prev_a = re.search(
                r'<a href="([a-z0-9-]+)"[^>]*>([\s\S]{20,500}?)</a>\s*</div>\s*<div[^>]*>\s*$',
                before
            )
            if prev_a:
                slug = prev_a.group(1)
                teksti = re.sub(r'<[^>]+>', '', prev_a.group(2))
                teksti = re.sub(r'\s+', ' ', teksti).strip()
                if len(teksti) >= 20:
                    posts.append({
                        "panimo": panimo,
                        "teksti": teksti[:500],
                        "aika": aika,
                        "slug": slug
                    })

        print(f"Löyhempi pattern löysi {len(posts)} postausta")

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
        posts_text += f"Slug: {post['slug']}\n"

    prompt = f"""Analysoi nämä suomalaisten pienpanimoiden some-postaukset ja tunnista AINOASTAAN ne, joissa julkaistaan uusi olut tai uusi erä.

HYVÄKSY (uutuusolut):
- Uuden oluen julkaisu nimellä, tyylillä ja/tai humalaluettelolla
- Selkeä "uutuus"-ilmoitus nimettynä tuotteena
- "Nyt saatavilla", "juuri tullut", "julkaisemme" + tuotenimi
- Viikon olut tai tuoreolut jota kuvataan yksityiskohtaisesti

HYLKÄÄ (ei uutuusolut):
- Tapahtumat, konsertit, festivaalit, aukioloajat, lounasmainokset
- Yleinen tunnelmajuttu tai brändimainonta
- Palkinnot jo olemassa olevista oluista
- Teaserviestit ilman tuotenimeä ("tulossa pian...")

Vastaa AINOASTAAN JSON-muodossa:
{{"uutuudet": [{{"panimo": "Panimon nimi", "olut": "Oluen nimi ja tyyli", "kuvaus": "max 100 merkkiä", "slug": "panimon-slug"}}]}}

Jos uutuuksia ei ole: {{"uutuudet": []}}

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
    html = fetch_page_html()
    print(f"HTML haettu, {len(html)} merkkiä")

    print("Poimitaan postaukset...")
    posts = extract_posts_from_html(html)
    print(f"Löytyi {len(posts)} postausta")

    if posts:
        print("Ensimmäiset 3 postausta:")
        for p in posts[:3]:
            print(f"  [{p['panimo']}] {p['teksti'][:80]}...")

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
