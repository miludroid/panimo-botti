# 🍺 Panimo-botti

Seuraa suomalaisten pienpanimoiden uutuusoluita [suomenpienpanimot.fi](https://suomenpienpanimot.fi):stä ja lähettää löydöt Discord-kanavalle päivittäin.

## Miten se toimii

1. GitHub Actions ajaa botin joka päivä klo 20:00 (Suomen aikaa)
2. Playwright-selain hakee suomenpienpanimot.fi:n some-postaukset
3. Claude AI analysoi postaukset ja tunnistaa uutuusolut
4. Jos uutuuksia löytyy, ne lähetetään Discord-kanavalle
5. Jo postatut oluet tallennetaan muistiin — samaa olutta ei postata kahdesti

## Mitä botti hyväksyy

- Uuden oluen julkaisu nimellä, tyylillä ja/tai humalaluettelolla
- Selkeä uutuusilmoitus nimettynä tuotteena
- "Nyt saatavilla", "juuri tullut", "julkaisemme" + tuotenimi

## Mitä botti hylkää

- Tapahtumat, konsertit, festivaalit, aukioloajat, lounasmainokset
- Yleinen tunnelmajuttu tai brändimainonta
- Palkinnot jo olemassa olevista oluista
- Teaserviestit ilman tuotenimeä ("tulossa pian...")
- "Viikon olut" -tyyppiset nostot vakiotuotteista

## Tiedostorakenne

```
panimo-botti/
├── panimo_bot.py                    # Pääskripti
├── seen_beers.json                  # Muistilista (GitHub Actions cache)
├── README.md
└── .github/
    └── workflows/
        └── panimo_bot.yml           # GitHub Actions ajastus
```

## Asennus

### 1. GitHub Secrets

Mene repositorion **Settings → Secrets and variables → Actions → New repository secret**

| Nimi | Arvo |
|------|------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL (kanavan asetuksista) |
| `ANTHROPIC_API_KEY` | Anthropic API-avain (console.anthropic.com) |

### 2. Testaa manuaalisesti

**Actions → Panimo-botti → Run workflow**

Lokilta näet kuinka monta postausta löytyi ja lähetettiinkö Discord-viesti.

### 3. Automaattinen ajo

Botti ajaa automaattisesti joka päivä klo 20:00 ilman toimenpiteitä.

## Discord-viestin esimerkki

```
🍺 Uutuusolut 14.8.2026

**Panimoyhtiö Tuju**
🆕 Lamatanssit 8,0% | West Coast DIPA
_Nectaron, Cryo Simcoe, Idaho 7 — uusi tölkki- ja hanauutuus_

**Vakka-Suomen Panimo**
🆕 El Dorado Tropical Fruit Pale Ale
_Trooppinen pale ale El Dorado -humalalla_
```

## Kustannukset

- GitHub Actions: ilmainen
- Anthropic API: alle 1 € / kuukausi
