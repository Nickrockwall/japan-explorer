# Japan Explorer · Japan's 47 Prefectures Through the Ages

[中文](README.md) | **English** | [日本語](README.ja.md)

[![Checks](https://github.com/Nickrockwall/japan-explorer/actions/workflows/checks.yml/badge.svg)](https://github.com/Nickrockwall/japan-explorer/actions/workflows/checks.yml)

**▶ Try it online: https://nickrockwall.github.io/japan-explorer/**

![Japan Explorer](src/assets/og-cover-en.png)

Tap any prefecture on the map of Japan to see which ancient provinces it once belonged to and how it changed from the ritsuryō era to the present day. Drag the timeline through nine historical periods, replay famous battles on a sandbox map, and chat with an AI history guide whose persona changes from region to region.

The app is available in Chinese, English and Japanese.

## Features

| Feature | Description |
|---|---|
| **Then and now** | 47 prefectures ⇄ 68 ancient provinces (the Gokishichidō circuits); provinces split across several prefectures are tagged "cross-border" |
| **Six-stage history** | A timeline for every prefecture: Ritsuryō → Kamakura → Muromachi → Sengoku → Edo → Modern |
| **Map filters** | Exploration progress / modern regions / ancient circuits / Sengoku powers (1572) / Bakumatsu camps. "Ancient circuits" draws the **real borders** of the 68 provinces — see Musashi spanning Tokyo, Saitama and Kanagawa, or Settsu split between Osaka and Hyōgo — with prefecture borders dashed on top |
| **Time travel** | Drag the slider or press play to see the map and seat of power in nine eras, from Asuka to today |
| **Battle sandbox** | Okehazama, Kawanakajima, Sekigahara, Dan-no-ura and the Satsuma Rebellion, replayed in four phases (deployment → opening → turning point → outcome) and narrated by the commanders themselves |
| **Hiroshige prints** | All 69 prints of Hiroshige's *Famous Places in the Sixty-odd Provinces* (1853–56): click a province on the ancient map to see how Hiroshige painted it, and where the scene is today; the detail card lists the prints for each prefecture, viewable full size |
| **The name lives on** | 190 things across the 68 provinces that still carry the old name: the Shinano River, Sanuki udon, Iyokan citrus, Bizen ware, Satsuma sweet potatoes, the Ōmi Railway… shown in the ancient-map tooltip, the province card and the detail card; each one checked against Wikipedia for its name and location |
| **Food layers** | A ramen atlas (with a cut-away of each local bowl) and a map of famous sake |
| **Municipal map** | Drill into any prefecture to see all 1,900+ cities, towns and villages, colored by ancient province or by population; hover for reading, province, Meiji-era districts, today's district and population. The search box finds municipalities too (kanji, kana or English) with duplicates listed separately; place names on the map; the AI guide answers about the selected place; links can point straight at a municipality |
| **Pilgrimage** | A fourth layer of anime pilgrimage spots and NHK taiga-drama locations, filterable by type; tap a pin for the work, the location, the scene and visiting tips, and the AI guide talks about them like an otaku or a drama critic. Every spot's coordinates and work–place link are checked against Wikipedia (111 spots across all 47 prefectures) |
| **Goshuin book** | Collect a stamp for every prefecture you visit — 47 family-crest seals in all |
| **Local rivalries** | Light-hearted regional in-jokes and friendly rivalries |
| **AI history guide** | A scholar whose persona changes by region (a Heian court lady, an ukiyo-e cat, a Ryukyu priestess…) ⇄ a famous local warlord speaking in the first person; works offline without an API key |
| **Japanese-style sound** | A bamboo tap when you pick a region or change era, a deep taiko hit when you stamp, taiko and a conch-shell horn when a battle begins, and drums at each clash; optional background music (koto improvising in the miyako-bushi scale, never the same twice) can be turned on in Settings. Everything is synthesised live in the browser — no audio files; the speaker in the top bar mutes all |
| **Three languages** | 中文 / English / 日本語 — follows your browser language on first visit; switch any time in the top-right corner |
| **Sharing** | A Share button on the detail card; links keep the region and language, e.g. `#pref=26&lang=en` opens Kyoto in English |
| **Mobile & install** | On phones, a bottom tab bar switches between Map, Details and Guide, each full-screen; "Add to Home Screen" opens it full-screen like an app, and pages you have viewed work offline |

## 📜 Patch Notes

> Adventurers, a new version has arrived. Here are all past announcements (latest first).

### 🏷️ v2.4 "The Name Lives On"
- **190 things that still carry an old province name!** The Shinano River, Sanuki udon, Iyokan citrus, Bizen ware, Satsuma sweet potatoes, the Ōmi Railway… names you hear every day turn out to be over a thousand years old
- Hover a province on the ancient map to see them, or click for the full list; the detail card gets a "The name lives on" section for the provinces in each prefecture
- Nicknames count too: Shinshū soba (Shinano), Kōshū wine (Kai), Kishū plums (Kii), Banshū abacuses (Harima)…
- Every entry is checked against Wikipedia: the name really contains the province's name, places and landscapes really lie in that province, and goods' articles really mention the province or prefecture — anything that doesn't check out is left out

### 🎨 v2.3 "Hiroshige's Sixty-odd Provinces"
- **All 69 prints of Hiroshige's *Famous Places in the Sixty-odd Provinces* are in!** One per province, plus Edo
- Click a province on the "Ancient circuits" map to see Hiroshige's view of it; Musashi also has the Year-End Market at Asakusa
- Each print shows where the scene is today, down to the city (located from Wikipedia coordinates; where the spot is unknown, it says so)
- New "through Hiroshige's eyes" section on the detail card; click a thumbnail for the full print and browse with ‹ › or the arrow keys
- The prints are public domain; images come from Wikimedia Commons and ship with the site, so they load in China too

### 🗾 v2.2 "Sixty-Eight Provinces"
- **The "Ancient circuits" filter is now a real map of the old provinces!** Instead of painting today's prefectures, the map draws the 68 provinces as they were
- Musashi spans Tokyo, Saitama and Kanagawa; Settsu is split between Osaka and Hyōgo — prefecture borders are dashed on top, so then and now line up at a glance
- Province names on the map, with more appearing as you zoom; hover for the reading, the circuit and the prefectures it covers today
- Clicking still selects the prefecture you clicked in
- Borders are pieced together from 1,900+ municipalities by province (a municipality spanning two provinces goes to the main one, so they are approximate)

### 🥁 v2.1 "Taiko & Koto"
- **Sound effects are live!** A bamboo *tok* on the map, a *dong* of taiko on every stamp, a conch-shell horn to open each battle and war drums at every clash
- New background music: koto improvising in the miyako-bushi scale, never repeating (off by default — turn it on under Sound in ⚙ Settings, with separate music and effects volume)
- New speaker button in the top bar: one-tap mute, remembered; music fades out when the tab goes to the background
- All sounds are synthesised live in the browser, zero downloads; if audio fails, the map keeps working (covered by a dedicated test)
- Works on phones from the first tap; on iPhone (iOS 16.4+) you'll hear it even in silent mode, and like video sites it pauses music from other apps — tap the speaker to mute

### 🌸 v2.0 "Pilgrimage" Expansion
- **New layer "Pilgrimage" unlocked!** 111 anime pilgrimage spots and NHK taiga-drama locations across all 47 prefectures
- Pins glow and breathe: sakura pink for anime, antique gold for taiga dramas; filter by All / Anime / Taiga
- Tap a pin and the camera glides in, opening a card with the scene and pilgrim's tips
- New "Pilgrimage Guide" in the detail panel; the AI guide learns two new voices: 🔥 hot-blooded otaku and 🎬 drama critic
- Every coordinate and work–place link verified against Wikipedia — about 10 fake pilgrimage sites were purged by the system

### 🛡️ v1.9 "Shield & Portal"
- New automated check system: every update must pass data checks and 51 live browser tests — **no pass, no release**
- Fixed: the map freezing on networks where CDNs are blocked (the map engine now ships with the site; loads in 0.5s)
- Fixed: legend and banner jumping when switching eras; the search list running off-screen on phones

### 🗺️ v1.8 "Map of a Thousand Towns"
- Drill-down map opened: 1,900+ municipalities, colored by ancient province or population, with place names
- Added Meiji-era former districts; the province table cross-checked at about 1,350 municipalities
- Search upgraded: kanji (simplified too), kana and English; duplicate names listed separately; share links straight to a municipality
- Phones now switch between Map / Details / Guide tabs

### 📱 v1.7 "Pocket Scroll"
- Add to Home Screen, works offline; share links carry the language
- Phone layout overhaul, notch-safe and landscape-ready
- Data bundling: first load down from about 100 requests to 2

### 🌏 v1.6 "Trilingual Pass"
- English and Japanese unlocked, all 47 prefectures fully translated; first visit follows your browser language

### ⚔️ v1.5 "Battle Sandbox"
- Five famous battles replayed in four phases — deployment, opening, turning point, outcome — narrated by the commanders
- Time-travel slider: nine eras from Asuka to today

### 🍜 v1.4 "Food Atlas"
- Two new layers: the ramen atlas and the sake map

### 🏯 v1.0 "Launch"
- 47 prefectures ⇄ 68 ancient provinces, six-stage timelines, the goshuin book, and an AI history guide that changes persona by region

## Connecting an AI (optional)

You can use the app without an AI service: quick questions and common questions are answered from local data, in the guide's voice. For free-form conversation, click **API Settings** in the top-right corner and enter your own key:

| Provider type | Use it for |
|---|---|
| Claude API | Anthropic |
| Gemini (native) | Google AI Studio keys, including the newer keys starting with `AQ.` |
| OpenAI-compatible | OpenAI, DeepSeek and any other service with a `/chat/completions` endpoint |

Use **Test connection** to check your settings. Your key is stored only in your own browser; requests go straight from your browser to the service you entered and never pass through this site.

## Using it on a phone

Open https://nickrockwall.github.io/japan-explorer/ in your phone's browser. To add it to your home screen:

- **iPhone (Safari):** tap the Share button → **Add to Home Screen**
- **Android (Chrome):** tap ⋮ → **Add to Home screen** / **Install app**

## Running locally

```bash
python -m http.server 8000   # or: npx serve .
```

Then open http://localhost:8000. Double-clicking `index.html` does not work, because the browser blocks data loading from `file://`.

## Editing the content

- Prefecture data: `src/data/prefectures/NN_slug.json` (the Chinese base text)
- English and Japanese translations: `src/data/i18n/{en,ja}/` (text fields only, layered over the Chinese base)
- Eras and battles: `src/data/historical_events.json`

**After changing any JSON file, rebuild the bundles.** The site reads the bundled files, not the individual ones:

```bash
python tools/build_bundle.py
```

The data schema and project conventions are documented in [CLAUDE.md](CLAUDE.md) (in Chinese).

## Automated checks and deployment

Every push to GitHub runs, in order:

1. **Data checks** (a few seconds): fields and values, translation structure, stale bundles, municipalities vs. the province table, and more
2. **UI tests** (~2 min): a real browser walks through the main features on desktop / tablet / phone in Chinese, English and Japanese
3. **Deploy**: only for `main`, and only when both previous steps pass; otherwise the site stays on the previous version, and failure screenshots can be downloaded from the run

See the badge above or the [Actions page](https://github.com/Nickrockwall/japan-explorer/actions). You can also run the checks locally:

```bash
python -X utf8 tools/check_data.py        # data & repo consistency, a few seconds
pip install playwright && python -m playwright install chromium   # first time
python -X utf8 tests/smoke.py             # UI smoke tests: desktop / tablet / phone × zh / en / ja, ~2 min
```

## Tech

- Plain HTML / CSS / ES modules — no framework, no npm dependencies
- Map: [Apache ECharts](https://echarts.apache.org/) 5.5.1, shipped with the site (`src/vendor/`, Apache-2.0) rather than loaded from a CDN, so the page also opens on networks where CDNs are blocked; Google Fonts are optional and fall back to system fonts
- Data: one bundled JSON file per language (`src/data/bundle/`), so first load needs only two data requests
- PWA: `manifest.webmanifest` + an offline cache in `sw.js`
- Hosting: GitHub Pages, published by GitHub Actions — a push to `main` is checked first and **goes live only if every check passes**; if anything fails, the site stays on the previous version

## Notes

History, local in-jokes, ramen and sake entries follow commonly accepted accounts. Some are approximations (for example, each prefecture is colored by its dominant power), and uncertain points are marked "according to one account" or "legend has it". The app is meant for casual exploration, not academic citation.

National map: source 「地球地図日本」 (Global Map Japan, Geospatial Information Authority of Japan), converted to GeoJSON by [dataofjapan/land](https://github.com/dataofjapan/land).

Municipal boundaries: 「国土数値情報（行政区域データ）」（国土交通省）を加工して作成 (Japan's Ministry of Land, Infrastructure, Transport and Tourism, simplified by [smartnews-smri/japan-topography](https://github.com/smartnews-smri/japan-topography)). Readings, population and English names come from [Wikidata](https://www.wikidata.org/) (CC0). Each municipality's ancient province comes from a hand-made table (`tools/province_overrides.json`) cross-checked against Wikidata and the former-district data; municipalities spanning several provinces use the main one. Former (Meiji-era) districts are compiled from the district articles of [Japanese Wikipedia](https://ja.wikipedia.org/) (CC BY-SA 4.0) into `tools/districts.json`; refresh with `python -X utf8 tools/fetch_districts.py`. Rebuild with `python -X utf8 tools/build_municipalities.py`. The 68 province borders (`src/data/provinces.json`) are merged from the municipalities by province: `pip install shapely`, then `python -X utf8 tools/build_provinces.py`. After adding or editing province names (`src/data/province_names.json`), run `python -X utf8 tools/province_names_tool.py verify`. Hiroshige prints (`src/data/hiroshige.json` and `src/assets/hiroshige/`): `pip install pillow`, then `python -X utf8 tools/fetch_hiroshige.py` (public domain only; scenes it cannot place, or places in the wrong province, are listed for manual review).

## Copyright & License

© 2026 Nickrockwall

- **Code** (HTML / CSS / JS / Python tools and tests): [MIT](LICENSE) — use, modify and use commercially; just keep the copyright notice
- **Content** (historical text, guide personas and answers, translations, cover images and icons): [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — share and adapt with credit to "Japan Explorer by Nickrockwall" and a link to this project, **non-commercial only**; for commercial use, open a GitHub issue first
- **Third-party material** keeps its own terms: ECharts (Apache-2.0), map boundaries (Global Map Japan / 国土数値情報), Wikidata (CC0), former-district data (Japanese Wikipedia, CC BY-SA 4.0)

See [LICENSE-CONTENT.md](LICENSE-CONTENT.md) for the full scope and third-party list.
