from html import escape
from math import sqrt
from textwrap import shorten, wrap

WIDTH = 1080
ICE, AQUA, DIM, EDGE = '#ccfbf0', '#60e7d8', '#8ac1bd', '#269c93'
MONO = 'ui-monospace, SFMono-Regular, Menlo, monospace'
DISPLAY = 'Avenir Next, system-ui, sans-serif'


def box(x, y, w, h, radius, fill, stroke='none'):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>'


def label(x, y, value, size, color=ICE, weight=500, *, mono=False, anchor='start'):
    family = MONO if mono else DISPLAY
    return (f'<text x="{x}" y="{y}" fill="{color}" font-size="{size}" font-weight="{weight}" '
            f'font-family="{family}" text-anchor="{anchor}">{escape(str(value))}</text>')


def panel(height, title, description, elements, *, inset=True):
    defs = '''<defs>
<linearGradient id="panel" x2=".85" y2="1">
  <stop stop-color="#0b3d41"/><stop offset=".55" stop-color="#10454a"/><stop offset="1" stop-color="#28435b"/>
</linearGradient>
<radialGradient id="glow" cx=".2" cy=".04" r=".52" gradientTransform="translate(0 .02) scale(1 .77)">
  <stop stop-color="#24a393" stop-opacity=".56"/><stop offset="1" stop-color="#24a393" stop-opacity="0"/>
</radialGradient>
<linearGradient id="inset" x2="1" y2="1">
  <stop stop-color="#102e33"/><stop offset="1" stop-color="#11282f"/>
</linearGradient>
<clipPath id="avatar"><circle cx="116" cy="112" r="54"/></clipPath>
</defs>'''
    roof = box(1, 1, WIDTH-2, height-2, 25, 'url(#panel)', EDGE)
    glow = box(2, 2, WIDTH-4, height-4, 25, 'url(#glow)')
    inner = box(32, 30, WIDTH-64, height-61, 23, 'url(#inset)', '#247e77') if inset else ''
    return '\n'.join([
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{escape(title)}</title>',
        f'<desc id="desc">{escape(description)}</desc>',
        defs, roof, glow, inner, *elements, '</svg>', '',
    ])


def header(d):
    username = d['login'].lower()
    bio = shorten(d['bio'], 65, placeholder='…')
    elements = [
        *(f'<circle cx="929" cy="145" r="{r}" fill="none" stroke="#1b3b41"/>' for r in (39, 67, 102)),
        '<circle cx="116" cy="112" r="60" fill="#102e33" stroke="#4ad8c7" stroke-width="2.5"/>',
        f'<image x="62" y="58" width="108" height="108" href="{escape(d["avatar"], quote=True)}" clip-path="url(#avatar)"/>',
        label(207, 81, '@'+username, 18, AQUA, 700, mono=True),
        label(203, 147, username, 62, ICE, 800),
        label(207, 184, bio, 20, AQUA),
    ]
    for i, language in enumerate(('Swift', 'Rust', 'Python', 'TypeScript')):
        x = 58 + 160*i
        elements += [box(x, 213, 143, 36, 18, '#173b40', EDGE), label(x+17, 237, language, 17, weight=700)]
    return panel(300, f'{username} on GitHub', f'{bio} Languages: Swift, Rust, Python, TypeScript.', elements)


def polygon(points, color):
    path = ' '.join(f'{x:.2f},{y:.2f}' for x, y in points)
    return f'<polygon points="{path}" fill="{color}"/>'


def city(d):
    total, active, peak = d['total'], d['active'], d['peak']
    elements = [
        label(43, 63, 'CONTRIBUTION CITY', 19, AQUA, 700, mono=True),
        label(40, 119, f'{total:,}', 54, ICE, 800),
        label(43, 152, 'contributions in the last year', 18, AQUA, 700),
        label(43, 192, f'{active:,} active days', 18),
        label(43, 220, f'Busiest day: {peak:,}', 18),
        label(43, 475, '@'+d['login'].lower(), 16, AQUA, mono=True),
        label(43, 498, 'PUBLIC CONTRIBUTION CALENDAR', 13, DIM, mono=True),
    ]
    tiles = []
    for week, day, count, level in sorted(d['days'], key=lambda row: (row[0]+row[1], row[0])):
        x, y = 391 + 12.3*(week-day), 83 + 6.65*(week+day)
        scale = sqrt(count/peak) if peak else 0
        tiles.append((x, y, scale, level))
    max_height = min([149, *((y-28)/scale for _, y, scale, _ in tiles if scale)])
    roofs = ('#1c6869', '#2d9b90', '#40b7a9', '#60cabb', '#85e4d4')
    front = ('#135557', '#227971', '#25897f', '#409e94', '#59b2a6')
    side = ('#17494c', '#1b655f', '#217369', '#33847b', '#47988d')
    for x, y, scale, level in tiles:
        height = 4 + max_height*scale
        a, b, c, e = (x, y-6.3), (x+11.7, y), (x, y+6.3), (x-11.7, y)
        ra, rb, rc, re = [(px, py-height) for px, py in (a,b,c,e)]
        elements += [polygon((re, rc, c, e), side[level]), polygon((rc, rb, b, c), front[level]), polygon((ra, rb, rc, re), roofs[level])]
    return panel(525, 'Contribution City', f'{total:,} contributions across {active:,} active days. Busiest day: {peak:,}.', elements, inset=False)


