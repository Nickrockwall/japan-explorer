# Changelog

[中文](CHANGELOG.md) | **English** | [日本語](CHANGELOG.ja.md)

Newest first.

## 3.34 · 2026-11-11

- The 3D map now tells what happened between the years: 33 events (the Ōnin War, the arrival of firearms, Nobunaga's march on Kyoto, Honnō-ji, the siege of Odawara…), each checked against Japanese Wikipedia for year, place and key facts. ▶ flies to each one in turn before returning to the whole country and spreading the ink to the next year; when you change the year yourself, "N events" appears at the bottom to step through, and battles can be replayed from there
- Kyoto carries weight: an always-visible "Kyō" seal shows who held the realm that year, and opens to the emperor, the shogun, and who ruled in name and in fact; zoom in to see the Heian-kyō street grid (schematic)
- The world moves: rows of seigaiha waves swell on the sea, low mist drifts, banners stir in the wind and smoke rises above castles in use nearby (can be turned off in settings; off by default if your system asks for reduced motion)
- The 2D battle panel has a "3D" button that opens the same battle at the same stage on the terrain; the tour gains a step pointing out the map's "3D" button
- Keyboard: arrows pan, + / - zoom, 1–6 change the year, Space plays, N faces north, T toggles top-down
- The README has a 3D screenshot and a "Sekigahara in 3D" link; links to the 3D map get their own preview image when shared

## 3.33 · 2026-11-11

- The 2D/3D switch now sits on the map itself: a dark "3D" button on the right of the main map (above the location button), easy to spot on desktop, tablet and phone without opening the Sengoku view first; the 3D view has a "2D | 3D" switch in the same place
- Battles can be replayed in 3D: Okehazama, Kawanakajima, Sekigahara, Dan-no-ura and the Satsuma Rebellion. Marching routes grow along the terrain stage by stage, the camera frames each stage, with the commanders' lines and an autoplay; Sengoku battles switch to the matching year, the other two are shown without clan colours
- A ▶ at the start of the year row plays 1467 to 1600, with the ink spreading at each year
- Clicking a clan in the legend opens its overview: its provinces are highlighted, with the number of provinces, estimated koku and rank that year, its leading figure and the provinces themselves; names in province cards and overviews open person cards (with a portrait and bio where we have one)
- Famous castles are drawn larger; castle cards say who held the place that year; English castle names now follow the Japanese reading ("Himeji Castle"); castles whose infobox gives only a century are included too (Shuri, Nakijin…, shown as "around the 14th century") — 483 castles in all
- New search (provinces, castles, clans, in any of the three languages), a face-north button and a top-down/tilted switch; the address bar follows the year, the selected province, the camera and the battle, so a copied link opens the same view
- Settings can save the current view as an image (paper border, title and seal) and turn sound on or off; loading shows progress; once opened, the 3D map works offline (except the detailed terrain); weaker devices start in battery-saver quality, and if WebGL is unavailable there's a link back to the 2D map

## 3.32 · 2026-11-10

- The 3D Sengoku map is now part of the site: the Sengoku year row has a "3D" button and province cards have "See it in 3D", which carry the year and province over; "← 2D map" in the 3D view brings you back to the same year and province. The 3D map now speaks Chinese, English and Japanese
- Castles across the whole country instead of just Kinki: 424 of them, with the same rule — only castles whose Japanese Wikipedia article gives a founding year before 1600. Ancient forts long abandoned by then (Taga, Mizuki…) are left out. From far away, castles too close together show only the better-known one; more appear as you zoom in
- Changing the year now spreads the new colours like ink, with a dark ink edge (switches instantly if your system asks for reduced motion)
- Changing the year no longer freezes for several seconds: map textures are drawn on the CPU and uploaded in one go, and each tile draws only its own lakes and rivers

## 3.31 · 2026-11-10

- The 3D Sengoku map gets a folding-screen look: ink-washed shaded slopes, gold on sunlit ridges, paper grain, low mist and a seigaiha wave pattern on the sea. Each clan’s territory now has a nobori banner (clan colour, crest and name); from far above it switches back to crest labels. The style can be turned off in settings

## 3.30 · 2026-11-10

- New experimental page, “3D Sengoku map” (`3d.html`, not yet linked from the main site): 3D terrain from GSI elevation data with the six years of Sengoku territories, borders and front lines, lakes and rivers. Zooming in switches to ~250 m terrain and adds forests, 74 castles in the Kinki region (shown by the years they were built and abandoned) and small models of each province’s ichinomiya, provincial office and kokubunji. Click a province for its six years, or a castle for its dates

## 3.29 · 2026-11-09

- Went through every prefecture card's original text (timeline, sights, specialties, dialect, local jokes, characters, ramen, sake) and fixed 18 items against Japanese Wikipedia, in all three languages:
  - Tokyo Prefecture dates from 1868, not 1871; Kōfu Prefecture from 1869, becoming Yamanashi in 1871; Takeda Nobumitsu died in 1417; Oda Prefecture joined Okayama in 1875; the Shimoge and Usa districts went to Fukuoka with Kokura Prefecture in 1876 and on to Ōita the same year
  - The gyōza rivalry now includes Miyazaki (winner 2021–2022, Hamamatsu since 2023); Shizuoka tea is now neck and neck with Kagoshima; Ise lobster is a Shima specialty; sakura shrimp are fished in Japan only in Suruga Bay; Japan's most hot-spring sources and greatest flow belong to Ōita as a whole (Beppu first, Yufuin next)
  - What makes Hyōgo unique is spanning five provinces, not facing two seas; Hearn wrote 'Kwaidan' after leaving Matsue; soft-water brewing began in Akitsu, not Saijō; Nitta Yoshisada ended the Kamakura shogunate, not "150 years of Hōjō rule"; Saitō Dōsan's one-lifetime rise is now flagged as the traditional story
  - Removed or reworded claims with no source: the 500-bowl wanko soba record, Senkin's "wooden-vat brewing", the title of a Shimane self-mocking manga


- New "Before mergers" row in the family register: which municipalities this place was made of in 1995 and when it took today's form (Ueda: Ueda, Maruko, Sanada and Takeshi, merged in 2006), with a matching line in the local timeline. Worked out from the 1995 boundaries and municipal dates of CODH's Historical Administrative Area Data Set; 652 municipalities have one
- New "Namesakes" row: when this place's name — today, in 1995 or in the Meiji era — contains Fuchū, Kokufu, Kokubu, Ichinomiya or Sōja, the register explains where such names come from, how far this province's capital (or Kokubun-ji, or ichinomiya) is from here, and lists where the other places of that name are today
- Sliding to the Nara period now shows the province borders of 757 (Tenpyō-hōji 1) by default, instead of 824, which is after the Nara period
- Fixed the 757 borders: Awa was restored as a province in the same month as Noto that year, but was drawn as still part of Kazusa
- The Sengoku stretch of each prefecture's timeline now also reads 1467–1600, matching the time slider


- Two more slider eras merged with filters: the Nara period now shows the Five Home Provinces and Seven Circuits on real province borders, and the Present day shows the eight modern regions. Tapping either filter moves the slider to its era. The filters left are the truly separate ones: exploration, Bakumatsu sides and province power
- The Sengoku era on the slider now reads 1467–1600, matching the six years of the Sengoku map (through Sekigahara)
- Map files use a lossless compact format: the first-screen map of Japan drops from about 290 KB to about 115 KB over the network, and the province and municipality maps shrink by more than half — they draw exactly as before
- Place-name origins in the family register grow from 124 to 222: 98 cities of 50,000–150,000 people whose Japanese Wikipedia article explains the name, such as Asaka (after Prince Asaka), Chitose (renamed because the old name sounded like "dead bones"), Kunitachi (one character each from Kokubunji and Tachikawa) and Naruto (whose first name lasted two months). Every entry is checked against its article for key words and years
- Removed per-prefecture era colouring that the merged eras no longer use

## 3.26 · 2026-11-08

- New logo: the top-left mark and the home-screen icon are now one vermilion seal with the Japanese archipelago (they used to be 古 and an old dark 旅 icon); browser tabs get a matching small icon
- The time slider's Sengoku era and the Sengoku power map are now one view: sliding to Sengoku shows the per-province map with its six years from 1467 to 1600; the Sengoku power button moves the slider there; leaving Sengoku returns to your previous filter
- The first "Start here" button shows a scroll instead of a lantern (the previous release meant to change it but didn't)

## 3.25 · 2026-11-08

- The welcome page has a new "Start here" section with three ways in: what your hometown was called back then, how the Sengoku warlords split Japan, and which old province you are standing in
- Usable without a mouse: the first Tab stop is "Skip to search", "/" jumps to the search box, and ↓ on an empty box lists all 47 prefectures; the map has a description for screen readers
- Place-name origins in the ancestral register grow from 74 to 124: 50 more cities and wards, including Tokyo's Kita, Minato, Taitō and Sumida, Hakodate, Asahikawa, Matsumoto, Takaoka, Takarazuka and Urayasu, each checked for key terms and years against its Japanese Wikipedia article; year mismatches between languages in the Ōta and Kitakyūshū entries are fixed
- Interface text is split by language, so only the current language downloads (about 120 KB less); On This Day data now loads once the page is idle, so the map comes first
- New unit tests for the data tools and a consistency check across the three languages' interface text run on every push; the offline cache list is now generated automatically
- The licence notes now cover the sources for place-name origins, Meiji villages and castle towns

## 3.24 · 2026-11-08

- The serif font for titles and place names now ships with the site instead of coming from Google Fonts, which is blocked in mainland China (the whole site fell back to system fonts there). Only the ~4,500 characters the site uses are included, cut into small slices by frequency, so a page downloads just the slices it needs (about 0.6 MB on first load, was about 1.3 MB)
- The ECharts map engine is now a custom build with only the parts the site uses: 1 MB → 0.55 MB (326 KB → 186 KB compressed)
- Hiroshige's 69 *Famous Places in the Sixty-odd Provinces* prints are now WebP: 7.2 MB → 5.0 MB with no visible difference
- The AI guide's provider list adds DeepSeek and Qwen (both reachable from mainland China; picking one fills in the address and model); the OpenAI default model is now gpt-4.1-mini

## 3.23 · 2026-11-08

- New light look based on Edo-period *kuniezu* (official province maps): mulberry-paper background, white land, a pale indigo sea and ink borders. Vermilion is now reserved for "seals" — the logo stamp, the stamp button, primary buttons and the selected place; selected filter buttons are ink
- The selected place's name sits on a paper slip on the map (vertical in Chinese and Japanese); legend swatches are the oval *koban* marks from kuniezu legends; map labels are ink with a paper outline
- Every data palette retuned to mid-tone mineral pigments under one rule: regions, circuits, Sengoku clans (about 80), Bakumatsu, ramen, sake, municipalities, province power (pale ochre → umber → deep vermilion), population change (indigo ↔ vermilion); Sengoku crest banners are now ink
- New palette check run on every push: text contrast on paper, each category colour against ink, against the land and against the rest of its group — it caught 6 pairs that were too close (Oda/Ryūzōji, Uesugi/Shimazu …), now fixed
- Consistent corner radii by hierarchy, no more glow shadows; guide avatars are paper with ink, ringed in each guide's colour; share cover and README screenshots redone
- Wide screens: sound, settings and language move into a "More" menu; the guide panel shrinks to one line until a place is picked; the map fits the four main islands to the window. Phones: map tooltips appear above the finger
- Korean Peninsula mode keeps its dark dancheong skin

## 3.22 · 2026-11-08

- Late-Edo lords: 26 of the 29 domain names that didn't match the domain list now do, so their lords open in the register — spelling variants (一ノ宮 / 一宮, 上ノ山 / 上山, 竜ヶ崎 / 龍ヶ崎), names from early-Meiji renamings or new seats (Takashima = Suwa, Tate = Matsumae, Matsumine = Dewa-Matsuyama, Mineoka = Minegoyama, Yoshimi = Mikami, Hanbara = Okabe, Tanoguchi = Okutono) and enclaves in other provinces (Yoshida in Tōtōmi, Kameyama and Fukuyama in Bitchū, "Kanazawa" in Ōmi = Kaga), each checked against the domain's article; Isesaki had been cut to "崎藩" by stripping a province name
- Seven branch domains without their own Wikipedia article are added, reading their lords from the section of the parent domain's article: Kuroishi (a domain from 1809), Hisai, Iwasaki and Dewa-Matsuyama, which lasted until 1871, plus Ōyama, Aterazawa and Kubota-Shinden
- Villages recorded only against Osaka city are placed in the ward named by the Nihon Rekishi Chimei Taikei (its coordinates often drift near city borders), with same-named villages told apart by reading and Meiji district; Kishidadō, Higashi-Ajiro and Arakawa go to Higashiōsaka, the database's second code. Unplaced rows fell from 23 to 11 (villages missing from the Taikei, and Tennōji, which spans two wards)
- Chinese names: 崎, 富 and 樫 had been written as the variants 﨑, 冨 and 㭴 (高﨑藩 → 高崎藩, 千叶胤冨 → 千叶胤富, 冨㭴政亲 → 富樫政亲)

## 3.21 · 2026-11-08

- The family register's data is split by prefecture: opening a register downloads only that prefecture (tens of KB) instead of the whole country (about 0.5 MB), so it opens faster on phones
- Ten Meiji villages that Wikipedia filed under the wrong municipality are corrected by checking CODH's 1920 boundaries (same prefecture, district and name, lying wholly in another municipality) — Yomogita is no longer counted in Aomori, Ina goes to Komagane, Kōzu and Sonoda (swapped on Wikipedia) go to Itami and Amagasaki, Kamigamo to Kita ward
- Late-Edo lords: villages recorded only against a whole city such as Osaka or Sendai are placed in wards by their coordinates; villages placed by coordinates in old municipalities that straddle today's borders rose from 635 to 1,146 (the dataset's "prefecture code" is really a volume number, which had hidden every prefecture after Kyoto), unmatched rows fell from 198 to 55, and 1,622 municipalities now have the row
- Name origins 57 → 74: the Iwate prefectural site covers every city in the prefecture, adding ten (Miyako, Hanamaki, Kitakami, Tōno, Ichinoseki, Kamaishi, Ninohe…); city and prefectural sites add Aomori, Fukushima, Mito, Ōtsu, Matsue, Saga and Kagoshima

## 3.20.1 · 2026-11-08

- Name origins for Morioka, Kumamoto and Ōita (57 in all): Morioka from the Iwate prefectural site (Kozukata → Morigaoka → 森岡 → 盛岡), Kumamoto from the city's castle documents (隈本 became 熊本 in 1607), Ōita from the city site (the Bungo Fudoki's "great fields", 碩田)

