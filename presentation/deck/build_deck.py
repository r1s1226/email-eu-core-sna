"""Build the 8+3 slide deck (airmail / letter look, matching the results website) from the pilot data.

Usage: python build_deck.py <site_data.json> <removal_curves.npz> <deck root> <preview.html>
Writes <deck root>/project/slides/<id>.html and <deck root>/project/deck.json, plus a local preview page.
"""
import json
import sys
from pathlib import Path

import numpy as np

site_path, npz_path, root, preview_path = map(Path, sys.argv[1:5])
D = json.loads(site_path.read_text(encoding="utf-8"))
Z = np.load(npz_path)
NET = "/_blob/b9faf58bc70a3e455b36f3a6ecf325ab"  # cover network drawing (asset in the deck)

# palette: the website's tokens
PAPER, SURFACE, INK, INK2, MUTED, RULE = "#f3f5f8", "#fcfdfe", "#14213d", "#3a4458", "#5c6577", "#d9dee6"
ACCENT, NAVY, ON_DARK, ON_DARK_MUTED, ACCENT_DARK = "#b4461a", "#14213d", "#e8ecf4", "#9aa5ba", "#f08a54"
BTW, DEG, RAND, AQUA, BAND, GONE = "#eb6834", "#2a78d6", "#8a909b", "#1baf7a", "#dfe2e8", "#c3c8d2"
STRIPE_R, STRIPE_B = "#c8402f", "#2a5bd7"
DISPLAY, BODY, MONO = "'Hahmlet', serif", "'IBM Plex Sans KR', sans-serif", "'IBM Plex Mono', monospace"
MAIN_TOTAL = 8


