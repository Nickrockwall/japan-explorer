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
- 代码文件中的创作性文字：向导人设、离线解答模板、界面文案等（`src/js/guide.js`、`src/js/i18n.js`、`src/js/lang/`）
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
| `src/3d/vendor/`（立体战国图 3d.html） | [three.js](https://threejs.org/) r170（`three.module.min.js` 与 OrbitControls / MapControls / BufferGeometryUtils） | MIT（见 `src/3d/vendor/three-LICENSE`） |
| `src/3d/terrain/`（立体战国图的地形） | [国土地理院 標高タイル](https://maps.gsi.go.jp/development/ichiran.html#dem)（基盤地図情報数値標高モデル）を加工して作成；粗图的蓝色通道是地球地図日本（国土地理院）的土地覆盖（lc） | 国土地理院コンテンツ利用規約（须注明出典；页面底部已写） |
| `src/3d/water.json`（立体战国图的湖与河） | 地球地図日本（国土地理院）第 2.2 版的内水面与河川 | 须注明「出典：地球地図日本」 |
| `src/3d/castles.json`（立体战国图的城） | 名称（含英文名）与坐标取自 [Wikidata](https://www.wikidata.org/)（CC0）；筑城 / 废城年取自[日本語版ウィキペディア](https://ja.wikipedia.org/)各城条目信息框 | 事实数据 |
| `src/3d/edo.json`（立体图江户与 1871 年的藩领） | 由 `tools/kyudaka.json`（国立历史民俗博物馆「旧高旧領取調帳データベース」按市区町村的汇总）取各市区町村石高最多的领主拼成；藩名、藩厅与藩主见 `han.json`、`tools/seats.json`；1871 年的县名对照[日本語版ウィキペディア](https://ja.wikipedia.org/)各藩条目 | 同 kyudaka（非营利、注明出处，只放汇总结果）；县名为事实数据 |
| `src/3d/meiji.json`（立体图 1876 / 1888 年的府县） | 今天的都道府县与市区町村边界按规则拼成，合并与分立对照[日本語版ウィキペディア](https://ja.wikipedia.org/)各县条目；英文名来自 [Wikidata](https://www.wikidata.org/)（CC0） | 事实数据 |
| `src/3d/kamakura.json`（立体图镰仓各国的守护） | [日本語版ウィキペディア](https://ja.wikipedia.org/)各国条目「守護」一节的鎌倉幕府守护名单（人名与任期） | 事实数据 |
| `src/3d/kaido.json`（五街道的宿场与明治最早的铁路） | 宿场名单与坐标取自[日本語版ウィキペディア](https://ja.wikipedia.org/)各街道与宿场条目（没写坐标的取 [Wikidata](https://www.wikidata.org/) P625）；铁路开业年与车站坐标取自各车站条目 | 事实数据 |
| `src/3d/kodai.json`（古代的城柵与平城京） | [日本語版ウィキペディア](https://ja.wikipedia.org/)各城柵条目与「平城京」条目（年份、规模）及其坐标 | 事实数据 |
| `src/fonts/` | [Noto Serif SC / JP](https://github.com/notofonts/noto-cjk)（按网站用到的字切片） | SIL Open Font License 1.1（见 `src/fonts/OFL.txt`） |
| `src/assets/geojson/japan.json` | 地球地図日本（国土地理院），经 [dataofjapan/land](https://github.com/dataofjapan/land) 转换 | 须注明「出典：地球地図日本」；商用须向国土地理院报告 |
| `src/data/municipalities/` 的边界，及由其合并而成的 `src/data/provinces.json` | 「国土数値情報（行政区域データ）」（国土交通省）を加工して作成，经 [smartnews-smri/japan-topography](https://github.com/smartnews-smri/japan-topography) 简化 | 国土数値情報の利用規約 |
| `src/data/municipalities/` 的读音、人口、英文名 | [Wikidata](https://www.wikidata.org/) | CC0 |
| `src/assets/hiroshige/` | 歌川広重『六十余州名所図会』（1853–56），图像取自 [Wikimedia Commons](https://commons.wikimedia.org/)（各图原始页面见 `src/data/hiroshige.json` 的 `source`） | 公有领域（Public domain）。画题译文与地点整理属本项目内容 |
| `src/data/koku_sites.json`（一宫·国府·国分寺的名称、所在地与现状） | 整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)「一宮」「国府」「国分寺」条目的一览表与各社寺条目的坐标 | **CC BY-SA 4.0**（不适用 NC） |
| `src/data/kokuryoku.json` 中的江户人口（1721、1846）与石高（1834） | 整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)「江戸時代の日本の人口統計」的旧国别人口表 | **CC BY-SA 4.0**（不适用 NC） |
| `src/assets/emblems/`（47 都道府县章）与 `src/data/emblems.json` | [Wikimedia Commons](https://commons.wikimedia.org/) 各县章 SVG（文件名见 emblems.json 的 `commons`），转成透明底 PNG | **公有领域**（工具逐个核对，只收公有领域 / CC0） |
| `src/assets/people/`（人物肖像） | 各人物 Wikidata P18 指向的 [Wikimedia Commons](https://commons.wikimedia.org/) 图像（文件名见 `src/data/people.json` 的 `commons`），缩到宽 240px | 多为**公有领域**；山名宗全（Musuketeer.3）、岛津义久（Ginger1192）两张为 **CC BY-SA 3.0**，卡片上注明作者与许可（`tools/people_tool.py` 逐个核对许可，其余许可不收） |
| `src/assets/castles/`（城的照片，3.40） | 100名城、続100名城与现存天守各城 Wikidata P18（没有则取日文维基条目首图）指向的 [Wikimedia Commons](https://commons.wikimedia.org/) 照片，长边缩到 480px、转为 WebP；每张的文件页、作者与许可见 `src/3d/castle_photos.json` | **公有领域 / CC0**，或 **CC BY / CC BY-SA**（2.0–4.0、2.1 jp）——卡片上注明作者与许可并链接到文件页；CC BY-SA 的缩小版按原许可提供。`tools/castle_photo_tool.py` 逐张核对许可，其余许可不收 |
| `src/assets/crests/`（家纹旗） | 各家日文维基条目信息框「家紋」指向的 [Wikimedia Commons](https://commons.wikimedia.org/) 图像（文件、作者与许可见 `tools/clan_crests.json`），统一处理成 96px 单色图 | **公有领域**、**CC0**、**CC BY 2.5** 或 **CC BY-SA 3.0 / 4.0**（多为 Mukai 绘制）；势力总览卡片注明家纹名、许可、作者并链接到文件页（`tools/crest_tool.py` 逐个核对许可，其余许可不收）。改编图同样按原许可发布 |
| `src/data/sengoku.json` 中的各国石高（`koku`，1598 年太阁检地高） | 整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)「石高」的「旧国別石高の変遷」表 | **CC BY-SA 4.0**（不适用 NC） |
| `src/3d/peaks.json`、`src/data/ages.json`、`tools/han_seats.json`（3.40） | 百名山的名单与标高按日文维基「日本百名山」，山顶坐标取各山条目或 Wikidata；人物生卒年取 Wikidata（CC0）；藩厅坐标取藩厅 / 藩条目或 Wikidata | 事实数据；Wikidata 为 CC0 |
| `src/data/sengoku.json`、`rulers.json`、`people.json`、`regimes.json`、`region_eras.json` | 势力归属、天皇 / 将军 / 执权在位年份、各时期的实际掌权者与分界年份按[日本語版ウィキペディア](https://ja.wikipedia.org/)各条目整理并核对（事实数据）；人物简介、「实权」各段与冲绳 / 北海道地区年表的说明为本项目自行撰写 | 本项目内容（简介）；年份等事实不受著作权保护 |
| `src/data/kako.json`、`src/data/han.json` | 日期、事件与藩主名单整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)的日期条目、「藩の一覧」与各藩条目（藩主在位年份取各藩主条目的「○○藩主」导航框），名称与坐标取自 Wikidata（CC0）；彼时今日的日文原句摘自维基条目 | 日文原句为 **CC BY-SA 4.0**（不适用 NC）；其余为事实数据 |
| `tools/domains.json` 及数据包中的 `domains`（幕末各郡的领主与町村数） | 整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)各郡条目「近世以降の沿革」中的《旧高旧領取調帳》表；藩的英文名来自 [Wikidata](https://www.wikidata.org/)（CC0） | **CC BY-SA 4.0**（不适用 NC） |
| `src/data/korea/regions.json` 的边界（朝鲜半岛模式） | [geoBoundaries](https://www.geoboundaries.org/)（gbOpen）：韩国 ADM1 取自 Natural Earth，ADM2 取自 citypopulation.de；朝鲜 ADM1/ADM2 取自 WFP / OCHA ROAP。按现行区划合并、简化 | 韩国 ADM1 公有领域；韩国 ADM2 CC BY 3.0；朝鲜 CC BY 3.0 IGO（均须署名） |
| `src/data/korea/regions.json` 与 `counties/` 的名称、人口、面积，独岛 / 竹岛的坐标 | [Wikidata](https://www.wikidata.org/) | CC0 |
| `src/data/korea/counties/`、`eras/` 的边界 | 同上 geoBoundaries（韩国 ADM3 的邑面洞用于补全灵光郡、拼出仁川检丹区：韩国公共누리第 1 类，须注明出处） | 同上 |
| `src/data/korea/hyanggyo.json`（半岛乡校的位置与名称） | [Wikidata](https://www.wikidata.org/)；汉字写法取自[한국어 위키백과](https://ko.wikipedia.org/)各乡校条目 | Wikidata 部分 CC0；汉字写法 **CC BY-SA 4.0**（不适用 NC） |
| `src/data/korea/sul.json`（半岛传统酒） | 整理自[한국어 위키백과](https://ko.wikipedia.org/)各市道「무형문화재」名录、「대한민국식품명인」名录与各酒条目 | **CC BY-SA 4.0**（不适用 NC） |
| `src/assets/daedong/`（《大东舆地图》局部） | 金正浩《大东舆地图》（1861），首尔大学奎章阁藏本，图像取自 [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Daedongyeojido-full.jpg)，由 `tools/build_daedong.py` 裁切 | 公有领域 |
| `src/data/korea/power.json`（1432 年各区的户、口、垦田） | 《世宗实录·地理志》原文（15 世纪，公有领域），取自国史编纂委员会[「조선왕조실록」网站](https://sillok.history.go.kr/)，只用数字；郡县今地按 `tools/sejong_locate.py` 用[한국어 위키백과](https://ko.wikipedia.org/)核对 | 公有领域（只取原文数字） |
| `src/data/korea/eras/silla.json`、`samguk.json` 的州 / 国归属 | 整理自[한국어 위키백과](https://ko.wikipedia.org/)「신라의 행정 구역」九州表格；高丽各道据《高丽史·地理志》（[维基文库](https://zh.wikisource.org/)，公有领域） | **CC BY-SA 4.0**（新罗九州部分，不适用 NC） |
| `src/data/korea/battles.json`（半岛古战场） | 自写，内容据[한국어](https://ko.wikipedia.org/)、[English](https://en.wikipedia.org/)、[日本語](https://ja.wikipedia.org/)维基百科各战役条目核对 | CC BY-NC 4.0（本项目） |
| `tools/kyudaka.json` 及户籍数据包中的 `kyu`（今天各市区町村里幕末各村的领主与石高合计） | 国立历史民俗博物馆[「旧高旧領取調帳データベース」](https://www.rekihaku.ac.jp/doc/gaiyou/kyuudaka.html)（データベースれきはく，木村礎校订《旧高旧領取調帳》为底本）；村的位置用下面两项 CODH 数据 | 按[国立歴史民俗博物館データベース利用規程](https://www.rekihaku.ac.jp/doc/db_kitei.pdf)非营利使用、注明出处；网站只放按市区町村汇总的结果，不转载原始记录 |
| `tools/mura.json` 中维基没有写到的町村、`tools/kyudaka.json` 的旧市町村对应、`tools/heisei.json`（平成合并前的市町村与变动年份，另用其「市区町村 ID 一览」的有效期间） | ROIS-DS 人文学开放数据共同利用中心（CODH）[《歴史的行政区域データセットβ版》](https://geoshape.ex.nii.ac.jp/city/)（1920、1985、1995 年市区町村边界，国土数値情報「行政区域データ」加工）与[《日本歴史地名大系』地名項目データセット》](https://geoshape.ex.nii.ac.jp/nrct/)（村的坐标） | **CC BY 4.0**：『歴史的行政区域データセットβ版』（CODH作成）、『日本歴史地名大系』地名項目データセット（CODH作成） doi:10.20676/00000448 |
| `tools/wamyo.json` 及户籍数据包中的 `wamyo`（各郡的古代郷名与读音） | 《和名類聚抄》（10 世纪），据奈良文化财研究所[「古代地名検索システム」](https://chimei.nabunken.go.jp/)只取《和名类聚抄》本身所载的郷名与读音 | 典籍内容为公有领域（事实）；注明检索系统出处 |
| `src/data/han.json` 中部分藩主的在位年份 | 日文维基与 Wikidata 都没有的，取[English Wikipedia](https://en.wikipedia.org/)各藩条目的藩主表（按汉字名对上） | 事实数据 |
| `tools/yurai.json`（地名来历，124 条） | 说明全部自行撰写，不转载原文；98 条按[日本語版ウィキペディア](https://ja.wikipedia.org/)各市区条目核对关键词与年份，其余 26 条的出处为岩手县「いわての文化情報大事典」（盛冈等县内 11 市）；青森（市民图书馆）、福岛、水户、前桥、福井、静冈（县）、大津、松江、德岛、松山、佐贺（县）、长崎、熊本、大分、鹿儿岛（县）等市（县）政府官方网页 | 说明为本项目自行撰写，只核对关键词与年份 |
| `tools/mura.json` 中取自维基的明治町村、`tools/main_gun.json`（市区町村的主要郡）、`tools/seats.json`（城下町与藩厅）、数据包 `ken-*.json` 的明治府县沿革 | 整理自[日本語版ウィキペディア](https://ja.wikipedia.org/)各市区町村、郡与藩条目（只取名称、年份与对应关系） | 事实数据；整理所据条目为 **CC BY-SA 4.0** |
| `tools/districts.json` 及市区町村数据中的旧郡（`old_districts`） | [日本語版ウィキペディア](https://ja.wikipedia.org/) 各郡条目 | **CC BY-SA 4.0**（这部分不适用 NC，按 CC BY-SA 4.0 继承） |

作品名、人物名、商标（动画、大河剧、酒造、拉面店等）归各自权利人所有，本项目仅作介绍性引用。
Titles, names and trademarks (anime, taiga dramas, breweries, ramen shops, etc.) belong to their respective owners and are referenced descriptively.
作品名・人名・商標（アニメ、大河ドラマ、酒蔵、ラーメン店など）は各権利者に帰属し、紹介目的で言及しています。