## 3.20 · 2026-11-08

- Late-Edo lords down to the municipality: the family register now uses the National Museum of Japanese History's Kyūdaka Kyūryō Torishirabechō database (about 65,000 villages, 97,000 records), adding up the lords and rice yields of every village inside today's municipality — "111 villages here, 57,112 koku — Ueda Domain 79%, Shogunate 8%…", sealed "Town". It used to be inferred from the Meiji district or the whole city; villages shared by several lords are now split by each lord's yield instead of being lumped as "shared". 1,607 municipalities have it, including the wards of Saitama and Nagoya (villages in old municipalities that straddle today's borders are placed by their coordinates in CODH's Nihon Rekishi Chimei Taikei data set)
- Places split among several domains, like Ōita, now lead with the largest yield (Usuki 35%, Funai 24%…) rather than the district of the town centre
- New row in the family register, "Ancient townships": the townships (gō) of the district in the 10th-century Wamyō Ruijushō, with readings (via the Nara National Research Institute for Cultural Properties). About 980 municipalities match an ancient district; districts split or renamed later are traced back (Ashigarakami → Ashi-no-kami, Kasugai → Kasugabe…), and districts made from several ancient ones are left out. The hometown timeline's ancient line shows the district too
- Meiji villages for about 370 more municipalities (1,399 → 1,772), filled in from the 1920 municipal boundaries of CODH's Historical Administrative Area Data Set where Wikipedia is silent (only villages founded under the 1889 system and still there in 1920)
- Reign years: lords missing from both Japanese Wikipedia and Wikidata are looked up in the daimyo tables of English Wikipedia's domain articles (matched by kanji name) — 18 more
- Name origins for six more cities — Maebashi, Fukui, Shizuoka, Tokushima, Matsuyama and Nagasaki — checked against the city or prefecture's own website, since Wikipedia doesn't say (54 in all)