# ---------- shared pieces ----------
def stripe(width, height, vertical=False, period=48, w=16):
    """Airmail stripe (red/blue parallelograms) as an svg; vertical draws it down a side edge."""
    h = width if vertical else height
    length = height if vertical else width
    groups = {STRIPE_R: [], STRIPE_B: []}
    x = -h - period
    while x < length + h:
        for off, col in ((0, STRIPE_R), (period // 2, STRIPE_B)):
            x0 = x + off
            pts = [(x0, h), (x0 + h, 0), (x0 + h + w, 0), (x0 + w, h)]
            if vertical:
                pts = [(b, a) for a, b in pts]
            groups[col].append("<polygon points=\"" + " ".join(f"{a},{b}" for a, b in pts) + "\"/>")
        x += period
    body = "".join(f'<g fill="{c}">{"".join(p)}</g>' for c, p in groups.items())
    return body


def svg(label, w, h, inner, style):
    return (f'<svg aria-label="{label}" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'xmlns="http://www.w3.org/2000/svg" style="{style}">{inner}</svg>')


def top_stripe():
    return svg("", 1920, 10, stripe(1920, 10), "position:absolute;left:0px;top:0px;width:1920px;height:10px")


def envelope():
    t = 18
    return "\n".join([
        svg("", 1920, t, stripe(1920, t), f"position:absolute;left:0px;top:0px;width:1920px;height:{t}px"),
        svg("", 1920, t, stripe(1920, t), f"position:absolute;left:0px;top:{1080 - t}px;width:1920px;height:{t}px"),
        svg("", t, 1080, stripe(t, 1080, vertical=True), f"position:absolute;left:0px;top:0px;width:{t}px;height:1080px"),
        svg("", t, 1080, stripe(t, 1080, vertical=True), f"position:absolute;left:{1920 - t}px;top:0px;width:{t}px;height:1080px"),
    ])


def tag(text, color=ACCENT):
    face = f"font-family:{BODY};font-size:24px;font-weight:600;letter-spacing:1px" if text.startswith("부록") else \
        f"font-family:{MONO};font-size:24px;font-weight:500;letter-spacing:2px"
    return (f'<p style="{face};line-height:1.3;'
            f'color:{color};border:2px solid {color};border-radius:6px;padding:2px 12px">{text}</p>')


def header(tg, eyebrow, title):
    return f'''<div style="display:flex;flex-direction:column;gap:20px">
<div style="display:flex;align-items:center;gap:16px">
{tag(tg)}
<p style="font-size:24px;font-weight:600;letter-spacing:1px;color:{MUTED}">{eyebrow}</p>
</div>
<h2 style="font-family:{DISPLAY};font-size:60px;font-weight:700;line-height:1.15;letter-spacing:-1px;color:{INK}">{title}</h2>
</div>'''


def footer(left, right):
    return (f'<p style="position:absolute;left:128px;bottom:64px;width:1300px;font-size:24px;color:{MUTED}">{left}</p>\n'
            f'<p style="position:absolute;right:128px;bottom:64px;width:240px;font-family:{BODY if right.startswith("부록") else MONO};font-size:24px;'
            f'letter-spacing:1px;color:{MUTED};text-align:right">{right}</p>')


def stamp(line1, line2):
    """A rubber-stamp verdict pinned at the top right, like a postmark on the letter."""
    return f'''<div style="position:absolute;right:136px;top:120px;width:280px;display:flex;flex-direction:column;align-items:center;gap:2px;border:4px double {ACCENT};border-radius:14px;padding:12px 16px;transform:rotate(-6deg)">
<p style="font-size:24px;font-weight:600;letter-spacing:2px;color:{ACCENT}">{line1}</p>
<p style="font-family:{DISPLAY};font-size:40px;font-weight:700;line-height:1.15;color:{ACCENT}">{line2}</p>
</div>'''


def light(sid, inner, notes, extra=""):
    return (f'<section id="{sid}"{extra} style="background:{PAPER};color:{INK2};font-family:{BODY};'
            f'padding:128px 128px 160px;display:flex;flex-direction:column;gap:48px">\n'
            f'{top_stripe()}\n{inner}\n<aside>{notes}</aside>\n</section>\n')


def page(n):
    return f"{n:02d} / {MAIN_TOTAL:02d}"


def hbar(label, value, text, width, color, label_w, bold=False):
    weight = "font-weight:600;" if bold else ""
    return (f'<div style="display:flex;align-items:center;gap:16px">'
            f'<p style="width:{label_w}px;font-size:24px;{weight}text-align:right;color:{INK if bold else INK2}">{label}</p>'
            f'<div style="width:{width}px;height:36px;background:{color};border-radius:0px 6px 6px 0px"></div>'
            f'<p style="font-size:24px;font-weight:600;white-space:nowrap;color:{INK}">{text}</p></div>')


slides = {}

# ---------- 1 cover ----------
slides["cover"] = f'''<section id="cover" data-transition="fade" style="background:{NAVY};color:{ON_DARK};font-family:{BODY};padding:128px;display:flex;flex-direction:column;justify-content:space-between">
<img src="{NET}" alt="" style="position:absolute;left:1010px;top:110px;width:860px;height:860px;object-fit:contain">
{envelope()}
<p style="font-size:24px;font-weight:600;letter-spacing:3px;color:{ACCENT_DARK}">사회 네트워크 분석 · 기말 프로젝트 발표</p>
<div style="display:flex;flex-direction:column;gap:32px">
<h1 style="font-family:{DISPLAY};font-size:88px;font-weight:700;line-height:1.15;letter-spacing:-2px;color:{ON_DARK};width:1100px">조직 이메일 네트워크의<br>핵심 인물 탐지와 부서 예측</h1>
<p style="font-size:30px;line-height:1.45;color:{ON_DARK_MUTED};width:900px">SNAP email-Eu-core 데이터로 본 중심성, 동종선호, 그래프 학습</p>
</div>
<div style="display:flex;flex-direction:column;gap:18px">
<div style="display:flex;align-items:baseline;gap:24px"><p style="width:110px;font-family:{MONO};font-size:24px;letter-spacing:2px;color:{ON_DARK_MUTED}">FROM</p>
<div style="display:grid;grid-template-columns:380px 380px;gap:12px">
{"".join(f'<div style="display:flex;align-items:baseline;gap:16px"><p style="font-size:30px;color:{ON_DARK}">{n}</p><p style="font-family:{MONO};font-size:24px;letter-spacing:1px;color:{ON_DARK_MUTED}">{sid}</p></div>' for n, sid in [("당택군", "2022047710"), ("란가성", "2023093418"), ("왕철한", "2023080719"), ("유열", "2021068022")])}
</div>
</div>
<div style="display:flex;align-items:baseline;gap:24px"><p style="width:110px;font-family:{MONO};font-size:24px;letter-spacing:2px;color:{ON_DARK_MUTED}">DATE</p><p style="font-size:30px;color:{ON_DARK}">2026. 10. 26.</p></div>
</div>
<aside>안녕하세요. 저희 팀을 대표해 발표하겠습니다. 저희는 유럽의 한 연구기관 구성원들이 주고받은 이메일 네트워크로, 조직의 핵심 인물과 부서 구조를 분석했습니다.</aside>
</section>
'''

# ---------- 2 data and hypotheses ----------
def stat(num, unit, cap):
    return (f'<div style="display:flex;flex-direction:column;gap:6px;border-top:3px solid {INK};padding:20px 0px 0px 0px">'
            f'<p style="font-family:{DISPLAY};font-size:88px;font-weight:700;line-height:1.1;color:{INK}">{num}<span style="color:{MUTED}">{unit}</span></p>'
            f'<p style="font-size:24px;color:{MUTED}">{cap}</p></div>')


def hypo(tg, title, text):
    return (f'<div style="flex:1;display:flex;flex-direction:column;gap:16px;background:{SURFACE};border:1px solid {RULE};border-radius:16px;padding:36px 40px">'
            f'<div style="display:flex;align-items:center;gap:16px">{tag(tg)}'
            f'<p style="font-size:30px;font-weight:700;color:{INK}">{title}</p></div>'
            f'<p style="font-size:30px;line-height:1.45;color:{INK2}">{text}</p></div>')


s = D["structure"]
slides["data-hypotheses"] = light("data-hypotheses", f'''{header("DATA", "데이터와 가설", "email-Eu-core와 세 가지 가설")}
<div style="display:grid;grid-template-columns:1fr 1.25fr 0.75fr 1fr;gap:40px">
{stat(f"{s['nodes']:,}", "명", "구성원 (노드)")}
{stat(f"{s['directed_edge_lines']:,}", "개", "이메일 관계 (방향 간선)")}
{stat(s['departments'], "개", "부서 라벨")}
{stat(s['lcc_nodes'], "명", "분석 대상 (최대 연결 요소, LCC)")}
</div>
<div style="flex:1"></div>
<div style="display:flex;flex-direction:column;gap:20px">
<p style="font-size:24px;font-weight:600;letter-spacing:1px;color:{MUTED}">과제 수행 계획서의 세 가지 가설</p>
<div style="display:flex;gap:32px">
{hypo("H1", "연결자와 분절", "betweenness가 높은 사람은 부서를 잇는 연결자이고, 이들을 빼면 네트워크가 쪼개진다.")}
{hypo("H2", "동종선호와 예측", "같은 부서끼리 밀집해 있어, 연결 구조만으로 부서를 맞힐 수 있다.")}
{hypo("H3", "모델 비교", "node2vec이 DeepWalk보다, GCN이 얕은 임베딩보다 부서를 더 잘 맞힌다.")}
</div>
</div>
{footer(f"SNAP email-Eu-core · 자기 루프 {s['self_loops']}개 제거 후 무방향 그래프로 변환", page(2))}''',
    "데이터는 SNAP의 email-Eu-core입니다. 1,005명이 주고받은 이메일 관계 25,571개와 42개 부서 라벨이 있습니다. "
    "자기 루프를 지우고 무방향 그래프로 바꾼 뒤, 가장 큰 연결 요소인 986명을 분석했습니다. "
    "저희가 세운 가설은 세 가지입니다. 첫째, betweenness가 높은 사람은 부서를 잇는 연결자이고, 이들을 빼면 네트워크가 쪼개진다. "
    "둘째, 같은 부서끼리 밀집해 있어 연결 구조만으로 부서를 맞힐 수 있다. "
    "셋째, node2vec이 DeepWalk보다, GCN이 얕은 임베딩보다 부서를 더 잘 맞힌다. "
    "결론부터 말씀드리면, 어느 가설도 처음 형태 그대로는 지지되지 않았습니다.")

# ---------- 3 H1 brokers ----------
c = D["centrality"]
cross = [c["cross_dept_frac_mean_top10_betweenness"], c["cross_dept_frac_mean_top10_degree"], c["cross_dept_frac_mean_all"]]
ndep = [c["neighbour_depts_mean_top10_betweenness"], c["neighbour_depts_mean_top10_degree"], c["neighbour_depts_mean_all"]]
BAR_MAX, LBL = 640, 290
rows = [("betweenness 상위 10명", BTW), ("degree 상위 10명", DEG), ("전체 평균", RAND)]
block1 = "\n".join(hbar(l, v, f"{v * 100:.0f}%", round(v * BAR_MAX), col, LBL) for (l, col), v in zip(rows, cross))
block2 = "\n".join(hbar(l, v, f"{v:.1f}개", round(v / s["departments"] * BAR_MAX), col, LBL) for (l, col), v in zip(rows, ndep))
in_36 = sum(1 for r in c["top10_betweenness"] if r["dept"] == 36)


def fact(num, cap):
    return (f'<div style="display:flex;flex-direction:column;gap:4px;border-top:2px solid {INK};padding:16px 0px 0px 0px">'
            f'<p style="font-family:{DISPLAY};font-size:60px;font-weight:700;line-height:1.15;color:{INK}">{num}</p>'
            f'<p style="font-size:24px;color:{MUTED}">{cap}</p></div>')


slides["h1-brokers"] = light("h1-brokers", f'''{header("H1", "가설 1 · 핵심 인물", "부서를 잇는 사람은 누구인가")}
<div style="display:flex;gap:64px">
<div style="flex:1;display:flex;flex-direction:column;gap:40px">
<div style="display:flex;flex-direction:column;gap:12px">
<h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{INK}">이웃 중 다른 부서 사람의 비율</h3>
{block1}
</div>
<div style="display:flex;flex-direction:column;gap:12px">
<h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{INK}">이웃이 속한 부서 수 (전체 42개 중)</h3>
{block2}
</div>
</div>
<div style="width:500px;display:flex;flex-direction:column;gap:24px">
{fact(f"{c['spearman_betweenness_degree']:.2f}", "betweenness와 degree의 순위 상관")}
{fact(f"{c['overlap_top10_betweenness_degree']} / 10", "두 지표 상위 10명에 모두 든 사람")}
{fact(f"{in_36} / 10", "betweenness 상위 10명 중 부서 36 소속")}
</div>
</div>
<div style="flex:1"></div>
<p style="font-size:30px;line-height:1.4;background:{NAVY};color:{ON_DARK};border-radius:16px;padding:24px 40px">연결자인 것은 맞지만, betweenness 상위자만의 특징이 아니라 <b>허브에 공통된 특징</b>이다.</p>
{footer("무방향 그래프 기준 · 순위 상관은 Spearman", page(3))}''',
    "먼저 가설 1입니다. betweenness 상위 10명은 이웃의 93%가 다른 부서 사람이고, 평균 33.6개 부서와 이어져 있어 연결자인 것은 맞습니다. "
    "예를 들어 betweenness 1위인 160번 구성원은 345명과 연락하고, 36개 부서와 이어져 있습니다. "
    "그런데 연락 상대가 많은 degree 상위 10명도 93%로 똑같고, 두 명단 중 7명이 겹칩니다. "
    "오른쪽의 0.93은 betweenness와 degree 순위의 상관계수로, 두 순위가 거의 같다는 뜻입니다. "
    "즉 연결자 역할은 betweenness가 높은 사람만의 특징이 아니라, 허브들에게 공통된 특징입니다. "
    "참고로 betweenness 상위 10명 중 6명은 같은 36번 부서 소속이어서, 중개 역할이 한 부서에 몰려 있습니다.")

# ---------- 4 H1 removal ----------
N = s["lcc_nodes"]
PW, PH, PL, PT = 980, 500, 96, 17   # plot size and its offset inside the chart host


def px(q):
    return q / 0.5 * PW


def py(f):
    return (1 - f) * PH


def line(xs, ys):
    return " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in zip(xs, ys) if x <= 0.5 + 1e-9)


k = Z["k"]
q = k / N
rnd = Z["random"]
band = (" ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in zip(q, rnd.max(0)) if x <= 0.5)
        + " " + " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in reversed(list(zip(q, rnd.min(0)))) if x <= 0.5))
grid = "".join(f'<line x1="0" y1="{py(f):.1f}" x2="{PW}" y2="{py(f):.1f}" stroke="{BAND}" stroke-width="2"/>' for f in (0.25, 0.75, 1.0))
half = {"betweenness": D["removal"]["betweenness (adaptive, every 10)"]["q_when_lcc_below_half"],
        "degree": D["removal"]["degree (adaptive, every 1)"]["q_when_lcc_below_half"],
        "random": D["removal"]["random (mean of 20)"]["q_when_lcc_below_half"]}
marks = "".join(f'<circle cx="{px(v):.1f}" cy="{py(0.5):.1f}" r="10" fill="{col}" stroke="{PAPER}" stroke-width="3"/>'
                for v, col in ((half["random"], RAND), (half["degree"], DEG), (half["betweenness"], BTW)))
plot = (grid
        + f'<line x1="0" y1="{py(0.5):.1f}" x2="{PW}" y2="{py(0.5):.1f}" stroke="{MUTED}" stroke-width="2" stroke-dasharray="10 8"/>'
        + f'<polygon points="{band}" fill="{BAND}" opacity="0.7"/>'
        + f'<polyline points="{line([0, 0.5], [1, 0.5])}" fill="none" stroke="#a9adb6" stroke-width="3" stroke-dasharray="3 7" stroke-linecap="round"/>'
        + f'<polyline points="{line(q, rnd.mean(0))}" fill="none" stroke="{RAND}" stroke-width="4" stroke-linejoin="round"/>'
        + f'<polyline points="{line(q, Z["degree_adaptive"])}" fill="none" stroke="{DEG}" stroke-width="4" stroke-linejoin="round"/>'
        + f'<polyline points="{line(Z["betweenness_adaptive_k"] / N, Z["betweenness_adaptive"])}" fill="none" stroke="{BTW}" stroke-width="5" stroke-linejoin="round"/>'
        + f'<line x1="0" y1="{PH}" x2="{PW}" y2="{PH}" stroke="{MUTED}" stroke-width="2"/>'
        + marks)
ticks = "\n".join(
    [f'<p style="position:absolute;left:0px;top:{PT + py(f) - 17:.0f}px;width:80px;font-family:{MONO};font-size:24px;color:{MUTED};text-align:right">{int(f * 100)}%</p>'
     for f in (0, 0.25, 0.5, 0.75, 1.0)]
    + [f'<p style="position:absolute;left:{PL + px(x) - 50:.0f}px;top:{PT + PH + 12}px;width:100px;font-family:{MONO};font-size:24px;color:{MUTED};text-align:center">{int(x * 100)}%</p>'
       for x in (0, 0.1, 0.2, 0.3, 0.4, 0.5)])
bq, bl = Z["betweenness_adaptive_k"][-1] / N, Z["betweenness_adaptive"][-1]
chart = f'''<div style="position:relative;width:1100px;height:610px">
{svg("제거한 노드 비율에 따른 최대 연결 요소 크기. betweenness 순 30.4%, degree 순 33.0%, 무작위 46.9%에서 절반 아래로 떨어진다.", PW, PH, plot, f"position:absolute;left:{PL}px;top:{PT}px;width:{PW}px;height:{PH}px")}
{ticks}
<p style="position:absolute;left:{PL}px;top:{PT + PH + 52}px;width:{PW}px;font-size:24px;color:{MUTED};text-align:center">제거한 구성원 비율 (가로) · 최대 연결 요소 크기, 처음 986명 = 100% (세로)</p>
<p style="position:absolute;left:{PL + px(bq) - 100:.0f}px;top:{PT + py(bl) + 16:.0f}px;width:200px;font-size:24px;font-weight:600;color:{ACCENT};text-align:center">{Z["betweenness_adaptive_k"][-1]}명까지 계산</p>
</div>'''


def legend(color, text, dotted=False):
    sw = (f'<div style="width:40px;border-top:4px dotted #a9adb6"></div>' if dotted
          else f'<div style="width:40px;height:6px;background:{color};border-radius:3px"></div>')
    return f'<div style="display:flex;align-items:center;gap:14px">{sw}<p style="font-size:24px;color:{INK2}">{text}</p></div>'


def halfrow(color, value, name):
    return (f'<div style="display:flex;align-items:center;gap:18px">'
            f'<div style="width:22px;height:22px;background:{color};border-radius:50%"></div>'
            f'<p style="width:236px;font-family:{DISPLAY};font-size:60px;font-weight:700;line-height:1.15;color:{INK}">{value * 100:.1f}%</p>'
            f'<p style="font-size:24px;color:{MUTED}">{name}</p></div>')


slides["h1-removal"] = light("h1-removal", f'''{header("H1", "가설 1 · 제거 실험", "핵심 인물을 빼면 소통망이 끊길까")}
<div style="display:flex;gap:56px">
{chart}
<div style="flex:1;display:flex;flex-direction:column;gap:28px">
<div style="display:flex;flex-direction:column;gap:12px">
{legend(BTW, "betweenness 순으로 제거")}
{legend(DEG, "degree 순으로 제거")}
{legend(RAND, "무작위 제거 (20회 평균)")}
{legend(None, "제거한 만큼만 감소", dotted=True)}
</div>
<div style="display:flex;flex-direction:column;gap:12px;border-top:2px solid {INK};padding:20px 0px 0px 0px">
<p style="font-size:24px;font-weight:600;color:{MUTED}">절반 아래로 떨어질 때까지 제거한 비율</p>
{halfrow(BTW, half["betweenness"], "betweenness")}
{halfrow(DEG, half["degree"], "degree")}
{halfrow(RAND, half["random"], "무작위")}
</div>
<p style="font-size:24px;line-height:1.4;color:{MUTED}">두 번째로 큰 조각은 측정 범위 내내 8% 미만</p>
</div>
</div>
{stamp("가설 1", "수정")}
{footer("LCC 986명 기준 · 순위는 제거 중 재계산 (한 번만 계산하면 31.4% / 33.9%)", page(4))}''',
    "다음은 핵심 인물을 차례로 빼면서 가장 큰 연결 요소가 얼마나 줄어드는지 본 실험입니다. "
    "주황색은 betweenness, 파란색은 degree 순서로 뺀 결과이고, 회색은 무작위 제거입니다. "
    "주황 선은 계산 시간이 오래 걸려서 400명, 약 40%까지만 계산했습니다. "
    "무작위로는 46.9%를 빼야 절반 아래로 떨어지니, 표적 제거가 더 빠릅니다. "
    "하지만 표적 제거로도 절반 아래로 떨어뜨리려면 betweenness 순으로 30.4%, degree 순으로 33.0%를 빼야 합니다. "
    "두 번째로 큰 연결 요소도 8%를 넘지 않아, 네트워크는 쪼개지기보다 조금씩 깎여 나갑니다. "
    "그래서 가설 1은 ‘표적 제거가 더 효과적이지만 핵심 구조는 견고하다’로 수정합니다.")

# ---------- 5 H2 ----------
TW, TH, TPAD = 600, 500, 26
xy = np.array([[n[5], n[6]] for n in D["nodes"]], dtype=float)
dept = np.array([n[2] for n in D["nodes"]])
lo, hi = xy.min(0), xy.max(0)
scale = min((TW - 2 * TPAD) / (hi[0] - lo[0]), (TH - 2 * TPAD) / (hi[1] - lo[1]))
off = np.array([(TW - (hi[0] - lo[0]) * scale) / 2, (TH - (hi[1] - lo[1]) * scale) / 2])
pt = (xy - lo) * scale + off
pt[:, 1] = TH - pt[:, 1]
top3 = [(4, DEG), (14, BTW), (1, AQUA)]


def dots(mask, color, width):
    d = "".join(f"M{x:.0f} {y:.0f}h0" for x, y in pt[mask])
    return f'<path d="{d}" stroke="{color}" stroke-width="{width}" stroke-linecap="round" fill="none"/>'


others = ~np.isin(dept, [d for d, _ in top3])
tsne = dots(others, GONE, 9) + "".join(dots(dept == d, SURFACE, 14) + dots(dept == d, col, 10) for d, col in top3)
sizes = D["dept_sizes"]
tsne_legend = "\n".join(
    f'<div style="display:flex;align-items:center;gap:12px"><div style="width:20px;height:20px;background:{col};border-radius:50%"></div>'
    f'<p style="font-size:24px;color:{INK2}">{name}</p></div>'
    for col, name in [(DEG, f"부서 4 · {sizes['4']}명"), (BTW, f"부서 14 · {sizes['14']}명"),
                      (AQUA, f"부서 1 · {sizes['1']}명"), (GONE, "그 외 부서")])
h = D["homophily"]
cl = D["classification"]
dw = cl["n2v"]["deepwalk"]
maj = cl["seed0"]["majority"]["acc"]


def bignum(num, cap, color=INK):
    return (f'<div style="display:flex;flex-direction:column;gap:4px">'
            f'<p style="font-family:{DISPLAY};font-size:88px;font-weight:700;line-height:1.1;color:{color}">{num}</p>'
            f'<p style="font-size:24px;color:{MUTED}">{cap}</p></div>')


slides["h2"] = light("h2", f'''{header("H2", "가설 2 · 동종선호와 부서 예측", "연결 구조만으로 부서를 맞힐 수 있을까")}
<div style="display:flex;gap:64px">
<div style="width:600px;display:flex;flex-direction:column;gap:16px">
<div style="position:relative;width:600px;height:500px;background:{SURFACE};border:1px solid {RULE};border-radius:16px">
{svg("DeepWalk 임베딩의 t-SNE. 가장 큰 세 부서(부서 4, 14, 1)가 각각 따로 모여 있다.", TW, TH, tsne, f"position:absolute;left:0px;top:0px;width:{TW}px;height:{TH}px")}
</div>
<div style="display:grid;grid-template-columns:repeat(2, 1fr);gap:8px">
{tsne_legend}
</div>
</div>
<div style="flex:1;display:flex;flex-direction:column;gap:32px">
<div style="display:flex;flex-direction:column;gap:12px">
<p style="font-size:24px;font-weight:600;color:{MUTED}">같은 부서끼리 이어진 간선의 비율</p>
<div style="display:flex;align-items:baseline;gap:32px">
<p style="font-family:{DISPLAY};font-size:88px;font-weight:700;line-height:1.1;color:{INK}">{h['edge_homophily'] * 100:.1f}%</p>
<p style="font-size:30px;color:{MUTED}">라벨을 무작위로 섞으면 {h['shuffled_label_null_mean'] * 100:.1f}%</p>
</div>
<p style="font-size:30px;line-height:1.45;color:{INK2}">하지만 이웃 중 같은 부서는 평균 {h['node_homophily_mean'] * 100:.0f}% → 유의하지만 약한 동종선호</p>
</div>
<div style="display:flex;flex-direction:column;gap:12px;border-top:2px solid {INK};padding:24px 0px 0px 0px">
<p style="font-size:24px;font-weight:600;color:{MUTED}">35개 부서 분류 · DeepWalk + 로지스틱 회귀</p>
<div style="display:flex;gap:72px">
{bignum(f"{dw['acc']:.2f}", "정확도")}
{bignum(f"{dw['macro_f1']:.2f}", "Macro-F1")}
{bignum(f"{maj:.2f}", "다수 클래스 기준선 (정확도)", MUTED)}
</div>
</div>
</div>
</div>
{stamp("가설 2", "부분 지지")}
{footer("35개 부서(968명) · 층화 5-fold · 라벨 80%로 학습 · 시드 3개 평균 · t-SNE는 LCC 986명", page(5))}''',
    "다음은 가설 2입니다. 같은 부서끼리 이어진 간선은 33.6%로, 부서 라벨을 무작위로 섞었을 때의 4.7%보다 훨씬 많습니다. "
    "하지만 한 사람의 이웃 중 같은 부서는 평균 46%로 절반이 안 됩니다. 그래서 동종선호는 유의하지만, 밀집이라고 하기에는 약합니다. "
    "그래도 연결 구조만으로 부서를 꽤 잘 맞힙니다. 왼쪽 t-SNE에서 큰 부서들이 대체로 각자 모여 있습니다. "
    "DeepWalk 임베딩에 로지스틱 회귀를 쓰고 라벨의 80%로 학습했더니, 5명 미만인 작은 부서 7개를 뺀 35개 부서 분류에서 정확도는 0.76, Macro-F1은 0.65였습니다. "
    "다수 클래스 기준선은 0.11입니다. 그래서 가설 2는 부분 지지입니다.")

# ---------- 6 H3 ----------
n2v = cl["n2v"]
pts3 = [("DeepWalk", n2v["deepwalk"]), ("node2vec q=0.5", n2v["node2vec_p1_q0.5"]), ("node2vec q=2", n2v["node2vec_p1_q2"])]
DW_, DH_, DL_ = 330, 230, 230  # dot plot: track width, height, left label column
lo_f, hi_f = 0.60, 0.68


def fx(v):  # x inside the dot-plot svg, which has 10px of room on each side of the track
    return (v - lo_f) / (hi_f - lo_f) * DW_ + 10


dot_rows = [40 + i * 70 for i in range(3)]
dp = "".join(f'<line x1="{fx(t):.1f}" y1="0" x2="{fx(t):.1f}" y2="{DH_ - 30}" stroke="{BAND}" stroke-width="2"/>' for t in (0.60, 0.64, 0.68))
for (name, r), y in zip(pts3, dot_rows):
    m, sd = r["macro_f1"], r["macro_f1_seed_std"]
    col = DEG
    dp += (f'<line x1="{fx(m - sd):.1f}" y1="{y}" x2="{fx(m + sd):.1f}" y2="{y}" stroke="{col}" stroke-width="4" stroke-linecap="round"/>'
           f'<circle cx="{fx(m):.1f}" cy="{y}" r="11" fill="{col}" stroke="{SURFACE}" stroke-width="3"/>')
dot_labels = "\n".join(
    f'<p style="position:absolute;left:0px;top:{y - 17}px;width:{DL_ - 20}px;font-size:24px;text-align:right;color:{INK2}">{name}</p>'
    for (name, _), y in zip(pts3, dot_rows))
dot_ticks = "\n".join(
    f'<p style="position:absolute;left:{DL_ - 10 + fx(t) - 45:.0f}px;top:{DH_ - 22}px;width:90px;font-family:{MONO};font-size:24px;text-align:center;color:{MUTED}">{t:.2f}</p>'
    for t in (0.60, 0.64, 0.68))
dotplot = f'''<div style="position:relative;width:{DL_ + DW_ + 20}px;height:{DH_ + 20}px">
{svg("node2vec과 DeepWalk의 Macro-F1. 세 방법의 평균 ± 표준편차가 서로 겹친다.", DW_ + 20, DH_ - 20, dp, f"position:absolute;left:{DL_ - 10}px;top:0px;width:{DW_ + 20}px;height:{DH_ - 20}px")}
{dot_labels}
{dot_ticks}
</div>'''
sd0 = cl["seed0"]
# verified display values (same as the website): plain float formatting turns the stored 0.7665 into 0.766
SHOWN = {"majority": ("0.111", "0.006"), "vote": ("0.719", "0.554"), "label_spreading": ("0.767", "0.612"),
         "deepwalk_logreg": ("0.749", "0.634"), "mlp": ("0.767", "0.635"), "gcn": ("0.787", "0.668"), "gcn_identity": ("0.740", "0.516")}
for key, (a_, f_) in SHOWN.items():  # each shown value must match the stored one to within rounding
    assert abs(float(a_) - sd0[key]["acc"]) <= 0.0006 and abs(float(f_) - sd0[key]["macro_f1"]) <= 0.0006, key
KEYS = {"이웃 투표": "vote", "label spreading": "label_spreading", "DeepWalk + 로지스틱 회귀": "deepwalk_logreg",
        "MLP (메시지 전달 없음)": "mlp", "GCN": "gcn"}
bars = [("이웃 투표", sd0["vote"]["macro_f1"], RAND), ("label spreading", sd0["label_spreading"]["macro_f1"], RAND),
        ("DeepWalk + 로지스틱 회귀", sd0["deepwalk_logreg"]["macro_f1"], DEG), ("MLP (메시지 전달 없음)", sd0["mlp"]["macro_f1"], DEG),
        ("GCN", sd0["gcn"]["macro_f1"], BTW)]
H3_MAX = 470  # px for Macro-F1 0.7
bar_rows = "\n".join(hbar(n, v, SHOWN[KEYS[n]][1], round(v / 0.7 * H3_MAX), col, 320, bold=(n == "GCN")) for n, v, col in bars)
pair = cl["paired"]["deepwalk: gcn - mlp"]
card = f"display:flex;flex-direction:column;gap:16px;background:{SURFACE};border:1px solid {RULE};border-radius:16px;padding:36px 40px"
slides["h3"] = light("h3", f'''{header("H3", "가설 3 · 모델 비교", "node2vec과 GCN은 더 나을까")}
<div style="display:flex;gap:40px">
<div style="width:660px;{card}">
<h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{INK}">node2vec vs DeepWalk</h3>
<p style="font-size:24px;color:{MUTED}">Macro-F1 · 임베딩 시드 3개 평균 ± 표준편차</p>
{dotplot}
<div style="flex:1"></div>
<p style="font-size:30px;line-height:1.45;color:{INK2}">차이가 시드 변동 수준<br>→ 시험한 p·q에서 우위 없음</p>
</div>
<div style="flex:1;{card}">
<h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{INK}">GCN vs 다른 방법</h3>
<p style="font-size:24px;color:{MUTED}">Macro-F1 · 같은 5-fold · 시드 0 임베딩</p>
{bar_rows}
<div style="display:flex;align-items:baseline;gap:24px;border-top:1px solid {RULE};padding:20px 0px 0px 0px">
<p style="font-family:{DISPLAY};font-size:60px;font-weight:700;line-height:1.15;color:{INK}">+{pair['macro_f1_diff_mean']:.3f}</p>
<p style="font-size:24px;line-height:1.4;color:{MUTED}">GCN − MLP · 5개 fold 중 {pair['macro_f1_folds_better']}개에서 앞섬 (예비 결과)</p>
</div>
</div>
</div>
{stamp("가설 3", "부분 지지")}
{footer("회색: 학습 없는 기준선 · 파랑: 임베딩 + 분류기 · 주황: GCN", page(6))}''',
    "마지막으로 가설 3입니다. 왼쪽 그림처럼 node2vec의 q를 0.5와 2로 바꿔 봐도, DeepWalk와의 차이는 시드에 따른 변동 정도입니다. "
    "그래서 시험한 설정에서는 node2vec이 낫다고 할 수 없습니다. "
    "오른쪽에서 회색은 학습 없는 기준선, 파란색은 DeepWalk 임베딩에 분류기를 붙인 방법입니다. "
    "GCN은 Macro-F1 0.668로 가장 높았고, 같은 DeepWalk 특징을 쓰되 그래프 연결만 뺀 MLP보다 0.033 높았습니다. "
    "5개 fold 중 4개에서 앞섰지만, 분할 하나와 임베딩 시드 하나로 얻은 예비 결과입니다. 그래서 가설 3도 부분 지지입니다.")

# ---------- 7 summary ----------
def verdict(tg, v, before, after):
    return (f'<div style="flex:1;display:flex;flex-direction:column;gap:16px;background:{SURFACE};border:1px solid {RULE};border-radius:16px;padding:36px 40px">'
            f'<div style="display:flex;align-items:center;justify-content:space-between">{tag(tg)}'
            f'<p style="font-size:24px;font-weight:700;letter-spacing:1px;color:{ACCENT};border:3px double {ACCENT};border-radius:10px;padding:4px 16px">{v}</p></div>'
            f'<p style="font-size:24px;line-height:1.4;color:{MUTED};text-decoration:line-through solid {ACCENT}">{before}</p>'
            f'<p style="font-size:30px;font-weight:600;line-height:1.45;color:{INK}">{after}</p></div>')


def impl(text):
    return f'<p style="flex:1;font-size:30px;line-height:1.45;color:{ON_DARK}">{text}</p>'


slides["summary"] = light("summary", f'''{header("SUMMARY", "종합", "세 가설의 검증 결과")}
<div style="display:flex;gap:32px">
{verdict("H1", "수정", "핵심 인물을 빼면 네트워크가 쪼개진다", "표적 제거가 더 빠르지만, 절반까지 약 30%를 빼야 하는 견고한 구조")}
{verdict("H2", "부분 지지", "같은 부서끼리 밀집해 있다", "동종선호는 약하지만 유의하고, 구조만으로도 부서를 맞힌다 (정확도 0.76)")}
{verdict("H3", "부분 지지", "node2vec과 GCN이 더 정확하다", "node2vec 우위는 없고, GCN이 MLP보다 조금 앞선다 (예비 결과)")}
</div>
<div style="flex:1"></div>
<div style="display:flex;flex-direction:column;gap:18px;background:{NAVY};border-radius:16px;padding:32px 40px">
<p style="font-size:24px;font-weight:600;letter-spacing:2px;color:{ACCENT_DARK}">조직에 주는 시사점</p>
<div style="display:flex;gap:48px">
{impl("상위 10명(1%)이 betweenness의 21% → 허브의 연락 부담 점검")}
{impl("허브가 빠져도 핵심부는 유지 → 연결이 적은 구성원의 고립 관리")}
{impl("연락 기록만으로 소속 추론 → 메타데이터도 프라이버시 보호 대상")}
</div>
</div>
{footer("한계: 무방향 변환 · 데이터 분할 1개 · 하이퍼파라미터 튜닝 없음 (부록 C)", page(7))}''',
    "정리하겠습니다. 가설 1은 수정, 가설 2와 3은 부분 지지입니다. "
    "연결자 역할은 허브의 공통 특징이었고, 네트워크는 쉽게 쪼개지지 않았습니다. "
    "동종선호는 약했지만 구조만으로 부서를 맞힐 수 있었습니다. node2vec의 우위는 보이지 않았고, GCN은 MLP보다 조금 앞섰지만 아직 예비 결과입니다. "
    "조직 관점에서는 세 가지를 말씀드릴 수 있습니다. 첫째, 상위 10명, 즉 1%가 betweenness 총합의 21%를 차지할 만큼 부서 간 중개가 몰려 있으니, 이들의 연락 부담을 살펴봐야 합니다. "
    "둘째, 허브가 빠져도 핵심부는 유지되지만, 연결이 적은 구성원은 고립되지 않게 챙겨야 합니다. "
    "셋째, 연락 기록만으로 소속을 추론할 수 있으니, 메타데이터도 프라이버시 보호 대상으로 다뤄야 합니다. "
    "다만 방향 정보를 쓰지 않았고 데이터 분할도 하나뿐이어서, 이 부분은 다음 과제로 남겨 두었습니다.")

# ---------- 8 thanks ----------
slides["qa"] = f'''<section id="qa" data-transition="fade" style="background:{NAVY};color:{ON_DARK};font-family:{BODY};padding:128px;display:flex;flex-direction:column;justify-content:space-between">
<img src="{NET}" alt="" style="position:absolute;left:1010px;top:110px;width:860px;height:860px;object-fit:contain;opacity:0.6">
{envelope()}
<p style="font-size:24px;font-weight:600;letter-spacing:3px;color:{ACCENT_DARK}">질의응답</p>
<div style="display:flex;flex-direction:column;gap:24px">
<h1 style="font-family:{DISPLAY};font-size:88px;font-weight:700;line-height:1.15;letter-spacing:-2px;color:{ON_DARK}">감사합니다</h1>
<p style="font-size:40px;line-height:1.3;color:{ACCENT_DARK}">질문 받겠습니다</p>
</div>
<div style="display:flex;flex-direction:column;gap:14px;width:1000px">
<div style="display:flex;align-items:baseline;gap:24px"><p style="width:110px;font-family:{MONO};font-size:24px;letter-spacing:2px;color:{ON_DARK_MUTED}">WEB</p><p style="font-family:{MONO};font-size:30px;color:{ON_DARK}"><a href="https://r1s1226.github.io/email-eu-core-sna/">r1s1226.github.io/email-eu-core-sna</a></p></div>
<div style="display:flex;align-items:baseline;gap:24px"><p style="width:110px;font-family:{MONO};font-size:24px;letter-spacing:2px;color:{ON_DARK_MUTED}">REF</p><p style="flex:1;font-size:24px;line-height:1.5;color:{ON_DARK_MUTED}">Leskovec et al. 2007 · Yin et al. 2017 · Perozzi et al. 2014<br>Grover &amp; Leskovec 2016 · Kipf &amp; Welling 2017 · Yu et al. 2017</p></div>
</div>
<aside>이상으로 발표를 마치겠습니다. 결과와 인터랙티브 그래프는 화면의 웹사이트에서 직접 보실 수 있습니다. 감사합니다. 질문 받겠습니다. (질문이 나오면 뒤의 부록 슬라이드를 활용)</aside>
</section>
'''

# ---------- appendix A: all model numbers ----------
def table(head, rows, widths, aligns, size=26):
    th = "".join(f'<th style="width:{w}%;text-align:{a}">{t}</th>' for t, w, a in zip(head, widths, aligns))
    trs = "".join("<tr>" + "".join(f'<td style="text-align:{a}">{t}</td>' for t, a in zip(r, aligns)) + "</tr>" for r in rows)
    return f'<table style="font-size:{size}px;color:{INK}"><tr>{th}</tr>{trs}</table>'


seed0_rows = [("다수 클래스", "—", "majority"), ("이웃 투표", "—", "vote"), ("label spreading (α = 0.2)", "—", "label_spreading"),
              ("로지스틱 회귀", "DeepWalk", "deepwalk_logreg"), ("MLP", "DeepWalk", "mlp"), ("GCN", "DeepWalk", "gcn"),
              ("GCN", "단위 행렬", "gcn_identity")]
t1 = table(["방법", "특징", "정확도", "Macro-F1"], [(a, b) + SHOWN[k] for a, b, k in seed0_rows],
           [44, 22, 17, 17], ["left", "left", "right", "right"])
t2 = table(["방법", "정확도", "Macro-F1", "편차"], [(n, f"{r['acc']:.3f}", f"{r['macro_f1']:.3f}", f"{r['macro_f1_seed_std']:.3f}") for n, r in pts3],
           [38, 20, 25, 17], ["left", "right", "right", "right"])
slides["appx-models"] = light("appx-models", f'''{header("부록 A", "모델 비교 상세", "모든 방법의 정확도와 Macro-F1")}
<div style="display:flex;gap:48px">
<div style="flex:3;display:flex;flex-direction:column;gap:16px">
<p style="font-size:24px;font-weight:600;color:{MUTED}">시드 0 임베딩 · 같은 5-fold</p>
{t1}
</div>
<div style="flex:2;display:flex;flex-direction:column;gap:16px">
<p style="font-size:24px;font-weight:600;color:{MUTED}">로지스틱 회귀 · 임베딩 시드 3개 평균</p>
{t2}
<p style="font-size:24px;line-height:1.45;color:{MUTED}">편차: Macro-F1의 시드 간 표준편차. node2vec은 p=1 고정이며, p와 q가 모두 1이면 DeepWalk와 같다.</p>
</div>
</div>
{footer("GCN − MLP: Macro-F1 +0.033, 정확도 +0.021 (fold별 짝 비교 평균)", "부록 A")}''',
    "[백업 슬라이드]\n정확도나 기준선을 묻는 질문이 나오면 사용합니다. 왼쪽은 시드 0 임베딩으로 같은 5-fold에서 비교한 값이고, 오른쪽은 임베딩 시드 3개의 평균입니다. "
    "GCN과 MLP를 fold별로 짝지어 비교하면 Macro-F1은 평균 0.033, 정확도는 0.021 높았고, 5개 fold 중 4개에서 GCN이 앞섰습니다. "
    "label spreading의 α는 테스트 결과를 본 뒤 기본값 0.2로 바꿨기 때문에, 이 기준선은 약간 낙관적일 수 있습니다.")

# ---------- appendix B: homophily detail ----------
cq = D["cliques"]
def bigfact(num, cap):
    return (f'<div style="display:flex;flex-direction:column;gap:6px;border-top:3px solid {INK};padding:20px 0px 0px 0px">'
            f'<p style="font-family:{DISPLAY};font-size:88px;font-weight:700;line-height:1.1;color:{INK}">{num}</p>'
            f'<p style="font-size:24px;color:{MUTED}">{cap}</p></div>')


pure = round(cq["max_size_cliques"]["share_purity_ge_0.8"] * cq["max_size_cliques"]["count"])
slides["appx-homophily"] = light("appx-homophily", f'''{header("부록 B", "동종선호 상세", "같은 부서끼리 얼마나 모여 있나")}
<div style="display:grid;grid-template-columns:repeat(2, 1fr);gap:40px">
{bigfact(f"{h['assortativity']:.2f}", "부서 assortativity")}
{bigfact(f"{h['dept_modularity_lcc']:.2f}", "부서를 커뮤니티로 본 modularity")}
{bigfact(f"{h['node_homophily_mean'] * 100:.0f}%", "이웃 중 같은 부서 (평균)")}
{bigfact(f"{pure} / {cq['max_size_cliques']['count']}",f"{cq['max_clique_size']}명 최대 clique 중 한 부서가 80% 이상")}
</div>
<div style="flex:1"></div>
<p style="font-size:30px;line-height:1.45;background:{NAVY};color:{ON_DARK};border-radius:16px;padding:24px 40px">가장 촘촘한 {cq['max_kcore']}-core도 {cq['max_kcore_nodes']}명이 {cq['max_kcore_distinct_depts']}개 부서에 걸쳐 있다 → 핵심부는 부서를 가로지른다</p>
{footer("z ≈ 100: 같은 부서 간선 33.6% vs 라벨을 200번 섞은 평균 4.7% (부서 크기 유지)", "부록 B")}''',
    "[백업 슬라이드]\n동종선호가 얼마나 강한지 묻는 질문이 나오면 사용합니다. assortativity는 0.30, 부서를 커뮤니티로 본 modularity는 0.29입니다. "
    "18명짜리 최대 clique 56개 중 한 부서 사람이 80% 이상인 것은 4개뿐이고, 가장 촘촘한 34-core의 79명도 28개 부서에 걸쳐 있습니다.")

# ---------- appendix C: limits ----------
def listcard(title, items, dark=False):
    bg = f"background:{NAVY}" if dark else f"background:{SURFACE};border:1px solid {RULE}"
    tc, ic = (ACCENT_DARK, ON_DARK) if dark else (INK, INK2)
    lis = "".join(f"<li>{t}</li>" for t in items)
    return (f'<div style="flex:1;display:flex;flex-direction:column;gap:20px;{bg};border-radius:16px;padding:40px">'
            f'<h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{tc}">{title}</h3>'
            f'<ul style="font-size:30px;line-height:1.6;color:{ic}">{lis}</ul></div>')


slides["limits"] = light("limits", f'''{header("부록 C", "한계와 향후 과제", "이번 분석의 한계와 다음 단계")}
<div style="display:flex;gap:32px">
{listcard("한계", ["무방향 변환: 단방향 관계(약 45%)의 방향 손실", "분할 1개 · 튜닝 없음 · numpy로 직접 구현", "5명 미만 7개 부서(18명) 평가 제외", "label spreading의 α는 테스트 결과를 보고 정함"])}
{listcard("향후 과제", ["방향 그래프 분석 (방향 betweenness)", "여러 분할·시드 반복, 검증 집합으로 p·q·α 선택", "GraphSAGE · GAT 등 다른 GNN과 비교", "gensim · PyTorch Geometric으로 재현"], dark=True)}
</div>
{footer("email-Eu-core 네트워크 분석", "부록 C")}''',
    "[백업 슬라이드]\n한계나 향후 과제를 묻는 질문이 나오면 사용합니다. 가장 큰 한계는 방향 정보를 버린 것입니다. "
    "관계의 약 45%가 한쪽 방향뿐인데, 무방향으로 바꾸면서 이 정보가 사라졌습니다. 또 데이터 분할이 하나뿐이고 하이퍼파라미터 튜닝도 하지 않았습니다. "
    "다음 단계로는 방향 그래프로 다시 분석하고, 여러 분할과 시드로 반복하면서 검증 집합으로 p, q, α를 고르려고 합니다.")

ORDER = ["cover", "data-hypotheses", "h1-brokers", "h1-removal", "h2", "h3", "summary", "qa", "appx-models", "appx-homophily", "limits"]
assert list(slides) == ORDER[:8] + ["appx-models", "appx-homophily", "limits"]

out = root / "project" / "slides"
for sid, html in slides.items():
    (out / f"{sid}.html").write_text(html, encoding="utf-8")
deck_path = root / "project" / "deck.json"
deck = json.loads(deck_path.read_text(encoding="utf-8"))
deck["order"] = ORDER
deck["sections"] = {
    "s1": {"description": "도입: 데이터와 세 가지 가설", "start": "cover"},
    "s2": {"description": "가설 1: 핵심 인물과 제거 실험", "start": "h1-brokers"},
    "s3": {"description": "가설 2와 가설 3", "start": "h2"},
    "s4": {"description": "종합, 시사점과 질의응답", "start": "summary"},
    "s5": {"description": "부록: 질의응답용 백업 슬라이드", "start": "appx-models"},
}
deck["faces"] = {
    "hahmlet": {"family": "Hahmlet", "href": "https://fonts.googleapis.com/css2?family=Hahmlet:wght@500;700&display=swap"},
    "ibm-plex-sans-kr": {"family": "IBM Plex Sans KR", "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+KR:wght@400;500;600;700&display=swap"},
    "ibm-plex-mono": {"family": "IBM Plex Mono", "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap"},
}
deck_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2), encoding="utf-8")

# local preview: every slide at half size, the asset swapped for the local file
links = "".join(f'<link rel="stylesheet" href="{f["href"]}">' for f in deck["faces"].values())
body = "".join(f'<div class="frame"><div class="label">{i + 1}. {sid}</div><div class="scaler">{slides[sid].replace(NET, "network_dark.png")}</div></div>'
               for i, sid in enumerate(ORDER))
preview_path.write_text(f'''<!doctype html><html><head><meta charset="utf-8">{links}<style>
body{{margin:0;background:#888;font-family:sans-serif}} *{{box-sizing:border-box}}
p,h1,h2,h3,ul{{margin:0}} ul{{padding-left:1.2em}} aside{{display:none}} a{{color:inherit}}
table{{border-collapse:collapse;width:100%}} td,th{{border:1px solid #d9dee6;padding:0.35em 0.6em}}
.frame{{width:960px;height:560px;margin:16px}} .label{{font:14px monospace;color:#fff;height:20px}}
.scaler{{width:1920px;height:1080px;transform:scale(0.5);transform-origin:0 0}}
section{{position:relative;width:1920px;height:1080px;overflow:hidden}}
</style></head><body>{body}</body></html>''', encoding="utf-8")
one = (f'<!doctype html><html><head><meta charset="utf-8">{links}<style>body{{margin:0}} *{{box-sizing:border-box}} '
       'p,h1,h2,h3,ul{margin:0} ul{padding-left:1.2em} aside{display:none} a{color:inherit} '
       'body{word-break:keep-all;overflow-wrap:break-word} table{border-collapse:collapse;width:100%} td,th{border:1px solid #d9dee6;padding:0.35em 0.6em} '
       'section{position:relative;width:1920px;height:1080px;overflow:hidden}</style></head><body>')
shots = preview_path.parent / "shots"
shots.mkdir(exist_ok=True)
for i, sid in enumerate(ORDER):
    (shots / f"{i + 1:02d}-{sid}.html").write_text(one + slides[sid].replace(NET, "../network_dark.png") + "</body></html>", encoding="utf-8")
print("wrote", len(slides), "slides;", {k: len(v) for k, v in slides.items()})
