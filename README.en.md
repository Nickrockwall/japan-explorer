# Japan Explorer · Japan's 47 Prefectures Through the Ages

[中文](README.md) | **English** | [日本語](README.ja.md)

**▶ Try it online: https://nickrockwall.github.io/japan-explorer/**

![Japan Explorer](src/assets/og-cover-en.png)

Tap any prefecture on the map of Japan to see which ancient provinces it once belonged to and how it changed from the ritsuryō era to the present day. Drag the timeline through nine historical periods, replay famous battles on a sandbox map, and chat with an AI history guide whose persona changes from region to region.

The app is available in Chinese, English and Japanese.

## Features

| Feature | Description |
|---|---|
| **Then and now** | 47 prefectures ⇄ 68 ancient provinces (the Gokishichidō circuits); provinces split across several prefectures are tagged "cross-border" |
| **Six-stage history** | A timeline for every prefecture: Ritsuryō → Kamakura → Muromachi → Sengoku → Edo → Modern |
| **Map filters** | Exploration progress / modern regions / ancient circuits / Sengoku powers (1572) / Bakumatsu camps |
| **Time travel** | Drag the slider or press play to see the map and seat of power in nine eras, from Asuka to today |
| **Battle sandbox** | Okehazama, Kawanakajima, Sekigahara, Dan-no-ura and the Satsuma Rebellion, replayed in four phases (deployment → opening → turning point → outcome) and narrated by the commanders themselves |
| **Food layers** | A ramen atlas (with a cut-away of each local bowl) and a map of famous sake |
| **Goshuin book** | Collect a stamp for every prefecture you visit — 47 family-crest seals in all |
| **Local rivalries** | Light-hearted regional in-jokes and friendly rivalries |
| **AI history guide** | A scholar whose persona changes by region (a Heian court lady, an ukiyo-e cat, a Ryukyu priestess…) ⇄ a famous local warlord speaking in the first person; works offline without an API key |
| **Three languages** | 中文 / English / 日本語 — follows your browser language on first visit; switch any time in the top-right corner |
| **Sharing** | A Share button on the detail card; links keep the region and language, e.g. `#pref=26&lang=en` opens Kyoto in English |
| **Mobile & install** | Phone-friendly layout; "Add to Home Screen" opens it full-screen like an app, and pages you have viewed work offline |

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

## Tech

- Plain HTML / CSS / ES modules — no framework, no npm dependencies
- Map: [Apache ECharts](https://echarts.apache.org/) 5.5.1, loaded from a CDN with fallback mirrors
- Data: one bundled JSON file per language (`src/data/bundle/`), so first load needs only two data requests
- PWA: `manifest.webmanifest` + an offline cache in `sw.js`
- Hosting: GitHub Pages — every push to `main` goes live automatically

## Notes

History, local in-jokes, ramen and sake entries follow commonly accepted accounts. Some are approximations (for example, each prefecture is colored by its dominant power), and uncertain points are marked "according to one account" or "legend has it". The app is meant for casual exploration, not academic citation.

Map data: [dataofjapan/land](https://github.com/dataofjapan/land).
