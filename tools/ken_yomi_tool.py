"""明治初年（1871–）县名的读音（3.46），给英文的县名用：

    python -X utf8 tools/ken_yomi_tool.py

对象：bundle/ken-en.json 里还写着日文的县名（「花房県」这样，英文没有出处）。
出处只收日文维基原文写明的：
  ① 县条目或藩条目里「X県'''（よみけん）」或「X県（よみけん）」；
  ② 县由同名的藩改称（藩条目里写着「→ X県」或「X県」），藩条目开头「X藩'''（よみはん）」。
找不到的照旧写日文。输出 tools/ken_kana.json：{县名: [读音, 出处条目]}，build_bundle 的 domains().ken 用。
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from pilgrimage_tool import pages  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUT = os.path.join(ROOT, 'tools', 'ken_kana.json')
KANA = r'([ぁ-んゔー]{2,12})'


def names():
    s = open(os.path.join(ROOT, 'src', 'data', 'bundle', 'ken-en.json'), encoding='utf-8').read()
    out = set()
    for n in re.findall(r'"([^"\x00-\x7f]{1,20}県)"', s):
        out.update(x for x in n.split('・') if x.endswith('県'))
    return sorted(out)


def text(pg):
    return pg['revisions'][0]['slots']['main']['content'] if pg.get('revisions') else ''


def find(ken, txts):
    stem = r"(?<![一-龥々ヶ])" + re.escape(ken[:-1])  # 「伊勢亀山県（いせかめやまけん）」不能算亀山県
    for title, t in txts:
        m = re.search(stem + r"県(?:\]\]|'{3})?\s*[（(]\s*" + KANA + r'けん\s*[）)、，,：:/／]', t)
        if m:
            return m.group(1), title
    for title, t in txts:
        if not t or ken not in t:
            continue
        m = re.search(stem + r"藩'''\s*[（(]\s*" + KANA + r'はん\s*[）)、，,：:/／]', t)
        if m:
            return m.group(1), title
    return None


def main():
    old = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
    todo = names()
    titles = [t for k in todo for t in (k, k[:-1] + '藩')]
    got = pages(titles, 'revisions', rvprop='content', rvslots='main')
    out = dict(old)
    for k in todo:
        r = find(k, [(t, text(got.get(t, {}))) for t in (k, k[:-1] + '藩')])
        if r:
            out[k] = list(r)
    json.dump(out, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=0, sort_keys=True)
    miss = [k for k in todo if k not in out]
    print(f'{len(todo)} 个县 → 找到读音 {len([k for k in todo if k in out])}，没有出处 {len(miss)}：{"、".join(miss)}')


if __name__ == '__main__':
    main()
