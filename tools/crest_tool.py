"""战国势力图的家纹旗：各家的家纹图（src/assets/crests/<键>.png）与出处（tools/clan_crests.json）。
    python -X utf8 tools/crest_tool.py          # 抓取、核对并写出
    python -X utf8 tools/crest_tool.py --sheet  # 另存一张总览图 .cache/sengoku/crests-sheet.png，人工看一遍

- 家纹取该家日文维基条目（sengoku_tool.CLANS 的条目名，跟随重定向）信息框的「家紋」与「家紋名称」；
  信息框没有的，只有在 MANUAL 里写明图档与条目原文依据（工具核对原文确实出现在条目里）才收，否则不收（界面用文字旗）。
- 只收 Commons 上公有领域、CC0、CC BY、CC BY-SA 的图，记下作者与许可（LICENSE-CONTENT 与人物卡式的注明）。
- 图统一处理成「白色图案 + 透明底」的 96px 方图：先铺到白底上，四周一圈偏亮就取深色部分为图案（白底黑纹、透明底黑纹），
  偏暗（黑底白纹，如 Commons 上不少「Japanese Crest …」）就取亮色部分；判断错的写进 FLIP 反过来。
- 总称（国人割据等）与一揆、寺社不是家族，不配家纹。
"""
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import sengoku_tool as st  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'clan_crests.json')
IMG = os.path.join(ROOT, 'src', 'assets', 'crests')
CACHE = os.path.join(ROOT, '.cache', 'sengoku')
UA = {'User-Agent': 'japan-explorer-data-tool/1.0 (https://github.com/Nickrockwall/japan-explorer)'}
SIZE = 96

# 不是家族：不配家纹
NOT_FAMILY = {'kofukuji', 'ikko', 'iga_ikki'}
# 信息框没有家纹的：(图档, 家纹名, 条目, 条目里的原文依据)
MANUAL = {
    # 条目开头的总信息框家纹为空，下面「加賀前田家」的信息框写的是加賀梅鉢
    'maeda': ('Japanese crest Kaga Umebachi.svg', '加賀梅鉢', '前田氏', '|家紋=Japanese crest Kaga Umebachi.svg'),
    # 「三木氏」条目没有信息框；「姉小路氏」（即三木氏）的信息框家纹名为剣菱、图档缺，图用 Commons 上标明「剣菱」紋的公有领域图
    'anegakoji': ('Ken Bishi inverted.png', '剣菱', '姉小路氏', '|家紋名称= [https://assets.st-note.com/img/1676440279084-LOs9LC11zM.png {{ruby|剣菱|けんびし}}]'),
    # 堀越公方是足利政知一系（足利将军家的分家），条目没有家纹：用足利氏信息框里的足利二つ引
    'horigoe': ('Ashikaga mon rev.svg', '足利二つ引', '足利氏', '{{ruby|[[引両紋|足利二つ引]]'),
}
# 自动判断底色反了的图：反过来取
FLIP = set()
LICENSES = re.compile(r'^(Public domain|CC0|CC BY(-SA)? [\d.]+( [a-z]+)?|CC BY(-SA)?)$', re.I)


def get(url):
    for attempt in range(6):
        time.sleep(0.5 + 8 * attempt)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
    raise SystemExit('一直限速')


