"""半岛详卡「大东舆地图上的这里」：金正浩《大东舆地图》（1861）里各区所在的那一块。
    pip install pillow numpy scipy     # 仅生成时需要，网站本身不依赖
    python -X utf8 tools/build_daedong.py          # 用已存的配准参数裁图
    python -X utf8 tools/build_daedong.py --fit    # 重新配准（几分钟），结果写进 tools/daedong_fit.json
图像：Wikimedia Commons「Daedongyeojido-full.jpg」（17837×30000，公有领域；拼接自首尔大学奎章阁所藏本）与同一来源的
小图「Daedongyeojido-small.png」（1177×1977）。原图约 104MB，下载缓存在 .cache/korea/daedong/，按 JPEG 半尺寸解码。
配准：古图没有经纬网，只能和今天的海岸线对齐。小图上线条密的地方是陆地（山脉、河流），空白处是海；
用三次多项式把小图像素映射到经纬度：先让它与今天的半岛陆地（regions.json）重合得最好（IoU 约 0.87），
再细调使「海岸线平均距离（公里）+ 30 ×（1 − IoU）」最小：只看面积时海岸曲折的南部会偏二三十公里，
只看海岸线又会把内陆扭歪，两者一起算。
济州岛在古图上离本土的距离不成比例、郁陵岛位置也偏，二者都不参与拟合；济州与罗先按古图上的位置手工框出（MANUAL）。
古图本身各处比例不一，局部仍可能偏十几公里，所以每块都留足边（MARGIN、MIN_KM），界面上注明是估算。
外框只按面积够大、离主体不远的陆块算（ISLAND、FAR_KM），远处的岛（全南的可居岛、仁川的白翎岛）不把框撑大。
输出：src/assets/daedong/NN.jpg（长边 ≤ LONG 像素）与 src/data/korea/daedong.json（{id: [宽, 高]}）。
"""
import json
import os
import sys
import urllib.request

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, optimize

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
CACHE = os.path.join(ROOT, '.cache', 'korea', 'daedong')
FIT = os.path.join(ROOT, 'tools', 'daedong_fit.json')
REGIONS = os.path.join(ROOT, 'src', 'data', 'korea', 'regions.json')
OUT_DIR = os.path.join(ROOT, 'src', 'assets', 'daedong')
OUT = os.path.join(ROOT, 'src', 'data', 'korea', 'daedong.json')
UA = {'User-Agent': 'japan-explorer-build/1.0 (github.com/Nickrockwall/japan-explorer)'}
SMALL = 'https://upload.wikimedia.org/wikipedia/commons/3/34/Daedongyeojido-small.png'
FULL = 'https://upload.wikimedia.org/wikipedia/commons/f/f0/Daedongyeojido-full.jpg'
MARGIN = 0.15   # 每边多留区域宽高的 15%
MIN_KM = 70     # 一块至少约 70 公里见方（首尔、大田这样的小区也能看出周边）
LONG = 1200     # 输出图长边像素
ISLAND = 0.02   # 陆块面积不到该区最大陆块 2% 的不参与算外框
FAR_KM = 60     # 离最大陆块中心超过 60 公里的岛也不算（仁川的白翎岛、延坪岛）
# 不走配准、按古图上的位置手工框出的（小图像素）：济州岛不参与拟合；罗先在古图东北角，图们江口一带
# 画得紧凑，多项式在边缘外推会落到海里，按古图上图们江口（庆兴一带）框出
MANUAL = {16: (350, 1870, 490, 1985), 18: (1050, 70, 1177, 250)}
# 小图像素归一化：X = (x - CX) / S，Y = (y - CY) / S
CX, CY, S = 588.0, 988.0, 600.0
LON0, LON1, LAT0, LAT1, RES = 124.0, 131.0, 33.0, 43.1, 0.01


def download(url, name):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, name)
    if not os.path.exists(path):
        print('下载', url)
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=600) as r, open(path, 'wb') as f:
            f.write(r.read())
    return path


def poly(p, X, Y):
    """三次多项式：前 6 项线性、再 6 项二次、再 8 项三次（经、纬各一半）"""
    lon = p[0] + p[1] * X + p[2] * Y + p[6] * X * X + p[7] * X * Y + p[8] * Y * Y
    lat = p[3] + p[4] * X + p[5] * Y + p[9] * X * X + p[10] * X * Y + p[11] * Y * Y
    if len(p) > 12:
        lon = lon + p[12] * X ** 3 + p[13] * X * X * Y + p[14] * X * Y * Y + p[15] * Y ** 3
        lat = lat + p[16] * X ** 3 + p[17] * X * X * Y + p[18] * X * Y * Y + p[19] * Y ** 3
    return lon, lat


def modern_land(geo):
    """今天的陆地，0.01° 栅格；济州不参与配准"""
    mw, mh = int((LON1 - LON0) / RES), int((LAT1 - LAT0) / RES)
    img = Image.new('L', (mw, mh), 0)
    d = ImageDraw.Draw(img)
    for f in geo['features']:
        g = f['geometry']
        for q in ([g['coordinates']] if g['type'] == 'Polygon' else g['coordinates']):
            for k, ring in enumerate(q):
                d.polygon([((x - LON0) / RES, (LAT1 - y) / RES) for x, y in ring], fill=255 if k == 0 else 0)
    m = np.asarray(img) > 0
    m[int((LAT1 - 33.7) / RES):, :] = False
    return mainland(m, 20000)