## 3.19 · 2026-11-08

- Faster first load: body text now uses system fonts, and only one serif web font is downloaded for the current language (Noto Serif SC for Chinese, Noto Serif JP for Japanese and English). Fonts on a first visit dropped from one or two hundred requests and 3–5 MB to a dozen or so requests and about 0.5–1.2 MB (about 0.5 MB on phones)
- In the English interface, kanji place and personal names now use Japanese glyph shapes (they used simplified-Chinese shapes before); map labels follow the language's serif font too
- Meiji villages now cover about 200 more municipalities (about 71% → 83%): rows written as "(現横須賀市)", "(現：上越市)" or "(現存)" are now understood. This also fixes about 60 wrongly placed villages that used to fall back to the district's default town — Nadachi was listed under Itoigawa (it is in Jōetsu), Nishimeya under Hirosaki, Azuma under Ashikaga (it is in Sano)
- Automated tests now run in 8 parallel parts, so changes go live a few minutes sooner

## 3.18 · 2026-11-08

- Castle towns now name their own domain: 122 municipalities that held a domain's seat (castle or jin'ya) show that domain as the late-Edo lord, still followed by the district's village counts. About 35 towns change, where counting villages across the whole district had picked a neighbour or bannermen: Matsuyama (Ōzu → Iyo-Matsuyama), Tsu (Kishū → Tsu), Yamagata (Kaminoyama → Yamagata), Uwajima, Akashi, Tsuchiura, Hachinohe, Amagasaki…; Toyama, empty before, now reads Toyama Domain. The seat is placed by the castle's coordinates and counted only when the domain or castle name is in the town's name, so small domains in merged-in outskirts (Yoita in Nagaoka, Matsushiro in Nagano, Yagyū in Nara) don't stand for the whole city
- The Home line now names the same district as the Edo line (Kasama: Nishi-Ibaraki, not the pre-1878 Ibaraki)
- Oda Nobutoshi of Tendō shows both terms (1868, 1869–1871) instead of one with years and one without
- Data tools: when Wikipedia returned more than one response holds, some articles used to be silently skipped; the tools now fetch the rest and stop with an error if anything is still missing. Each tool records the revision of every article it read, and domain-name matching no longer varies from run to run (Yamaguchi came and went)