def wikitext(title):
    path = os.path.join(CACHE, f'crest-wt-{re.sub(r"[^\w]", "_", title)}.txt')
    if not os.path.exists(path):
        q = urllib.parse.urlencode({'action': 'parse', 'page': title, 'prop': 'wikitext', 'redirects': 1, 'format': 'json', 'formatversion': 2})
        d = json.loads(get('https://ja.wikipedia.org/w/api.php?' + q))
        os.makedirs(CACHE, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(d.get('parse', {}).get('wikitext', ''))
    with open(path, encoding='utf-8') as f:
        return f.read()


def field(w, name):
    m = re.search(r'^[ \t]*\|[ \t]*' + name + r'[ \t]*=[ \t]*(.*)$', w, re.M)
    return m.group(1).strip() if m else ''


def plain(s):
    """家紋名称 → 纯文字：只取第一个名字（<br> 之前），去掉注释、ruby 读音、链接标记"""
    s = re.split(r'<br\s*/?>', s)[0]
    s = re.sub(r'<ref[^>]*/>|<ref.*?</ref>|\{\{(Sfn|sfn|efn|Efn|要出典|要ページ番号)[^{}]*\}\}', '', s)
    s = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', s)  # 先拆链接，ruby 里常套着链接
    s = re.sub(r'\{\{ruby\|([^|{}]*)\|[^{}]*\}\}', r'\1', s)
    s = re.sub(r"'''?|<[^>]+>|（代表的な家紋）|など$", '', s)
    return re.sub(r'\s+', ' ', s).strip(' 　')


def commons(files):
    out = {}
    for i in range(0, len(files), 40):
        q = urllib.parse.urlencode({'action': 'query', 'titles': '|'.join('File:' + f for f in files[i:i + 40]), 'prop': 'imageinfo',
                                    'iiprop': 'url|extmetadata', 'iiurlwidth': 256, 'format': 'json', 'formatversion': 2})
        d = json.loads(get('https://commons.wikimedia.org/w/api.php?' + q))
        norm = {n['to']: n['from'] for n in d['query'].get('normalized', [])}
        for p in d['query']['pages']:
            name = norm.get(p['title'], p['title']).replace('File:', '')
            ii = (p.get('imageinfo') or [{}])[0]
            em = ii.get('extmetadata', {})
            artist = html.unescape(re.sub(r'<[^>]+>', '', em.get('Artist', {}).get('value', ''))).strip()
            out[name] = {'missing': 'missing' in p, 'thumb': ii.get('thumburl'), 'page': ii.get('descriptionurl'),
                         'license': em.get('LicenseShortName', {}).get('value', ''), 'author': re.sub(r'\s+', ' ', artist)[:80]}
    return out


def mask(raw, flip):
    """任意底色的家纹图 → 白色图案、透明底的方图（返回图与是否按黑底白纹处理）"""
    from io import BytesIO
    from PIL import Image, ImageOps, ImageStat
    im = Image.open(BytesIO(raw)).convert('RGBA')
    bg = Image.new('RGBA', im.size, (255, 255, 255, 255))
    bg.alpha_composite(im)
    lum = ImageOps.autocontrast(ImageOps.grayscale(bg.convert('RGB')), cutoff=1)  # 彩色或灰色的图也拉开明暗
    w, h = lum.size
    e = max(2, min(w, h) // 30)
    ring = [ImageStat.Stat(lum.crop(b)).mean[0] for b in ((0, 0, w, e), (0, h - e, w, h), (0, 0, e, h), (w - e, 0, w, h))]
    dark = (sum(ring) / 4 < 128) != flip
    alpha = lum if dark else ImageOps.invert(lum)
    alpha = alpha.point(lambda v: 0 if v < 40 else 255 if v > 215 else round((v - 40) * 255 / 175))
    box = alpha.getbbox()
    if box:
        alpha = alpha.crop(box)
    side = max(alpha.size)
    sq = Image.new('L', (side, side), 0)
    sq.paste(alpha, ((side - alpha.width) // 2, (side - alpha.height) // 2))
    sq = sq.resize((SIZE, SIZE), Image.LANCZOS)
    out = Image.new('RGBA', (SIZE, SIZE), (255, 255, 255, 0))
    out.putalpha(sq)
    return out, dark


def main():
    plan, bad = {}, []
    for k, v in st.CLANS.items():
        art = v[4]
        if not art or k in NOT_FAMILY:
            continue
        w = wikitext(art)
        f, n = field(w, '家紋'), plain(field(w, '家紋名称'))
        f = re.sub(r'^\[\[(?:File|ファイル|画像):([^|\]]+).*$', r'\1', f).strip()
        if k in MANUAL:
            f, n, src, quote = MANUAL[k]
            if quote not in wikitext(src):
                bad.append(f'{k}：依据原文不在「{src}」里')
                continue
            art = src
        if not f or not re.search(r'\.(svg|png|jpe?g|gif)$', f, re.I):
            print(f'无家纹 {k}（{art}）')
            continue
        plan[k] = {'file': f.replace('_', ' '), 'name': n, 'wiki': art}
    meta = commons(sorted({p['file'] for p in plan.values()}))
    os.makedirs(IMG, exist_ok=True)
    out = {}
    for k, p in plan.items():
        m = meta.get(p['file'])
        if not m or m['missing'] or not m['thumb']:
            bad.append(f'{k}：Commons 上找不到 {p["file"]}')
            continue
        if not LICENSES.match(m['license']):
            bad.append(f'{k}：{p["file"]} 的许可是 {m["license"]}，不收')
            continue
        img, dark = mask(get(m['thumb']), k in FLIP)
        if dark:
            print(f'黑底白纹 {k}（{p["file"]}）')
        img.save(os.path.join(IMG, f'{k}.png'), optimize=True)
        # 家纹名夹着假名，转简体会变成「并び鹰の羽」这样的怪样子：三种界面都显示日文原名
        author = '' if m['license'] == 'Public domain' or m['author'].startswith('No machine-readable') else m['author']
        out[k] = {**p, 'license': m['license'], 'author': author, 'page': m['page']}
    for b in bad:
        print('不通过', b)
    for f in os.listdir(IMG):
        if f.endswith('.png') and f[:-4] not in out:
            os.remove(os.path.join(IMG, f))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'家纹 {len(out)} 家，写出 {OUT}')
    if '--sheet' in sys.argv:
        from PIL import Image, ImageDraw
        keys = sorted(out)
        cols = 8
        sheet = Image.new('RGB', (cols * 120, ((len(keys) + cols - 1) // cols) * 130), (24, 24, 28))
        d = ImageDraw.Draw(sheet)
        for i, k in enumerate(keys):
            im = Image.open(os.path.join(IMG, f'{k}.png'))
            x, y = (i % cols) * 120 + 12, (i // cols) * 130 + 6
            sheet.paste((212, 163, 115), (x, y, x + SIZE, y + SIZE), im)
            d.text((x, y + SIZE + 4), k, fill=(220, 220, 220))
        sheet.save(os.path.join(CACHE, 'crests-sheet.png'))
    if bad:
        sys.exit(1)


if __name__ == '__main__':
    main()
