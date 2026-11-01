# Changelog

[中文](CHANGELOG.md) | **English** | [日本語](CHANGELOG.ja.md)

Newest first.

## 2.11 · 2026-11-01

- The details card now shows each prefecture's emblem instead of an emoji (all 47 from Wikimedia Commons, public domain), drawn in gold; a seal with the old province names stands in if an emblem is missing
- The map tooltip shows the emblem before the prefecture name too
- On phones, buttons use short labels when the full text doesn't fit ("Stamp", "Stamped", "Towns"); the full text is in the tooltip

## 2.10 · 2026-11-01

- Quick tour: a 9-step introduction on first visit (map, details, guide, layers and filters, time travel, "Where am I?" and battles); replay it from settings or the welcome page
- Landscape phones: the toolbar and the legend/time slider each shrink to one row, leaving the middle to the map; cards sit on the right, the map moves aside for the battle panel, and rotating resets the view
- Smoother panning on the Ancient sites and Ancient circuits maps: prefecture borders are drawn in one pass (about 36 ms → 11 ms per frame on a slow phone)
- Ancient sites shows only ichinomiya when zoomed out; capitals and kokubunji appear as you zoom in
- New subtitle "Japan, Then and Now" and redesigned share covers; the copy no longer says "the map on the left"

## 2.9 · 2026-11-01

- Ancestral register: pick a municipality or use "Where am I?" to get a "Register of Then and Now" — home district, guardian shrine, distance to the provincial capital, 1572 power, late-Edo lords, Boshin War side and a local greeting — with each line's precision marked; save it as an image or share a link
- Late-Edo lords down to the district, from the 旧高旧領取調帳 tables in Japanese Wikipedia's district articles, covering municipalities home to about 80% of the population; elsewhere it falls back to the prefecture

## 2.8 · 2026-11-01

- Rankings: today's population regrouped by the 68 provinces and set against the 1721 census and rice yields; map colors, a clickable ranking, headlines computed from the data and rival face-offs
- Phone layout: the search box folds into a magnifier so the map gets more of the screen; tapping a prefecture redraws the map once, so it responds faster

## 2.7 · 2026-11-01

- Ancient sites layer: ichinomiya shrines (85), provincial capitals (85 presumed sites) and kokubunji temples (67); pay respects at an ichinomiya for a stamp, or earn an "in person" stamp within 1 km of the shrine; a new ichinomiya section in the goshuin book

## 2.6 · 2026-11-01

- The province map gains 712, 757, 824 and 1869, showing provinces splitting off and the Meiji re-division

## 2.5 · 2026-11-01

- Where am I?: your current province, prefecture, municipality and Meiji district from your phone's location, worked out on the device

## 2.4 · 2026-11-01

- The name lives on: 190 places, products and lines that still carry an old province name, each checked against Wikipedia

## 2.3 · 2026-11-01

- All 69 prints of Hiroshige's *Famous Places in the Sixty-odd Provinces*, with where each scene is today

## 2.2 · 2026-11-01

- The Ancient circuits filter now shows the real borders of the 68 provinces (pieced together from municipalities), with prefecture borders dashed on top

## 2.1 · 2026-10-31

- Japanese-style sound effects and koto music, synthesized in the browser; one-tap mute, audible in iPhone silent mode
- Copyright notice and licenses: MIT for code, CC BY-NC 4.0 for content

## 2.0 · 2026-10-31

- Pilgrimage layer: 111 anime and taiga-drama locations across all 47 prefectures, with coordinates and work–place links checked against Wikipedia

## 1.9 · 2026-10-31

- Automated checks: every push runs data checks and UI tests, and only publishes if they pass
- The map engine ships with the site so it loads in mainland China; fixed jumps when switching eras and the phone search list running off-screen

## 1.8 · 2026-10-31

- Municipal map: over 1,900 municipalities, colored by province or population, with Meiji-era districts
- Search with kanji, kana or English; phones switch between Map / Details / Guide tabs

## 1.7 · 2026-10-31

- Add to home screen and offline use; share links keep the language; data bundled, cutting first-load requests from about 100 to 2

## 1.6 · 2026-10-31

- English and Japanese interfaces, with all 47 prefectures translated

## 1.5 · 2026-10-31

- Battle sandbox (five battles in four phases) and the time-travel slider (nine eras)

## 1.4 · 2026-10-31

- Ramen and sake layers

## 1.0 · 2026-10-31

- First release: 47 prefectures ⇄ 68 provinces, six eras of history, the goshuin book and an AI history guide that changes identity with the region
