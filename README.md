# 🍺 Panimo-botti

Seuraa suomalaisten pienpanimoiden uutuusoluita [suomenpienpanimot.fi](https://suomenpienpanimot.fi):stä ja lähettää löydöt Discord-kanavalle päivittäin.

## Miten se toimii

1. GitHub Actions ajaa botin joka päivä klo 20:00 (Suomen aikaa)
2. Botti hakee suomenpienpanimot.fi:n some-postaukset
3. Claude AI analysoi postaukset ja tunnistaa uutuusolut
4. Jos uutuuksia löytyy, ne lähetetään Discord-kanavalle

## Asennus

### 1. Luo GitHub-repositorio

Mene [github.com/new](https://github.com/new) ja luo uusi repositorio nimellä esim. `panimo-botti`.

### 2. Lisää tiedostot

Lataa tai kopioi nämä tiedostot repositorioosi:
- `panimo_bot.py`
- `.github/workflows/panimo_bot.yml`

### 3. Lisää GitHub Secrets

Mene repositoriosi asetuksiin:
**Settings → Secrets and variables → Actions → New repository secret**

Lisää kaksi secretia:

| Nimi | Arvo |
|------|------|
| `DISCORD_WEBHOOK_URL` | Discord webhook URL (kanavan asetuksista) |
| `ANTHROPIC_API_KEY` | Anthropic API-avain (console.anthropic.com) |

### 4. Testaa manuaalisesti

Mene **Actions**-välilehdelle → **Panimo-botti** → **Run workflow**

Näet lokin reaaliajassa — jos uutuuksia löytyy, Discord-viesti lähtee saman tien.

### 5. Valmis!

Botti ajaa automaattisesti joka päivä klo 20:00.

## Discord-viestin esimerkki

```
🍺 Uutuusolut tänään 13.8.2026

**Panimoyhtiö Tuju**
🆕 Lamatanssit 8,0% | West Coast DIPA
_Nectaron, Cryo Simcoe, Idaho 7 — uusi tölkki- ja hanauutuus_
https://suomenpienpanimot.fi/panimoyhtio-tuju

**Vakka-Suomen Panimo**
🆕 El Dorado Tropical Fruit Pale ALE
_Trooppinen pale ale El Dorado -humalalla_
https://suomenpienpanimot.fi/vakka-suomen-panimo
```

## Kustannukset

- GitHub Actions: ilmainen (julkisissa repositorioissa rajoittamaton)
- Anthropic API: ~0–1 € / kuukausi tällä käyttöasteella
