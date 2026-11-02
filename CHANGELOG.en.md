# Changelog

[中文](CHANGELOG.md) | **English** | [日本語](CHANGELOG.ja.md)

Newest first.

## 3.6 · 2026-11-03

- On this day: the welcome card shows what happened in Japan on today's date centuries ago — events and the births and deaths of historical figures, from the date articles of Japanese Wikipedia, checked against Wikidata for year (exact date for births and deaths) and place. Everyone gets a different order (the seed stays on your device), stable for the day; show others, or pick any date such as your birthday; tap one to drop a pin and select the prefecture. Gregorian dates, Julian before 1582
- "On this day here" at the end of each prefecture card: the next few anniversaries in that prefecture
- Edo domains: each prefecture card lists the domains seated there that lasted until their abolition in 1871 (261 domains, 3,194 lords) with their lords by house, linked to Wikipedia

## 3.5 · 2026-11-02

- Sengoku map, 1590: still all under Toyotomi, but the domains of the great lords — Tokugawa (six Kantō provinces), Mōri, Maeda, Uesugi, Date, Mogami, Shimazu, Kobayakawa and others — now have their own colors and leading figures
- Share links remember the Sengoku map: the address carries the year and the open province (e.g. `#sg=1600&sgp=美濃国`), so whoever opens it sees the same map and card
- The guide knows the Sengoku map: opening a province adds a quick question ("Who held Mino in 1600?") that lists all six years even offline; with an API key the record goes to the guide
- Portraits for 55 people: where Wikidata has no image the lead image of the Wikipedia article is used, and CC BY-SA images are now accepted with the author and license shown on the card; signatures and monuments are left out

## 3.4 · 2026-11-02

- Sengoku map: the "Sengoku powers" filter now colors the 68 provinces and switches between six years — 1467 at the start of the Ōnin War (the shugo governors: Yamana and Hosokawa ten provinces each), 1560 Okehazama, 1573 the fall of the shogunate, 1582 on the eve of Honnō-ji, 1590 unification under Toyotomi, and 1600 Sekigahara (Eastern army / Western army / switched sides / divided / stayed out). Provinces split between powers say so, unclear ones are shown as local lords or contested, and every entry is checked by script against the shugo lists and biographies on Japanese Wikipedia
- Click a province to see who held it in each of the six years and who led them; click a name for the person card
- Person cards: 61 emperors, shoguns, regents and Sengoku lords have a short bio in three languages (written for this site, every year and event checked against their Wikipedia article) and related people; 53 have a public-domain portrait, some a family crest
- Emperors and shoguns timeline: a "Timeline" button at the end of the year row lists the 126 emperors by period with their capital (plus the shogunate's seat from Kamakura to Edo), and the shoguns and Kamakura regents by shogunate; tap a row for the person card
- The Sengoku line of the "Register of Then and Now" now lists the province's holders in all six years

## 3.3 · 2026-11-02

- Peninsula power: a "Power" button at the end of the era bar counts the households, people and farmland registered for each county in the 1432 gazetteer of the Annals of King Sejong into today's 29 regions and sets them against today's population — five metrics, rankings, headlines worked out from the numbers, and face-offs such as Seoul vs Pyongyang or the two Gangwons. For the southern provinces, county totals match the gazetteer's provincial totals to within 10 households
- Peninsula battlefields: Salsu (612), Hwangsanbeol (660), Gwiju (1019), Cheoin (1232), Hansan Island (1592) and Myeongnyang (1597), replayed on the map in four stages with the guide Dancheong narrating; the Korean War is not included. Text checked against the Korean, English and Japanese Wikipedia
- Historical divisions: a new Three Kingdoms layer (c. 500: Goguryeo, Baekje, Silla, Gaya); Unified Silla now shows its nine provinces and royal capital, Goryeo its five circuits, two frontiers and capital region — all pieced together from today's counties (approximate)
- The "here, then and now" card adds a Three Kingdoms row and names the Silla province and Goryeo circuit

## 3.2 · 2026-11-02

Peninsula mode gets its own versions of Japan-only features:
- Peninsula seal book: one hangul square seal per region (no emblems or flags), grouped by the eight Joseon provinces; a hyanggyo chapter with the 141 hyanggyo that have coordinates on Wikidata — mark a visit, or check in within 1 km for a gold seal. No verifiable locations yet for hyanggyo in the North, and the book says so
- Traditional liquor: 16, only those on South Korean intangible-heritage or Food Master registers; Munbaeju is listed under Pyongyang, where it originated
- Here on the Daedongyeojido: each region on Kim Jeong-ho's 1861 map (Kyujanggak copy), zoomable; the old map is aligned automatically with today's coastline, so the area shown is an estimate

## 3.1 · 2026-11-02

- Shared history grows from 2 episodes to 9, in date order: migrants and Buddhism, Baekgang, the Mongol invasions, the Imjin War, the Joseon embassies, the road to annexation, Japanese rule, normalisation, and repatriation and the abductions. Each still has facts both sides accept, each side's account and sources, with North Korea's account where it is involved
- Renamed "Shared history: Japan and the Korean Peninsula"; one entry button on the welcome card, and the episode tabs scroll sideways in a single row
- Fix: in Peninsula mode the guide's quick-question buttons had a pale background that hid their text

## 3.0 · 2026-11-02

- New Korean Peninsula mode, switched from next to the title: 29 regions North and South (2026 divisions) and 400-plus cities and counties, named in English, Korean script and romanization
- A card for every region: six eras of history, sights, food, dialect and local in-jokes (in three languages)
- Historical divisions: Silla's nine provinces, Goryeo's circuits, Joseon's eight provinces and the 1896 thirteen provinces; the towns behind the province names, Where am I and Then and now
- Shared history of Japan and Korea: the Imjin War and Japanese rule, written as facts both sides accept / each side's account / sources, shared by both modes
- Disputed places (Dokdo / Takeshima, the Northern Territories, Sea of Japan / East Sea) show both names and each side's position; Japan mode now draws them the same way
- The peninsula guide Dancheong, dancheong colours, gayageum-style music and a first-visit tour

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
