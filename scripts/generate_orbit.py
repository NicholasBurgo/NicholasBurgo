#!/usr/bin/env python3
"""Regenerate orbit.svg: a deep-space radar scan of the most recently pushed
private repos.

Fetches the authenticated user's private repositories (newest push first),
takes the top 7, and renders them as radar blips plus a monospace readout.
Distance (au) encodes recency rank; blip/dot color is the repo's primary
language color; sweep pings and row pulses are phase-locked to each blip's
bearing.

Needs a token that can list private repos (GITHUB_TOKEN in Actions cannot):
    GH_TOKEN=$(gh auth token) python3 scripts/generate_orbit.py

Output is deterministic for a given repo list, so the nightly workflow only
commits when something actually changed.
"""

import json
import math
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

OUT = os.path.join(os.path.dirname(__file__), "..", "orbit.svg")

COUNT = 7
CX, CY = 215, 170
ANGLES = [25, 80, 145, 190, 235, 285, 340]  # degrees clockwise from +x
AUS = [0.4, 0.7, 0.9, 1.2, 1.4, 1.7, 1.9]   # recency rank -> distance
SWEEP_SECONDS = 6
ROW_STEP = 27
ROW_DOT_Y = 95.5
ROW_TEXT_Y = 99

# GitHub linguist colors for languages that plausibly show up here.
LANG_COLORS = {
    "javascript": "#f1e05a",
    "typescript": "#3178c6",
    "python": "#3776ab",
    "rust": "#dea584",
    "jupyter notebook": "#da5b0b",
    "c#": "#178600",
    "c++": "#f34b7d",
    "c": "#555555",
    "go": "#00add8",
    "java": "#b07219",
    "html": "#e34c26",
    "css": "#563d7c",
    "shell": "#89e051",
    "dockerfile": "#384d54",
}
FALLBACK_COLOR = "#8b949e"