## 3.17 · 2026-11-08

- Old Family Register: a new "Meiji villages" line lists the towns and villages of the 1889 municipal system that are now part of this place (Ueda: Ueda-machi, Kamikawa-mura…). From the district articles on Japanese Wikipedia, only where they say which town each village now belongs to: 1,199 municipalities, about 10,000 villages. Where an article names only a big city and not the ward, the ward is left out, so some lists are incomplete. The hometown timeline gets the same line
- New "The name": where city names come from, for 48 prefectural capitals, designated cities and cities over 300,000 whose articles explain it (Sapporo, Sendai, Takasaki, Shinjuku, Yokohama, Kōfu, Gifu, Hamamatsu, Kōbe, Himeji, Hiroshima, Kōchi, Naha…). Our own one- or two-line summaries in three languages, with every keyword and year checked against the article; competing theories are given as such. Cities whose articles don't say (Aomori, Akita, Matsuyama, Okayama…) are left out. Wards show their city's story under a "City" seal
- The register's footnote now explains the "City" seal
- The data tools' download cache never actually hit; a second run now downloads nothing. It also surfaced fixes to last time's "district of the town centre": 20-odd more towns (Tsuruoka, Maebashi, Takasaki, around Utsunomiya…), and Fuchū (Hiroshima) and Echizen (Fukui) are no longer mistaken for the other towns of the same name (Fuchū-chō, Echizen-chō)

