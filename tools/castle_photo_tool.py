"""城的照片（3.40）：100名城、続100名城与现存天守（castles.json 的 h100 / z100 / tenshu），立体图城卡片上放一张实景照。

    python -X utf8 tools/castle_photo_tool.py

- 图：Wikidata P18（没有就取日文维基条目首图 pageimage），跟人物肖像同一套许可规矩（people_tool）：
  公有领域 / CC0 直接收；CC BY / CC BY-SA 要有作者，卡片上写作者与许可；其余（含 GFDL-only、无许可信息）不收。
- 人工看过不是城本身的图（地图、纹章、城址碑……）写进 NOT_PHOTO。
- 存 src/assets/castles/<QID>.webp（长边 480px，WebP q70，约 20–40 KB），卡片打开时才下载。
输出 src/3d/castle_photos.json：{QID: [文件, 许可, 作者或空, Commons 文件页名]}，立体图开页时与 castles.json 一起下载（约 20 KB）。
"""
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from people_tool import api, UA, FREE, ATTRIB  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'src', '3d', 'castle_photos.json')
IMG = os.path.join(ROOT, 'src', 'assets', 'castles')
CACHE = os.path.join(ROOT, '.cache', 'castle_photos.json')
NOT_PHOTO = {'Edo P detail.jpg', 'KasugayamaCastle-print.jpg'}  # 人工看过、不是实景照的图（屏风画、版画）


def main():
    castles = [c for c in json.load(open(os.path.join(ROOT, 'src', '3d', 'castles.json'), encoding='utf-8')) if c.get('h100') or c.get('z100') or c.get('tenshu')]
    cache = json.load(open(CACHE, encoding='utf-8')) if os.path.exists(CACHE) else {}
    todo = [c['q'] for c in castles if c['q'] not in cache]
    for i in range(0, len(todo), 50):
        d = api('https://www.wikidata.org/w/api.php', {'action': 'wbgetentities', 'ids': '|'.join(todo[i:i + 50]), 'props': 'claims'})
        for q, e in d.get('entities', {}).items():
            files = [c['mainsnak'].get('datavalue', {}).get('value') for c in e.get('claims', {}).get('P18', [])]
            cache[q] = {'file': next((f for f in files if f), None)}
    need = [c for c in castles if not cache[c['q']].get('file') and 'pageimage' not in cache[c['q']]]
    for i in range(0, len(need), 40):
        part = need[i:i + 40]
        d = api('https://ja.wikipedia.org/w/api.php', {'action': 'query', 'titles': '|'.join(c['wiki'] for c in part), 'prop': 'pageimages',
                                                      'piprop': 'name', 'redirects': 1, 'formatversion': 2})
        names = {pg['title']: pg.get('pageimage') for pg in d['query']['pages']}
        alias = {r['from']: r['to'] for r in d['query'].get('redirects', [])}
        for c in part:
            pi = names.get(alias.get(c['wiki'], c['wiki']))
            cache[c['q']]['pageimage'] = pi
            cache[c['q']]['file'] = cache[c['q']]['file'] or pi
    os.makedirs(IMG, exist_ok=True)
    out, skipped = {}, []
    for c in castles:
        e = cache[c['q']]
        f = e.get('file')
        if not f or f in NOT_PHOTO or re.search(r'\.(svg|pdf|tif)$', f, re.I) or re.search(r'(^|[_ ])map|地図|紋|crest|location', f, re.I):
            skipped.append(f'{c["ja"]}（{f or "没有图"}）')
            continue
        if 'license' not in e:
            d = api('https://commons.wikimedia.org/w/api.php', {'action': 'query', 'titles': 'File:' + f, 'prop': 'imageinfo',
                                                                 'iiprop': 'url|extmetadata', 'iiurlwidth': 480})
            ii = (next(iter(d['query']['pages'].values())).get('imageinfo') or [{}])[0]
            meta = ii.get('extmetadata', {})
            e['license'] = meta.get('LicenseShortName', {}).get('value', '')
            e['author'] = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', meta.get('Artist', {}).get('value', ''))).strip()[:80]
            e['thumb'] = ii.get('thumburl')
        lic = e['license'].lower()
        free = lic.startswith(FREE)
        if not (free or (lic.startswith(ATTRIB) and e['author'])) or not e.get('thumb'):
            skipped.append(f'{c["ja"]}（{f}：{e["license"] or "无许可信息"}）')
            continue
        dest = os.path.join(IMG, f'{c["q"]}.webp')
        if not os.path.exists(dest):
            for wait in (1, 10, 30, 60):
                time.sleep(wait)
                try:
                    with urllib.request.urlopen(urllib.request.Request(e['thumb'], headers=UA), timeout=60) as r:
                        im = Image.open(io.BytesIO(r.read())).convert('RGB')
                    break
                except urllib.error.HTTPError as err:
                    if err.code != 429:
                        raise
            im.thumbnail((480, 480))
            im.save(dest, 'WEBP', quality=70, method=6)
        out[c['q']] = [f'src/assets/castles/{c["q"]}.webp', e['license'], '' if free else e['author'], 'File:' + f]
    json.dump(cache, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    size = sum(os.path.getsize(os.path.join(IMG, x)) for x in os.listdir(IMG))
    print(f'目标 {len(castles)} 座，收 {len(out)} 张（{size // 1024} KB）')
    print('不收：', skipped)


if __name__ == '__main__':
    main()
