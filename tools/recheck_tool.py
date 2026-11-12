"""第二轮核对（3.40）：各县的方言例句、拉面、地酒，对照日文维基找出没有出处的条目，打印出来人工看。

    python -X utf8 tools/recheck_tool.py

- 方言：dialect.name 的条目（找不到就试「○○弁」「○○方言」）与本县条目里，例句（去掉「〜」、标点）要出现；
  例句太短（≤2 字）或是常见词时只看条目是否提到。
- 地酒：sake.brand 或 sake.brewery（去掉括注）要有日文维基条目，或出现在「日本酒の銘柄一覧」/ 本县条目里。
- 拉面：style_name 里的地名 + ラーメン 的条目（如「京都ラーメン」），或「ご当地ラーメン」条目里提到本县。
不改数据；输出 .cache/recheck/report.txt，人工核对后改 src/data/prefectures 与 i18n 覆盖层。
"""
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import api, pages, text_of  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, '.cache', 'recheck')


def texts(titles):
    got = pages(sorted(set(titles)), 'revisions', rvprop='content', rvslots='main')
    return {t: text_of(p) if p and not p.get('missing') else '' for t, p in got.items()}


def search_hits(phrase):
    """日文维基全文检索这句话（加引号），命中的条目标题里有 弁 / 方言 / 言葉 / 語 的才算有出处"""
    d = api({'action': 'query', 'list': 'search', 'srsearch': f'"{phrase}"', 'srlimit': 20, 'srnamespace': 0})
    return [x['title'] for x in d.get('query', {}).get('search', []) if re.search(r'弁|方言|言葉|語|ことば', x['title'])]


def norm(s):
    return re.sub(r'[〜～ー、。！？!?\s「」（）()…・]', '', s)


def main():
    os.makedirs(OUT, exist_ok=True)
    prefs = [json.load(open(f, encoding='utf-8')) for f in sorted(glob.glob(os.path.join(ROOT, 'src', 'data', 'prefectures', '*.json')))]
    names = []
    for p in prefs:
        d = p['dialect']['name']
        base = re.sub(r'(弁|方言|言葉|ことば)$', '', d)
        names += [d, f'{base}弁', f'{base}方言', p['name']['kanji'], f'{p["name"]["kanji"].rstrip("都府県道")}弁']
    T = texts(names + ['日本酒の銘柄一覧', 'ご当地ラーメン'])
    report = []
    for p in prefs:
        d = p['dialect']['name']
        base = re.sub(r'(弁|方言|言葉|ことば)$', '', d)
        pool = ' '.join(T.get(x, '') for x in (d, f'{base}弁', f'{base}方言', f'{p["name"]["kanji"].rstrip("都府県道")}弁'))
        if not pool.strip():
            report.append(f'{p["id"]:02d} 方言条目找不到：{d}')
        flat = norm(pool)
        for ph in p['dialect']['phrases']:
            x = norm(ph['phrase'])
            if x and x not in flat:
                # 去掉句尾常见的变化再试一次（「〜しとる」→「しとる」已去）
                core = re.split(r'[ぞよねわなかさ]$', x)[0]
                if not core or core not in flat:
                    # 第二步：全文检索（例句常写在「関西弁」「名古屋弁」这类上一级或别名条目里）
                    q = re.sub(r'^[〜～]|[？?！!]$', '', ph['phrase'].split(' / ')[0]).strip()
                    hits = search_hits(q)
                    if not hits:
                        report.append(f'{p["id"]:02d} 方言例句没找到出处：{ph["phrase"]}（{ph["meaning"]}）')
    # 地酒
    ja = {}
    for f in glob.glob(os.path.join(ROOT, 'src', 'data', 'i18n', 'ja', 'prefectures', '*.json')):
        o = json.load(open(f, encoding='utf-8'))
        ja[int(os.path.basename(f)[:2])] = o
    for p in prefs:  # 日文名覆盖中文底本（中文是简体字形，对不上日文条目）
        o = ja.get(p['id'], {})
        if o.get('sake') and p.get('sake'):
            p['sake'] = {**p['sake'], **{k: v for k, v in o['sake'].items() if k in ('brand', 'brewery')}}
    sake_titles = []
    for p in prefs:
        s = p.get('sake') or {}
        b = re.sub(r'（.*?）|\(.*?\)', '', s.get('brewery', '')).strip()
        sake_titles += [s.get('brand', ''), b]
    S = texts([x for x in sake_titles if x])
    lst = T.get('日本酒の銘柄一覧', '')
    for p in prefs:
        s = p.get('sake') or {}
        if not s:
            continue
        b = re.sub(r'（.*?）|\(.*?\)', '', s.get('brewery', '')).strip()
        ok = S.get(s['brand']) or S.get(b) or s['brand'] in lst or s['brand'] in T.get(p['name']['kanji'], '')
        if not ok:
            report.append(f'{p["id"]:02d} 地酒没有出处：{s["brand"]} / {s.get("brewery")}')
    # 拉面
    gl = T.get('ご当地ラーメン', '')
    for p in prefs:
        r = p.get('ramen') or {}
        if not r:
            continue
        if p['name']['kanji'].rstrip('都府県道') not in gl and p['name']['kanji'] not in gl:
            report.append(f'{p["id"]:02d} 拉面：ご当地ラーメン 条目没提到本县（{r.get("style_name")}）')
    open(os.path.join(OUT, 'report.txt'), 'w', encoding='utf-8').write('\n'.join(report))
    print('\n'.join(report))
    print(f'共 {len(report)} 条待人工核对')


if __name__ == '__main__':
    main()
