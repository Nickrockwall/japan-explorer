# 版权与许可 · Copyright & Licensing · 著作権とライセンス

© 2026 Nickrockwall

本项目采用**双许可**：代码用 MIT，内容用 CC BY-NC 4.0。第三方素材按各自的条款，不在上述许可之内。

This project is **dual-licensed**: code under MIT, content under CC BY-NC 4.0. Third-party material keeps its own terms and is not covered by either.

本プロジェクトは**デュアルライセンス**です。コードは MIT、コンテンツは CC BY-NC 4.0。第三者の素材はそれぞれの条件に従い、上記のライセンスには含まれません。

## 1. 代码 · Code · コード — [MIT](LICENSE)

`index.html`、`sw.js`、`manifest.webmanifest`、`src/js/`、`src/css/`、`tools/*.py`、`tests/`

可自由使用、修改、商用，须保留版权声明与许可文本。
Free to use, modify and use commercially, as long as the copyright notice and license text are kept.
商用を含め自由に利用・改変できます。著作権表示とライセンス文は残してください。

## 2. 内容 · Content · コンテンツ — [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh-hans)

- `src/data/` 下的史料文字与整理数据：各县沿革、人设、地缘梗、拉面与地酒、御朱印、合战与时代、圣地巡礼的场景与贴士，及其英日译文与数据包（第 3 节所列第三方数据除外）
- 代码文件中的创作性文字：向导人设、离线解答模板等（`src/js/guide.js`、`src/js/i18n.js`）
- 图片：`src/assets/og-cover*.png`、`src/assets/icons/`
- README 与说明文字

**署名**：注明「Japan Explorer by Nickrockwall」并附项目链接 <https://github.com/Nickrockwall/japan-explorer>，标明是否做过修改。
**非商业**：不得用于商业目的。商用请先联系作者（GitHub Issue）。

**Attribution**: credit "Japan Explorer by Nickrockwall" with a link to <https://github.com/Nickrockwall/japan-explorer>, and indicate if changes were made.
**NonCommercial**: no commercial use. For commercial licensing, contact the author via a GitHub issue.

**表示**：「Japan Explorer by Nickrockwall」とプロジェクトへのリンクを記載し、改変の有無を示してください。
**非営利**：営利目的での利用はできません。商用利用は GitHub の Issue でご相談ください。

## 3. 第三方素材 · Third-party material · 第三者の素材

| 文件 / File | 来源 / Source | 条款 / Terms |
|---|---|---|
| `src/vendor/echarts*` | [Apache ECharts](https://echarts.apache.org/) | Apache-2.0（见 `src/vendor/echarts-LICENSE`、`echarts-NOTICE`） |
| `src/assets/geojson/japan.json` | 地球地図日本（国土地理院），经 [dataofjapan/land](https://github.com/dataofjapan/land) 转换 | 须注明「出典：地球地図日本」；商用须向国土地理院报告 |
| `src/data/municipalities/` 的边界，及由其合并而成的 `src/data/provinces.json` | 「国土数値情報（行政区域データ）」（国土交通省）を加工して作成，经 [smartnews-smri/japan-topography](https://github.com/smartnews-smri/japan-topography) 简化 | 国土数値情報の利用規約 |
| `src/data/municipalities/` 的读音、人口、英文名 | [Wikidata](https://www.wikidata.org/) | CC0 |
| `src/assets/hiroshige/` | 歌川広重『六十余州名所図会』（1853–56），图像取自 [Wikimedia Commons](https://commons.wikimedia.org/)（各图原始页面见 `src/data/hiroshige.json` 的 `source`） | 公有领域（Public domain）。画题译文与地点整理属本项目内容 |
| `src/data/koku_sites.json`（一宫·国府·国分寺的名称、所在地与现状） | 整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)「一宮」「国府」「国分寺」条目的一览表与各社寺条目的坐标 | **CC BY-SA 4.0**（不适用 NC） |
| `src/data/kokuryoku.json` 中的江户人口（1721、1846）与石高（1834） | 整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)「江戸時代の日本の人口統計」的旧国别人口表 | **CC BY-SA 4.0**（不适用 NC） |
| `tools/domains.json` 及数据包中的 `domains`（幕末各郡的领主与町村数） | 整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)各郡条目「近世以降の沿革」中的《旧高旧領取調帳》表；藩的英文名来自 [Wikidata](https://www.wikidata.org/)（CC0） | **CC BY-SA 4.0**（不适用 NC） |
| `tools/districts.json` 及市区町村数据中的旧郡（`old_districts`） | [日本語版ウィキペディア](https://ja.wikipedia.org/) 各郡条目 | **CC BY-SA 4.0**（这部分不适用 NC，按 CC BY-SA 4.0 继承） |

作品名、人物名、商标（动画、大河剧、酒造、拉面店等）归各自权利人所有，本项目仅作介绍性引用。
Titles, names and trademarks (anime, taiga dramas, breweries, ramen shops, etc.) belong to their respective owners and are referenced descriptively.
作品名・人名・商標（アニメ、大河ドラマ、酒蔵、ラーメン店など）は各権利者に帰属し、紹介目的で言及しています。