def population(d):
    elements = [
        label(56, 78, 'Profile Signal', 36, weight=800),
        label(58, 105, 'PUBLIC GITHUB STATS', 16, AQUA, mono=True),
    ]
    metrics = (('Stars', 'stars', '#55dac9'), ('Contributions', 'total', '#b6a1ff'),
               ('Repos', 'repos', '#78a4ff'), ('Followers', 'followers', '#43dbee'))
    reference = max(1, *(d[key] for _, key, _ in metrics))
    for i, (title, key, color) in enumerate(metrics):
        x = 48 + i*251
        width = max(12, round(178*d[key]/reference))
        elements += [
            box(x, 135, 230, 134, 20, '#0d1e26', EDGE),
            label(x+22, 176, title, 17, AQUA, 700, mono=True),
            label(x+20, 227, f'{d[key]:,}', 49, color, 800),
            box(x+22, 247, 178, 8, 4, '#263b42'),
            box(x+22, 247, width, 8, 4, color),
        ]
    details = ', '.join(f'{d[key]:,} {title.lower()}' for title, key, _ in metrics)
    return panel(322, 'Profile Signal', details, elements)


def ring(x, y, mix):
    palette = {'Rust':'#e9a984', 'Swift':'#ef624d', 'Python':'#66b7e6', 'JavaScript':'#e9cf60'}
    total = sum(size for _, size in mix)
    offset = 0
    elements = []
    for name, size in mix:
        part = 100*size/total
        color = palette.get(name, '#69b6aa')
        elements.append(f'<circle cx="{x}" cy="{y}" r="32" fill="none" stroke="{color}" stroke-width="9" '
                        f'pathLength="100" stroke-dasharray="{part:.4f} {100-part:.4f}" '
                        f'stroke-dashoffset="{-offset:.4f}" transform="rotate(-90 {x} {y})"/>')
        offset += part
    elements.append(label(x, y+5, f'{round(100*mix[0][1]/total)}%', 16, weight=700, anchor='middle'))
    return elements


def landmarks(d):
    projects = d['projects']
    elements = [label(42, 52, 'PROJECTS.LIST', 19, AQUA, mono=True),
                label(242, 52, './projects.sh --all', 17, DIM, mono=True),
                label(1038, 52, f'{len(projects)} projects', 17, DIM, mono=True, anchor='end'),
                box(41, 68, 998, 1.5, 0, EDGE)]
    for i, project in enumerate(projects):
        x, y = 36 + (i % 2)*515, 91 + (i // 2)*226
        name, mix = project['name'], project['mix']
        elements += [box(x, y, 493, 207, 18, '#112c33', EDGE), box(x+1, y+39, 491, 1, 0, EDGE),
                     f'<circle cx="{x+473}" cy="{y+21}" r="5" fill="#58bd7c"/>',
                     label(x+19, y+26, name, 16, AQUA, mono=True), label(x+21, y+74, name, 24, weight=750)]
        lines = wrap(' '.join(project['description'].split()), width=35, max_lines=2, placeholder='…')
        elements += [label(x+22, y+103+21*j, line, 16, AQUA, mono=True) for j, line in enumerate(lines)]
        if project['language']:
            lang = shorten(project['language'], 16, placeholder='…')
            elements += [box(x+21, y+146, max(64, len(lang)*9+22), 23, 12, '#17474b', EDGE),
                         label(x+34, y+162, lang, 13, AQUA, mono=True)]
        if mix:
            elements += ring(x+438, y+113, mix)
        updated = project['updated'].strftime('%b %d, %Y')
        elements.append(label(x+21, y+191, f"{project['stars']:,} stars  /  updated {updated}", 15, DIM, mono=True))
    height = 331 if len(projects) <= 2 else 557
    return panel(height, 'Landmarks', ', '.join(p['name'] for p in projects) or 'No public landmark projects', elements, inset=False)


def visit(d):
    handle = '@'+d['login'].lower()
    elements = [box(426, 49, 228, 58, 29, '#0c1c23', '#66cabf'),
                '<circle cx="459" cy="79" r="16" fill="#31484f"/>',
                label(459, 85, 'G', 17, weight=800, anchor='middle'),
                label(487, 74, 'GitHub', 15, AQUA, 700, mono=True),
                label(487, 94, handle, 18, weight=750)]
    return panel(156, 'Visit GitHub', handle, elements)


def render_cards(data):
    return {f'{renderer.__name__}.svg': renderer(data) for renderer in (header, city, population, landmarks, visit)}