def fetch_private_repos(token):
    req = urllib.request.Request(
        "https://api.github.com/user/repos"
        "?visibility=private&affiliation=owner&sort=pushed&direction=desc&per_page=30",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        repos = json.load(resp)
    repos = [r for r in repos if r.get("private") and not r.get("archived")]
    # API already sorts by push; re-sort with a name tie-break for determinism.
    repos.sort(key=lambda r: (r["pushed_at"], r["name"]), reverse=True)
    return repos[:COUNT]


def display_name(repo):
    name = repo["name"].lower()
    if len(name) > 24:
        name = name[:23] + "…"
    return escape(name)


def display_lang(repo):
    lang = (repo.get("language") or "unknown").lower()
    if lang == "jupyter notebook":
        lang = "jupyter"
    return escape(lang.split(" ")[0][:12])


def lang_color(repo):
    return LANG_COLORS.get((repo.get("language") or "").lower(), FALLBACK_COLOR)


def blip_pos(angle_deg, au):
    r = 40 + au * 45
    rad = math.radians(angle_deg)
    return round(CX + r * math.cos(rad), 1), round(CY + r * math.sin(rad), 1)


STATIC_HEAD = """<svg width="860" height="340" viewBox="0 0 860 340" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{aria}">
  <style>
    .tw {{ animation: twinkle 3.2s ease-in-out infinite; }}
    .tw2 {{ animation: twinkle 4.1s ease-in-out infinite; animation-delay: 1.3s; }}
    .tw3 {{ animation: twinkle 2.6s ease-in-out infinite; animation-delay: 0.7s; }}
    @keyframes twinkle {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.15; }} }}
    .drift {{ animation: drift 28.0s linear infinite; }}
    @keyframes drift {{ from {{ transform: translateY(0); }} to {{ transform: translateY(340px); }} }}

    .hdr {{ font: 500 11px ui-monospace, 'Cascadia Code', 'Fira Code', Consolas, monospace; fill: #6e7681; letter-spacing: 1px; }}
    .name {{ font: 500 11px ui-monospace, 'Cascadia Code', 'Fira Code', Consolas, monospace; fill: #9198a1; }}
    .meta {{ font: 500 10px ui-monospace, 'Cascadia Code', 'Fira Code', Consolas, monospace; fill: #6e7681; }}
    .stat {{ font: 500 10px ui-monospace, 'Cascadia Code', 'Fira Code', Consolas, monospace; fill: #f0c674; }}
    .brg  {{ font: 500 8px ui-monospace, 'Cascadia Code', 'Fira Code', Consolas, monospace; fill: #484f58; }}

    .sweep {{ animation: sweep {sweep}s linear infinite; transform-origin: 215px 170px; }}
    @keyframes sweep {{ from {{ transform: rotate(0deg); }} to {{ transform: rotate(360deg); }} }}

    .blip {{ animation: blip {sweep}s linear infinite; }}
    @keyframes blip {{ 0% {{ opacity: 1; }} 55% {{ opacity: 0.2; }} 100% {{ opacity: 0.2; }} }}
    .ping {{ animation: ping {sweep}s linear infinite; transform-box: fill-box; transform-origin: center; }}
    @keyframes ping {{ 0% {{ transform: scale(0.4); opacity: 0.7; }} 45% {{ transform: scale(2.2); opacity: 0; }} 100% {{ transform: scale(2.2); opacity: 0; }} }}
    .row {{ animation: rowp {sweep}s linear infinite; }}
    @keyframes rowp {{ 0% {{ opacity: 1; }} 55% {{ opacity: 0.55; }} 100% {{ opacity: 0.55; }} }}

    .core {{ animation: corep 3s ease-in-out infinite; }}
    @keyframes corep {{ 0%, 100% {{ opacity: 0.25; }} 50% {{ opacity: 0.6; }} }}
    .cursor {{ animation: cur 1.1s steps(1) infinite; }}
    @keyframes cur {{ 0%, 49% {{ opacity: 1; }} 50%, 100% {{ opacity: 0; }} }}

{delays}  </style>

  <rect width="860" height="340" fill="#0d1117"/>
  <g class="drift">
    <g id="rstars">
      <circle cx="33" cy="52" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="97" cy="301" r="0.8" fill="#ffffff" opacity="0.4"/>
      <circle cx="141" cy="26" r="1.2" fill="#ffffff" opacity="0.6" class="tw"/>
      <circle cx="58" cy="187" r="0.7" fill="#ffffff" opacity="0.35"/>
      <circle cx="122" cy="118" r="1.1" fill="#ffffff" opacity="0.55"/>
      <circle cx="203" cy="322" r="0.9" fill="#ffffff" opacity="0.45"/>
      <circle cx="259" cy="58" r="1.0" fill="#ffffff" opacity="0.5" class="tw2"/>
      <circle cx="305" cy="146" r="0.8" fill="#ffffff" opacity="0.4"/>
      <circle cx="288" cy="262" r="1.2" fill="#ffffff" opacity="0.6"/>
      <circle cx="357" cy="31" r="0.9" fill="#ffffff" opacity="0.45"/>
      <circle cx="371" cy="208" r="0.7" fill="#ffffff" opacity="0.35" class="tw3"/>
      <circle cx="402" cy="304" r="1.1" fill="#ffffff" opacity="0.55"/>
      <circle cx="433" cy="89" r="0.8" fill="#ffffff" opacity="0.4"/>
      <circle cx="455" cy="177" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="489" cy="258" r="0.9" fill="#ffffff" opacity="0.45" class="tw"/>
      <circle cx="514" cy="44" r="1.2" fill="#ffffff" opacity="0.6"/>
      <circle cx="548" cy="132" r="0.7" fill="#ffffff" opacity="0.35"/>
      <circle cx="561" cy="296" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="596" cy="210" r="0.8" fill="#ffffff" opacity="0.4" class="tw2"/>
      <circle cx="613" cy="71" r="1.1" fill="#ffffff" opacity="0.55"/>
      <circle cx="648" cy="313" r="0.9" fill="#ffffff" opacity="0.45"/>
      <circle cx="676" cy="158" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="699" cy="36" r="1.2" fill="#ffffff" opacity="0.6" class="tw3"/>
      <circle cx="722" cy="244" r="0.8" fill="#ffffff" opacity="0.4"/>
      <circle cx="748" cy="109" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="768" cy="290" r="0.7" fill="#ffffff" opacity="0.35"/>
      <circle cx="793" cy="180" r="1.1" fill="#ffffff" opacity="0.55" class="tw"/>
      <circle cx="816" cy="58" r="0.9" fill="#ffffff" opacity="0.45"/>
      <circle cx="838" cy="236" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="846" cy="127" r="0.8" fill="#ffffff" opacity="0.4"/>
      <circle cx="72" cy="88" r="0.9" fill="#ffffff" opacity="0.45" class="tw2"/>
      <circle cx="176" cy="222" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="238" cy="193" r="0.7" fill="#ffffff" opacity="0.35"/>
      <circle cx="324" cy="90" r="1.1" fill="#ffffff" opacity="0.55"/>
      <circle cx="508" cy="204" r="0.8" fill="#ffffff" opacity="0.4" class="tw3"/>
      <circle cx="585" cy="20" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="663" cy="222" r="1.1" fill="#ffffff" opacity="0.55"/>
      <circle cx="737" cy="20" r="0.8" fill="#ffffff" opacity="0.4" class="tw"/>
      <circle cx="806" cy="320" r="1.0" fill="#ffffff" opacity="0.5"/>
      <circle cx="48" cy="262" r="1.2" fill="#ffffff" opacity="0.6"/>
    </g>
    <use href="#rstars" y="-340"/>
  </g>

  <g stroke="#30363d" fill="none" opacity="0.55">
    <circle cx="215" cy="170" r="45"/>
    <circle cx="215" cy="170" r="90"/>
    <circle cx="215" cy="170" r="135"/>
    <line x1="80" y1="170" x2="350" y2="170" stroke-dasharray="2 5"/>
    <line x1="215" y1="35" x2="215" y2="305" stroke-dasharray="2 5"/>
  </g>
  <g stroke="#30363d" opacity="0.8">
    <line x1="344" y1="170" x2="350" y2="170"/>
    <line x1="326.7" y1="234.5" x2="331.9" y2="237.5"/>
    <line x1="279.5" y1="281.7" x2="282.5" y2="286.9"/>
    <line x1="215" y1="299" x2="215" y2="305"/>
    <line x1="150.5" y1="281.7" x2="147.5" y2="286.9"/>
    <line x1="103.3" y1="234.5" x2="98.1" y2="237.5"/>
    <line x1="86" y1="170" x2="80" y2="170"/>
    <line x1="103.3" y1="105.5" x2="98.1" y2="102.5"/>
    <line x1="150.5" y1="58.3" x2="147.5" y2="53.1"/>
    <line x1="215" y1="41" x2="215" y2="35"/>
    <line x1="279.5" y1="58.3" x2="282.5" y2="53.1"/>
    <line x1="326.7" y1="105.5" x2="331.9" y2="102.5"/>
  </g>
  <text x="215" y="26" text-anchor="middle" class="brg">000</text>
  <text x="358" y="173" class="brg">090</text>
  <text x="215" y="321" text-anchor="middle" class="brg">180</text>
  <text x="72" y="173" text-anchor="end" class="brg">270</text>

  <g class="sweep">
    <path d="M215 170 L350 170 A135 135 0 0 0 331.9 102.5 Z" fill="#3fb950" opacity="0.12"/>
    <path d="M215 170 L331.9 102.5 A135 135 0 0 0 282.5 53.1 Z" fill="#3fb950" opacity="0.05"/>
    <line x1="215" y1="170" x2="350" y2="170" stroke="#3fb950" stroke-opacity="0.8"/>
  </g>

"""

STATIC_CORE = """
  <circle cx="215" cy="170" r="11" fill="#f0c674" class="core"/>
  <circle cx="215" cy="170" r="5" fill="#f5d78e"/>

  <text x="385" y="58" class="hdr">// deep-space scan :: private sector</text>
  <text x="845" y="58" text-anchor="end" class="hdr">{count} objects tracked</text>
  <line x1="385" y1="72" x2="845" y2="72" stroke="#30363d"/>

"""

STATIC_TAIL = """
  <text x="385" y="290" class="hdr">// signal origin classified</text>
  <rect x="592" y="280" width="7" height="12" fill="#3fb950" class="cursor"/>
</svg>
"""


def render(repos):
    n = len(repos)
    aria = f"Deep-space scan tracking {n} private repositories"

    delays = ""
    for i, angle in enumerate(ANGLES[:n]):
        delay = round(angle / 360 * SWEEP_SECONDS, 2)
        delays += f"    .d{i + 1} {{ animation-delay: {delay}s; }}\n"

    svg = STATIC_HEAD.format(aria=aria, sweep=SWEEP_SECONDS, delays=delays)

    for i, repo in enumerate(repos):
        x, y = blip_pos(ANGLES[i], AUS[i])
        color = lang_color(repo)
        svg += (
            f'  <circle cx="{x}" cy="{y}" r="10" fill="{color}" opacity="0" class="ping d{i + 1}"/>\n'
            f'  <circle cx="{x}" cy="{y}" r="4.5" fill="{color}" class="blip d{i + 1}"/>\n'
        )

    svg += STATIC_CORE.format(count=n)

    for i, repo in enumerate(repos):
        dot_y = ROW_DOT_Y + i * ROW_STEP
        text_y = ROW_TEXT_Y + i * ROW_STEP
        svg += (
            f'  <g class="row d{i + 1}">\n'
            f'    <circle cx="392" cy="{dot_y}" r="3.5" fill="{lang_color(repo)}"/>\n'
            f'    <text x="406" y="{text_y}" class="name">{display_name(repo)}</text>\n'
            f'    <text x="610" y="{text_y}" class="meta">{display_lang(repo)}</text>\n'
            f'    <text x="750" y="{text_y}" text-anchor="end" class="meta">{AUS[i]} au</text>\n'
            f'    <text x="765" y="{text_y}" class="stat">private</text>\n'
            f'  </g>\n'
        )

    svg += STATIC_TAIL
    return svg


def main():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("GH_TOKEN not set; need a PAT that can list private repos")

    repos = fetch_private_repos(token)
    if not repos:
        sys.exit("no private repos returned; refusing to overwrite orbit.svg")

    svg = render(repos)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"orbit.svg regenerated with {len(repos)} repos:")
    for repo in repos:
        print(f"  {repo['pushed_at'][:10]}  {repo['name']}  ({repo.get('language') or 'unknown'})")


if __name__ == "__main__":
    main()