def mainland(mask, min_px):
    """只留大陆块：古图南海岸岛屿密集，岛群一并进来会把「陆地」往海里撑，对齐就整体偏南"""
    lab, n = ndimage.label(mask)
    if not n:
        return mask
    size = ndimage.sum(mask, lab, range(1, n + 1))
    keep = np.isin(lab, [i + 1 for i, s in enumerate(size) if s >= min_px])
    return ndimage.binary_fill_holes(keep)


def old_land(small):
    """小图上的陆地：深色笔画密的地方；透明处是拼图以外"""
    a = np.asarray(small)
    alpha = a[..., 3] > 0
    dark = (a[..., :3].astype(float).mean(axis=2) < 150) & alpha
    land = ndimage.uniform_filter(dark.astype(float), size=7) > 0.08
    land = ndimage.binary_opening(ndimage.binary_closing(land & alpha, iterations=2), iterations=2)
    land = mainland(land, 20000)
    use = alpha.copy()
    use[:260, 700:] = False       # 右上角的图例与地图目录
    use[1820:, :] = False         # 济州
    use[1150:1300, 900:] = False  # 郁陵岛
    return land, use


def fit(small, geo):
    land, use = old_land(small)
    modern = modern_land(geo)
    mh, mw = modern.shape
    ys, xs = np.nonzero(use[::4, ::4])
    ys, xs = ys * 4, xs * 4
    lab = land[ys, xs]
    X, Y = (xs - CX) / S, (ys - CY) / S

    def score(p):
        lon, lat = poly(p, X, Y)
        c = ((lon - LON0) / RES).astype(int)
        r = ((LAT1 - lat) / RES).astype(int)
        ok = (c >= 0) & (c < mw) & (r >= 0) & (r < mh)
        m = np.zeros_like(lab)
        m[ok] = modern[r[ok], c[ok]]
        return -(m & lab).sum() / (m | lab).sum()

    # 初值：济州中心（小图 830, 1864 ↔ 126.55°E, 33.38°N），约 147 像素 / 经度、178 像素 / 纬度
    p0 = [126.55 + (CX - 830) / 147, S / 147, 0, 33.38 + (1864 - CY) / 178, 0, -S / 178] + [0] * 6
    best = None
    for dx in (-0.6, 0, 0.6):
        for dy in (-0.8, 0, 0.8):
            q = list(p0)
            q[0] += dx
            q[3] += dy
            r = optimize.minimize(score, q[:6] + [0] * 6, method='Nelder-Mead', options={'maxiter': 4000, 'xatol': 1e-4, 'fatol': 1e-5})
            if best is None or r.fun < best.fun:
                best = r
    r = optimize.minimize(score, best.x, method='Nelder-Mead', options={'maxiter': 20000, 'xatol': 1e-5, 'fatol': 1e-6})
    r = optimize.minimize(score, r.x, method='Powell', options={'maxiter': 20000})
    r = optimize.minimize(score, list(r.x) + [0] * 8, method='Powell', options={'maxiter': 40000})
    r = optimize.minimize(score, r.x, method='Nelder-Mead', options={'maxiter': 40000, 'xatol': 1e-6, 'fatol': 1e-7})
    iou = -r.fun
    print(f'按面积配准 IoU {iou:.3f}')

    # 第二步：海岸线。古图陆地的边（去掉贴着拼图边界的）到今天海岸线的距离（0.01° ≈ 1 公里，超过 25 公里按 25 算）
    alpha = np.asarray(small)[..., 3] > 0
    coast = land & ~ndimage.binary_erosion(land) & use & ~ndimage.binary_dilation(~alpha, iterations=6)
    cy, cx = np.nonzero(coast)
    CXn, CYn = (cx - CX) / S, (cy - CY) / S
    dist = ndimage.distance_transform_edt(~(modern & ~ndimage.binary_erosion(modern)))

    def coast_km(p):
        lon, lat = poly(p, CXn, CYn)
        c = np.clip(((lon - LON0) / RES).astype(int), 0, mw - 1)
        r_ = np.clip(((LAT1 - lat) / RES).astype(int), 0, mh - 1)
        return np.minimum(dist[r_, c], 25.0).mean()
    both = lambda p: coast_km(p) + 30 * (1 + score(p))  # noqa: E731
    print(f'海岸平均距离 {coast_km(r.x):.2f} 公里')
    r = optimize.minimize(both, r.x, method='Powell', options={'maxiter': 60000, 'xtol': 1e-5, 'ftol': 1e-6})
    r = optimize.minimize(both, r.x, method='Nelder-Mead', options={'maxiter': 60000, 'xatol': 1e-6, 'fatol': 1e-6})
    print(f'细调后海岸平均距离 {coast_km(r.x):.2f} 公里，IoU {-score(r.x):.3f}')
    json.dump({'iou_area': round(iou, 4), 'iou': round(-score(r.x), 4), 'coast_km': round(float(coast_km(r.x)), 2),
               'p': [float(x) for x in r.x]}, open(FIT, 'w'), indent=1)