## 3.16 · 2026-11-08

- Old Family Register "Late-Edo lord" and the Edo part of the hometown timeline: now present for 96.7% of municipalities from Honshū to Kyūshū (was 90.7%; by population 86% → 96%)
  - The cities of Edo and Kyoto: Chiyoda, Chūō, Minato, Bunkyō and Taitō read "Shogunate land · the city of Edo, under the town magistrates"; Kamigyō, Nakagyō and Shimogyō read "under the Kyoto town magistrates" (sources: the Japanese Wikipedia articles on Tokyo's 15 wards and the Kyoto town magistrate). In Meiji these were wards, part of no district
  - Wards of big cities with no district record use the districts of the whole city, only when every one is led by the same lord, marked "City" (Nagoya's wards → Owari, Hiroshima's Naka → Hiroshima, Saitama's wards → Shogunate)
  - Towns spanning several districts led by different lords now follow the district of their town centre (the "X-gun Y-machi" written in the town's article) instead of the first listed; 43 towns corrected, e.g. Ōgaki → Ōgaki, Tsuyama → Tsuyama, Fukuchiyama → Fukuchiyama, Hamada → Hamada, Ōita → Funai
  - 45 more district articles are now read: Kyoto's village-by-village tick tables (new category "court nobles"), column tables (Abe), articles that mention the register early and give the table later (Tsuzuki), "Sendai Domain (34 villages)" phrasing, and districts merged in Meiji (Naka-Kawachi, Kimitsu, Ibo, Inashiki, Kita-Katsuragi, Nakatado…)
  - Futaba now adds up both Shineha and Naraha (Naraha was missed); village counts for Iga, Ago and others no longer pick up the 1889 figure
  - Domains renamed in early Meiji (Nagoya, Kagoshima, Kōchi, Yamaguchi…) show their usual names (Owari, Satsuma, Tosa, Chōshū) so their lords can be expanded; only full-page redirects count, so branch domains such as Hisai and Kuroishi stay separate
  - Tokyo's Chūō ward was wrongly matched to Tama district (same name as Sagamihara's Chūō ward); removed
- About 70 more lords have reign years (92% → 94%), taken from the "Lord of X Domain" position on Wikidata where neither Wikipedia source has them; checked first against the 3,664 lords that already had years: 99% agree
- Still without an Edo line (Izu Islands, Oki, Toyama's Niikawa districts, Hamamatsu's wards, Higashiōsaka…): the articles give no village-by-village holdings or counts, so nothing is written

## 3.15 · 2026-11-08

- Prefectures after 1871 in "This place through time" are more precise: changes that only affected part of a district ("the area under X prefecture went to Y") are shown only when the place was under X at the time (Takashima in Ōmi used to list Toyooka, Iruma and Nukata in a row), and transfers of a few islands (Naoshima in Kagawa district) no longer count for the whole district
- Late-Edo lords for Minamikawachi and Futaba districts: merged districts whose predecessors were written with a line break or as "part of X district" were missed. Kaizu and Inaba districts had in fact counted only one predecessor, so their incomplete figures are dropped
- Reign years for 6 more lords: years written right after the name in a domain article's list, ruled out when they match the lord's birth and death years on Wikidata; Shirakawa domain's "Shirakawa Prefecture" is no longer listed as a lord
- 15 post-Meiji family heads are removed from the lord lists (some domain articles carry the list on to the present, e.g. Count Sakai Tadayoshi for Shōnai, Prince Hitachi for Hirosaki): anyone born in 1870 or later, by Wikidata, cannot have been a domain lord
- New README screenshots (the "Who ruled" page replaces the peninsula), a "Who held power" link, ten eras, prefectures after 1871 and the "Spot a mistake?" link; the "did you know" figures are recomputed from current data
- Tests: the browser used by the GitHub checks is cached (about 150 MB less to download each run); local parallel runs allow more time for page loads, so they no longer occasionally time out and retry

## 3.14 · 2026-11-08

- Fixed: 37 On this day entries (Ōtomo Yoshishige, Ryōkan, Maeda Toshinaga…) were pinned in Shiga. Their place was recorded only as "Japan", whose Wikidata coordinates happen to fall in Shiga; such places are now skipped in favour of the next one, or the entry is left out
- Fixed: people whose birthplace is recorded only as "Kyoto", "Tokyo", "Edo", a prefecture or a province were counted in whichever ward holds that place's marker (Sugawara no Michizane "born in Nakagyō", Chiyoda's timeline crowded with "born in Tokyo"). They still appear in On this day and on prefecture cards, but no longer in a single ward's "This place through time"
- The Amami Islands get their own timeline: under Ryūkyū from the late 15th century, ruled directly by Satsuma from 1609 (with its sugar monopoly), US military rule from 1946, returned on 25 December 1953
- The era slider gains "Taishō & early Shōwa (1912–1945)"; it used to jump from Meiji straight to after 1945. Colours: prefectures hit hardest by the 1923 Great Kantō earthquake (Tokyo, Kanagawa, Chiba, Ibaraki, Shizuoka, as the article lists), homes of the six great cities, the atomic bombings (Hiroshima, Nagasaki) and the Battle of Okinawa; the banner's real-power line reads oligarchs → party cabinets → the military
- "This place through time" now goes past 1871: which prefecture the place first belonged to and how it merged into today's (Ueda: Ueda → Nagano; Takamatsu: Takamatsu → Kagawa → Myōdō → Kagawa → Ehime → Kagawa again in 1888). Taken from each district article; where a district lists several new prefectures, the one matching the local domain is picked, otherwise none. This data is a separate file loaded only when you open an ancestral register
- The timelines have their own link: `#rl=power` opens the "Who ruled" page (the address follows the tab, ready to share)
- On phones the era banner's real-power line wraps onto two lines instead of being cut off

## 3.13 · 2026-11-07

- "This place through time" is no longer almost empty for Okinawa and Hokkaidō. Okinawa follows Ryūkyū history: the Three Kingdoms, Shō Hashi's unification (1429), the Second Shō dynasty (1470), the Satsuma invasion (1609), the Ryūkyū Domain (1872), Okinawa Prefecture (1879), the Battle of Okinawa and US rule, and the return (1972). Hokkaidō covers Ainu culture, Koshamain's War (1457), the Matsumae Domain (1604), Shakushain's War (1669), direct shogunate rule (1799, 1855), the Development Commission (1869) and the Hokkaidō Agency (1886), with the Japanese enclave at the tip of the Oshima Peninsula and the rest of Ezochi each getting their own entries. Every year is checked against Japanese Wikipedia, and the empty "outside the provinces" Sengoku lines are gone
- The guide now knows "Who ruled": on the era slider a new quick question asks who held power in that era, answered even without an API key (the real holders and nominal heads of each period); asking "who held real power in the Edo period" works too. With an API key the whole list goes into the guide's reference material
- The guide also knows "This place through time": pick a place on the municipal map and ask what it was in the old days, and the answer goes on to who held it over time (Ueda: Sanada → Sengoku → Matsudaira → domains abolished 1871). With an API key the whole timeline goes into its references, with an instruction not to add holders that are not listed

## 3.12 · 2026-11-07

- Fixed the start year of 152 domains: it came from the succession box, which for domains abolished and re-created gives the last re-creation, so cards showed things like "Hirosaki 1871–1871". Start years are now corrected to the earliest lord's accession (Hirosaki 1590, Shimodate 1598)
- Fixed: the ancestral register crashed for Natori, Sendai and a few other places. Their district articles only say "all of it was Sendai domain land" without a village count, which used to be read as an empty record; it now shows "all of Natori district"
- Late-Edo lords are now read for 70 more districts: newer-style tables (Suntō, Kamo…), prose such as "all of it under the X magistrate's office" (Minamitsuru, Minamiaizu), and districts merged around 1896 whose articles have no table (Chōsei = Nagara + Kamihabu, adding up their predecessors). Municipalities with an Edo line in the register and its timeline rise from 87% to 94% (outside Hokkaidō and Okinawa)
- Reign years for 32 more lords: where the succession box gives a single year, the reign is taken from the neighbouring lords' years only if that year matches one end (mostly reigns of under a year)
- The saved ancestral-register image now includes "This place through time"
- When you drag the era slider, the banner gains a "Real power" line listing who held power in that era (Heian: Emperor and Council of State → Fujiwara regents → Retired emperors → The Taira), from the same data as the "Who ruled" page
- In "This place through time", a house whose first lord has no reign years now shows "…" for its start instead of the second lord's accession; reading glosses are dropped from house names

## 3.11 · 2026-11-07

- New "Who held power": the timelines dialog opens on a "Who ruled" page that splits Japanese history from the 3rd-century Yamato kingship to today into 20 periods, each with the nominal head, the person or group that really held power (the Soga, the Fujiwara regents, the retired emperors, the Taira, the Hōjō regents, Oda, Toyotomi, Tokugawa, the Meiji oligarchs, party cabinets, the military, GHQ…) and the seat of power. Where two boundary dates are in common use (Kamakura from 1185 or 1192) both are shown; every year and name is checked against the matching Japanese Wikipedia article. It opens from the welcome card, and "Emperors" / "Shoguns" / "Regents" jump to that period's list
- Edo domain lords now show their reign years (about 3,900 lords, nine in ten), taken from the succession box at the end of each lord's article; single years or ones that disagree with the domain article are left out. "Lord of …" tags in On this day and the birthday card show the years too
- The ancestral register ends with "This place through time": the municipality's province, its Sengoku lords year by year, the domain and houses that ruled it in the Edo period (by reign), the abolition of the domains and today, with On this day events, births and deaths located here slotted in — tap one to mark it on the map
- Sengoku map banners for the Miki (Anegakōji) and the Horigoe kubō: the Miki use the ken-bishi crest named in the infobox of Japanese Wikipedia's "Anegakōji clan" article; the Horigoe kubō were an Ashikaga branch and use the Ashikaga two-bar crest
- Every card (prefecture and peninsula cards, Sengoku province / clan / person cards, the ancestral register, the birthday card, the timelines) ends with "Spot a mistake?", which opens a new GitHub issue already filled in with the card, the current link and the interface language (needs a GitHub login; the site itself collects nothing)
- Fixed: when someone has both a birth and a death entry in On this day, tapping the birth could mark the place of death (Sugawara no Michizane landed in Dazaifu); entries are now matched by type
- The UI tests run as four parallel shards, so updates go live sooner

## 3.10 · 2026-11-03

- Ōu is no longer one grey block of "Northern clans": Mutsu and Dewa are split into 43 districts, so the Nanbu, Tsugaru, Andō (Akita), Kasai, Ōsaki, Date, Ashina, Sōma, Iwaki, Mogami, Onodera, Tozawa, Daihōji and others each get their lands, banners and overviews. After the 1590 Ōu settlement the Kasai and Ōsaki lands go to Kimura Yoshikiyo, Aizu with Iwase, Asaka, Shirakawa and Ishikawa to Gamō, and the Date keep 13 districts; in 1600 the Uesugi lands are Western and the Sōma and Iwaki stay out. Every entry is checked against Japanese Wikipedia
- Ezo is split in two: the Wajinchi at the southern tip of the Oshima Peninsula (the Kakizaki, later Matsumae) and the rest as Ainu lands, instead of one block marked "outside the provinces"
- The ancient register now gives the Sengoku row for Tōhoku and Hokkaidō towns by district, with a "district" precision seal
- District borders are pieced together from today's municipalities and approximate; there are no 1598 koku figures by district, so powers holding Ōu land show koku for their other lands only (marked "≥") and are not ranked
- The legend lists at most 13 entries and folds the rest; zoomed out, banners appear by territory size, so Tōhoku is no longer crowded

## 3.9.1 · 2026-11-03

- Fixed the map colours drifting away from the borders and names after dragging: when you picked a prefecture or a card opened, the map slid into place with an animation, and dragging during that slide left the colour fill stuck at the old position until the next redraw. The base map now moves instantly, on desktop and phone, and in the town and peninsula maps too

## 3.9 · 2026-11-03

- The Sengoku map now reads like a map of rival domains: neighbouring provinces held by the same power merge into one block, and bright front lines run where two powers meet (in 1600, the line between East and West). Provinces held by local lords or shared between powers keep their borders
- Crest banners on the map: Oda's mokkō, Takeda's diamonds, Hōjō's scales, Mōri's ichimonji mitsuboshi… 50 families in all, taken from each family's Japanese Wikipedia article; zoomed out you see the powers holding two or more provinces, zoom in for the smaller ones. Families with no known crest show their name
- New power overview: tap a banner, a family in the legend, or a family name on a province card to see which provinces it held that year, an estimated koku total from the 1598 Taikō survey figures, its share of Japan and rank, how its provinces and koku changed from 1467 to 1590, and which powers bordered it by land; the map spotlights its territory. "Bordering" only means the provinces touch, not enmity or alliance
- The guide follows the overview with a "How big was … in …?" question, answered offline too; share a link with `sgc=` to open a family directly

## 3.8 · 2026-11-03

- A bigger map on phones: the top bar is a single row, with battles, goshuin, sound, settings and language moved into the ☰ menu; layers became a drop-down at the left of the toolbar, sharing a row with the filters; the legend is one row of swatches (tap it for the caption) and the time slider is one row too
- Cards on the map (rankings, prints, ancient sites, Sengoku, towns…) are bottom sheets on phones and tablets: they open part-way, tap the handle or drag up to expand, drag down to shrink and again to close; the map moves out of the way so the place you tapped stays visible, and cards are no longer see-through
- The detail card has a row of section links (overview, provinces, timeline, dialect, Edo domains…) that jump straight there and follow your scrolling; prefectures with many domains list six first, with "Show more"
- The emperor and shogun timeline can jump by era
- Phone buttons are now big enough to tap (mostly 36–44 px tall), small text is at least 12 px, and rows that scroll sideways fade at the edge to show there is more

## 3.7 · 2026-11-03

- New "🎂 Birthday card": pick a date in On this day (your birthday, say) to see everyone born and who died that day and what happened, plus how eventful the day is among all 366, how long ago the earliest entry was, and which prefecture it's most tied to; add a name and save it as an image, or copy a link
- Domain lords and On this day are linked: in Edo domains (prefecture card and ancestral register) a lord's name now carries birth / death dates that mark the birthplace or place of death on the map, and On this day entries that were lords say so

## 3.6.3 · 2026-11-03

- On this day now covers the whole year: six days used to be empty and many had only one or two entries — every one of the 366 now has at least three
- Added well-known people born before 1950 who have since died (Osamu Tezuka, Akira Kurosawa, Yukio Mishima…), chosen by a year of Japanese Wikipedia page views, two or three a day so the older history still leads

## 3.6.2 · 2026-11-03

- The "Lord, late Edo" row of the old family register now expands to that domain's line of lords
- Better "lasted until 1871" flags: Sasayama, Fukuchiyama, Miyazu, Izushi, Morioka and others that did last were filed as abolished, while Asakawa, Kuzuno and others long gone were counted as surviving. Years are now checked against Wikidata as well; 265 domains lasted until 1871. Domains with only one known year show it (e.g. "1819–")
- Added Bungo-Takada; removed Matsudaira Yoshiyuki's fief, which was not a domain
- The domain data (about 370 KB) is no longer downloaded on the home page, only when you open a prefecture
- The data check now looks at coverage per prefecture, so a prefecture with no domains, an odd number of surviving domains, or Aizu and the like missing or misplaced fails before anything is published

## 3.6.1 · 2026-11-03

- Edo domains completed: only domains that lasted until 1871 were listed, so Aizu, Hamamatsu, Kakegawa, Kōfu, Shirakawa and others that ended around the Boshin War or earlier were missing, and Yamanashi, Tokushima, Tokyo and Okinawa had none at all; Tokushima was dropped because of a wrong year in its article, and Bingo-Fukuyama was placed in Kanagawa. Now 498 domains and 4,257 lords: the 271 that lasted until 1871 first, the rest in a separate group, each with its years. Seven small domains whose lords appear only in the article text (Ōsaka, Tosa-Nakamura and others) were added by hand, each name checked against the article

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