def inverse(p, alpha):
    """经纬度 → 小图像素：在拼图范围内取样正向映射，再用三次多项式最小二乘反过来拟合"""
    ys, xs = np.nonzero(alpha[::6, ::6])
    ys, xs = ys * 6.0, xs * 6.0
    lon, lat = poly(p, (xs - CX) / S, (ys - CY) / S)
    u, v = lon - 127.5, lat - 38.0
    A = np.stack([np.ones_like(u), u, v, u * u, u * v, v * v, u ** 3, u * u * v, u * v * v, v ** 3], axis=1)
    cx, *_ = np.linalg.lstsq(A, xs, rcond=None)
    cy, *_ = np.linalg.lstsq(A, ys, rcond=None)
    rms = float(np.sqrt(np.mean((A @ cx - xs) ** 2 + (A @ cy - ys) ** 2)))
    print(f'反算误差 {rms:.2f} 像素（小图）')

    def to_px(lon, lat):
        u, v = np.asarray(lon) - 127.5, np.asarray(lat) - 38.0
        B = np.stack([np.ones_like(u), u, v, u * u, u * v, v * v, u ** 3, u * u * v, u * v * v, v ** 3], axis=-1)
        return B @ cx, B @ cy
    return to_px


def main():
    small = Image.open(download(SMALL, 'small.png'))
    geo = json.load(open(REGIONS, encoding='utf-8'))
    if '--fit' in sys.argv or not os.path.exists(FIT):
        fit(small, geo)
    p = json.load(open(FIT))['p']
    alpha = np.asarray(small)[..., 3] > 0
    to_px = inverse(p, alpha)
    km_px = None

    Image.MAX_IMAGE_PIXELS = None
    full = Image.open(download(FULL, 'full.jpg'))
    fw, fh = full.size
    full.draft('RGB', (fw // 2, fh // 2))
    full = full.convert('RGB')
    sx, sy = full.width / small.width, full.height / small.height
    print(f'原图 {fw}×{fh}，解码 {full.width}×{full.height}，小图 → 大图 ×{sx:.3f} / ×{sy:.3f}')

    os.makedirs(OUT_DIR, exist_ok=True)
    out = {}
    for f in geo['features']:
        pr = f['properties']
        if pr['id'] in MANUAL:
            x0, y0, x1, y1 = MANUAL[pr['id']]
        else:
            g = f['geometry']
            parts = [np.array(q[0]) for q in ([g['coordinates']] if g['type'] == 'Polygon' else g['coordinates'])]
            area = [abs(np.dot(q[:, 0], np.roll(q[:, 1], 1)) - np.dot(q[:, 1], np.roll(q[:, 0], 1))) / 2 for q in parts]
            big = parts[int(np.argmax(area))].mean(axis=0)
            near = lambda q: np.hypot((q[:, 0].mean() - big[0]) * 111.32 * np.cos(np.radians(big[1])), (q[:, 1].mean() - big[1]) * 110.57) <= FAR_KM  # noqa: E731
            pts = np.concatenate([q for q, a in zip(parts, area) if a >= ISLAND * max(area) and near(q)])
            px, py = to_px(pts[:, 0], pts[:, 1])
            x0, x1, y0, y1 = px.min(), px.max(), py.min(), py.max()
            # 最小尺寸：按该区中心附近 1 公里约合多少像素换算
            cl, ct = pts[:, 0].mean(), pts[:, 1].mean()
            ax, ay = to_px([cl, cl + 1 / (111.32 * np.cos(np.radians(ct)))], [ct, ct + 1 / 110.57])
            km_px = (abs(ax[1] - ax[0]) + abs(ay[1] - ay[0])) / 2
            w, h = x1 - x0, y1 - y0
            x0, x1, y0, y1 = x0 - w * MARGIN, x1 + w * MARGIN, y0 - h * MARGIN, y1 + h * MARGIN
            need = MIN_KM * km_px
            if x1 - x0 < need:
                c = (x0 + x1) / 2
                x0, x1 = c - need / 2, c + need / 2
            if y1 - y0 < need:
                c = (y0 + y1) / 2
                y0, y1 = c - need / 2, c + need / 2
        box = [max(0, int(x0 * sx)), max(0, int(y0 * sy)), min(full.width, int(x1 * sx)), min(full.height, int(y1 * sy))]
        crop = full.crop(box)
        k = min(1.0, LONG / max(crop.size))
        if k < 1:
            crop = crop.resize((round(crop.width * k), round(crop.height * k)), Image.LANCZOS)
        crop.save(os.path.join(OUT_DIR, f'{pr["id"]:02d}.jpg'), quality=78, optimize=True, progressive=True)
        out[str(pr['id'])] = [crop.width, crop.height]
        print(f'{pr["id"]:2d} {pr["zh"]}: {crop.width}×{crop.height}')
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f)
        f.write('\n')
    print('输出', OUT)


if __name__ == '__main__':
    main()
