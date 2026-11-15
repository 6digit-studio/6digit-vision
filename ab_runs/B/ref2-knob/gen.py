#!/usr/bin/env python3
"""Build candidate.html (438x393) reproducing reference.png."""
import math

W, H = 438, 393

# ------------------------------------------------------------ traced outlines
PLATE_PTS = [
    (110, 80), (130, 71), (150, 67), (170, 64), (190, 63), (210, 62),
    (230, 62), (250, 61), (270, 61), (290, 61), (310, 62), (330, 65),
    (350, 72), (362, 77), (370, 84),
    (374, 95), (379, 105), (383, 115), (387, 125), (390, 135), (392, 145),
    (393, 155), (394, 170), (395, 185), (396, 200), (397, 215), (397, 235),
    (397, 255), (396, 270), (394, 282), (391, 292), (387, 302), (381, 312),
    (373, 321), (362, 329), (350, 334),
    (340, 338), (320, 342), (300, 344), (280, 345), (260, 346), (240, 347),
    (220, 347), (200, 347), (180, 347), (160, 346), (140, 345), (126, 341),
    (114, 337), (104, 332),
    (98, 325), (93, 317), (88, 310), (83, 302), (79, 294), (76, 285),
    (73, 275), (71, 262), (70, 248), (70, 232), (70, 218), (71, 205),
    (71, 194), (72, 183), (73, 172), (74, 162), (75, 152), (76, 144),
    (78, 134), (81, 124), (85, 114), (90, 104), (96, 95), (103, 87),
]

CAP_PTS = [
    (128, 275), (123, 270), (119, 265), (117, 260), (115, 255), (113, 250),
    (112, 245), (112, 240), (111, 235), (111, 230), (110, 225), (110, 220),
    (110, 215), (110, 210), (111, 205), (111, 200), (111, 195), (111, 190),
    (112, 185), (112, 180), (112, 175), (112, 170), (112, 165), (113, 160),
    (113, 155), (113, 150), (114, 145), (115, 140), (116, 135), (117, 130),
    (118, 125), (120, 120), (123, 115), (126, 110), (129, 105),
    (140, 98), (150, 93), (160, 90), (170, 88), (180, 87), (190, 86),
    (200, 85), (210, 85), (220, 85), (230, 85), (240, 84), (250, 84),
    (260, 84), (270, 84), (280, 84), (290, 85), (300, 86), (310, 88),
    (320, 91), (330, 98),
    (336, 106), (341, 118), (344, 132), (345, 148), (345, 165), (346, 182),
    (346, 200), (346, 218), (345, 232), (344, 242), (341, 252), (337, 262),
    (331, 270), (322, 277),
    (320, 280), (310, 283), (300, 285), (290, 287), (280, 289), (270, 289),
    (260, 290), (250, 290), (240, 291), (230, 291), (220, 291), (210, 291),
    (200, 292), (190, 292), (180, 291), (170, 291), (160, 290), (150, 288),
    (142, 285), (135, 281),
]


def cr(pts, closed=True, alpha=0.5):
    n = len(pts)

    def d(a, b):
        return max(math.hypot(b[0] - a[0], b[1] - a[1]), 1e-6) ** alpha

    if closed:
        seq = [(pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n])
               for i in range(n)]
    else:
        ext = [pts[0]] + list(pts) + [pts[-1]]
        seq = [(ext[i - 1], ext[i], ext[i + 1], ext[i + 2])
               for i in range(1, len(ext) - 2)]
    out = f"M{seq[0][1][0]:.2f},{seq[0][1][1]:.2f}"
    for p0, p1, p2, p3 in seq:
        t0, t1 = 0.0, d(p0, p1)
        t2, t3 = t1 + d(p1, p2), t1 + d(p1, p2) + d(p2, p3)
        m1x = (t2 - t1) * ((p1[0] - p0[0]) / (t1 - t0) - (p2[0] - p0[0]) / (t2 - t0)
                           + (p2[0] - p1[0]) / (t2 - t1))
        m1y = (t2 - t1) * ((p1[1] - p0[1]) / (t1 - t0) - (p2[1] - p0[1]) / (t2 - t0)
                           + (p2[1] - p1[1]) / (t2 - t1))
        m2x = (t2 - t1) * ((p2[0] - p1[0]) / (t2 - t1) - (p3[0] - p1[0]) / (t3 - t1)
                           + (p3[0] - p2[0]) / (t3 - t2))
        m2y = (t2 - t1) * ((p2[1] - p1[1]) / (t2 - t1) - (p3[1] - p1[1]) / (t3 - t1)
                           + (p3[1] - p2[1]) / (t3 - t2))
        h = t2 - t1
        c1 = (p1[0] + m1x * h / 3, p1[1] + m1y * h / 3)
        c2 = (p2[0] - m2x * h / 3, p2[1] - m2y * h / 3)
        out += f" C{c1[0]:.2f},{c1[1]:.2f} {c2[0]:.2f},{c2[1]:.2f} {p2[0]:.2f},{p2[1]:.2f}"
    return out + (" Z" if closed else "")


def rrect(x, y, w, h, r):
    a, b, c, e = r
    return (f"M{x+a},{y} H{x+w-b} A{b},{b} 0 0 1 {x+w},{y+b} "
            f"V{y+h-c} A{c},{c} 0 0 1 {x+w-c},{y+h} "
            f"H{x+e} A{e},{e} 0 0 1 {x},{y+h-e} V{y+a} A{a},{a} 0 0 1 {x+a},{y} Z")


P_PLATE = cr(PLATE_PTS)
P_CAP = cr(CAP_PTS)
CAP_IN = [(113 + (p[0] - 113) * 0.955, 188 + (p[1] - 188) * 0.94) for p in CAP_PTS]
P_CAPIN = cr(CAP_IN)

P_WELL = (rrect(103, 81, 264, 237, (84, 80, 56, 58)) + " "
          + rrect(150, 279, 218, 40, (30, 30, 26, 26)))

# neon tube: ellipse arc fitted to the measured core
NEO_CX, NEO_CY, NEO_RX, NEO_RY = 289.5, 234.5, 66.0, 64.0
CX45 = NEO_CX + NEO_RX * 0.7071
CY45 = NEO_CY + NEO_RY * 0.7071
P_NEO_R = f"M355.5,148 V{NEO_CY} A{NEO_RX},{NEO_RY} 0 0 1 {CX45:.1f},{CY45:.1f}"
P_NEO_B = (f"M{CX45:.1f},{CY45:.1f} A{NEO_RX},{NEO_RY} 0 0 1 "
           f"{NEO_CX},{NEO_CY+NEO_RY} H150")

# ------------------------------------------------------------ icon grid
GRID = [
    "......#......#..",
    ".....##......##.",
    "....###....#..#.",
    "...####....#..#.",
    "#######.#..#..#.",
    "#######..#..#..+",
    "#######..#..#..#",
    "#######..#..#..#",
    "#######.#..#.##.",
    "...####....#..#.",
    "....###....#..#.",
    ".....##......##.",
    "......#......#..",
]
X0, PX = 173.5, 7.8
Y0, PY = 144.1, 6.825
DOT = 6.1


def dots():
    out = []
    for j, row in enumerate(GRID):
        for k, ch in enumerate(row):
            if ch == ".":
                continue
            cx = X0 + PX * k
            cy = Y0 + PY * j
            o = 0.88 if ch == "+" else 1.0
            out.append(f'<rect x="{cx-DOT/2:.2f}" y="{cy-DOT/2:.2f}" width="{DOT}" '
                       f'height="{DOT}" rx="1.15" fill="#e8e6e1" opacity="{o}"/>')
    return "\n".join(out)


HTML = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  html, body {{ margin:0; padding:0; width:{W}px; height:{H}px; overflow:hidden;
                background:#17181f; }}
  svg {{ display:block; }}
</style>
</head>
<body>
<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg">
<defs>
  <radialGradient id="ambBg" cx="398" cy="308" r="200" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#1fc9c2" stop-opacity="0.22"/>
    <stop offset="0.5" stop-color="#1bb8b4" stop-opacity="0.09"/>
    <stop offset="1" stop-color="#18a8a8" stop-opacity="0"/>
  </radialGradient>

  <linearGradient id="plateG" x1="70" y1="0" x2="398" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#4a4a4c"/>
    <stop offset="0.05" stop-color="#414143"/>
    <stop offset="0.11" stop-color="#464648"/>
    <stop offset="0.20" stop-color="#3d3d3f"/>
    <stop offset="0.34" stop-color="#333537"/>
    <stop offset="0.48" stop-color="#2c2e30"/>
    <stop offset="0.62" stop-color="#27292b"/>
    <stop offset="0.78" stop-color="#222427"/>
    <stop offset="1" stop-color="#1c1e21"/>
  </linearGradient>
  <linearGradient id="plateVert" x1="0" y1="262" x2="0" y2="350" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#000" stop-opacity="0"/>
    <stop offset="1" stop-color="#000" stop-opacity="0.17"/>
  </linearGradient>

  <radialGradient id="wellGlow" cx="336" cy="302" r="118" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#45e8e0" stop-opacity="0.62"/>
    <stop offset="0.45" stop-color="#2cc6c4" stop-opacity="0.22"/>
    <stop offset="1" stop-color="#1ba6a6" stop-opacity="0"/>
  </radialGradient>
  <linearGradient id="wellDark" x1="103" y1="81" x2="220" y2="318" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#0c0e0f"/>
    <stop offset="0.55" stop-color="#05080a"/>
    <stop offset="1" stop-color="#020607"/>
  </linearGradient>

  <linearGradient id="capG" x1="200" y1="88" x2="240" y2="292" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#333537"/>
    <stop offset="0.35" stop-color="#353739"/>
    <stop offset="0.75" stop-color="#363a3b"/>
    <stop offset="1" stop-color="#363a3b"/>
  </linearGradient>
  <radialGradient id="capSheen" cx="160" cy="120" r="95" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#ffffff" stop-opacity="0.06"/>
    <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="capDark" cx="300" cy="92" r="85" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#000000" stop-opacity="0.13"/>
    <stop offset="1" stop-color="#000000" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="capTeal" cx="330" cy="240" r="120" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#3fd2ce" stop-opacity="0.34"/>
    <stop offset="0.45" stop-color="#2fb4b2" stop-opacity="0.16"/>
    <stop offset="1" stop-color="#209a9a" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="capBl" cx="155" cy="285" r="75" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#ffffff" stop-opacity="0.05"/>
    <stop offset="1" stop-color="#ffffff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="capBotDark" cx="272" cy="294" r="80" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#000000" stop-opacity="0.06"/>
    <stop offset="1" stop-color="#000000" stop-opacity="0"/>
  </radialGradient>

  <linearGradient id="fadeR" x1="0" y1="292" x2="0" y2="138" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#fff" stop-opacity="1"/>
    <stop offset="0.34" stop-color="#fff" stop-opacity="0.9"/>
    <stop offset="0.55" stop-color="#fff" stop-opacity="0.72"/>
    <stop offset="0.74" stop-color="#fff" stop-opacity="0.42"/>
    <stop offset="0.90" stop-color="#fff" stop-opacity="0.12"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="fadeB" x1="348" y1="0" x2="150" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#fff" stop-opacity="1"/>
    <stop offset="0.22" stop-color="#fff" stop-opacity="0.92"/>
    <stop offset="0.36" stop-color="#fff" stop-opacity="0.78"/>
    <stop offset="0.52" stop-color="#fff" stop-opacity="0.55"/>
    <stop offset="0.70" stop-color="#fff" stop-opacity="0.30"/>
    <stop offset="0.86" stop-color="#fff" stop-opacity="0.08"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </linearGradient>
  <mask id="mR" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
    <rect width="{W}" height="{H}" fill="url(#fadeR)"/>
  </mask>
  <mask id="mB" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
    <rect width="{W}" height="{H}" fill="url(#fadeB)"/>
  </mask>
  <radialGradient id="rimMaskG" cx="110" cy="188" r="95" gradientUnits="userSpaceOnUse"
                  gradientTransform="translate(110,188) scale(1,1.62) translate(-110,-188)">
    <stop offset="0" stop-color="#fff" stop-opacity="1"/>
    <stop offset="0.52" stop-color="#fff" stop-opacity="0.85"/>
    <stop offset="0.72" stop-color="#fff" stop-opacity="0.35"/>
    <stop offset="0.88" stop-color="#fff" stop-opacity="0.06"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="cyG" cx="330" cy="288" r="78" gradientUnits="userSpaceOnUse">
    <stop offset="0" stop-color="#fff" stop-opacity="1"/>
    <stop offset="0.55" stop-color="#fff" stop-opacity="0.85"/>
    <stop offset="0.82" stop-color="#fff" stop-opacity="0.30"/>
    <stop offset="1" stop-color="#fff" stop-opacity="0"/>
  </radialGradient>
  <mask id="mCy" maskUnits="userSpaceOnUse" x="0" y="0" width="{W}" height="{H}">
    <rect width="{W}" height="{H}" fill="url(#cyG)"/>
  </mask>
  <mask id="mRim" maskUnits="userSpaceOnUse" x="90" y="60" width="290" height="270">
    <rect x="90" y="60" width="290" height="270" fill="url(#rimMaskG)"/>
  </mask>

  <clipPath id="cCap"><path d="{P_CAP}"/></clipPath>
  <clipPath id="cWell"><path d="{P_WELL}"/></clipPath>

  <filter id="b1" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="0.7"/>
  </filter>
  <filter id="b2" x="-40%" y="-40%" width="180%" height="180%">
    <feGaussianBlur stdDeviation="1.6"/>
  </filter>
  <filter id="b3" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="3"/>
  </filter>
  <filter id="b5" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="5"/>
  </filter>
  <filter id="b7" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="7"/>
  </filter>
  <filter id="b8" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="8"/>
  </filter>
  <filter id="b12" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="12"/>
  </filter>
  <filter id="b20" x="-70%" y="-70%" width="240%" height="240%">
    <feGaussianBlur stdDeviation="20"/>
  </filter>
</defs>

<rect width="{W}" height="{H}" fill="#17181f"/>
<rect width="{W}" height="{H}" fill="url(#ambBg)"/>

<!-- shadow -->
<g>
  <path d="{P_PLATE}" fill="#000" opacity="0.95" filter="url(#b12)" transform="translate(0,10)"/>
  <path d="{P_PLATE}" fill="#000" opacity="0.90" filter="url(#b5)" transform="translate(0,5)"/>
  <path d="{P_PLATE}" fill="#000" opacity="0.95" filter="url(#b2)" transform="translate(0,1)"/>
</g>

<!-- plate -->
<path d="{P_PLATE}" fill="url(#plateG)"/>
<path d="{P_PLATE}" fill="url(#plateVert)"/>
<path d="{P_PLATE}" fill="none" stroke="#0a0c0e" stroke-opacity="0.7" stroke-width="2.2"/>

<!-- well -->
<path d="{P_WELL}" fill="url(#wellDark)"/>
<g clip-path="url(#cWell)">
  <rect x="100" y="75" width="280" height="250" fill="url(#wellGlow)"/>
</g>
<path d="{P_WELL}" fill="none" stroke="#020506" stroke-opacity="0.9" stroke-width="1.2"
      clip-path="url(#cWell)" style="display:none"/>

<!-- wide neon bloom -->
<g mask="url(#mR)">
  <path d="{P_NEO_R}" fill="none" stroke="#2ab8b6" stroke-width="30" opacity="0.26" filter="url(#b12)"/>
  <path d="{P_NEO_R}" fill="none" stroke="#35cecb" stroke-width="12" opacity="0.45" filter="url(#b5)"/>
</g>
<g mask="url(#mB)">
  <path d="{P_NEO_B}" fill="none" stroke="#2ab8b6" stroke-width="30" opacity="0.24" filter="url(#b12)"/>
  <path d="{P_NEO_B}" fill="none" stroke="#35cecb" stroke-width="12" opacity="0.40" filter="url(#b5)"/>
  <path d="{P_NEO_B}" fill="none" stroke="#34a8a8" stroke-width="11" opacity="0.55"
        filter="url(#b7)" transform="translate(0,13)"/>
</g>

<!-- cap -->
<path d="{P_CAP}" fill="url(#capG)"/>
<g clip-path="url(#cCap)">
  <rect x="100" y="70" width="280" height="250" fill="url(#capSheen)"/>
  <rect x="100" y="70" width="280" height="250" fill="url(#capDark)"/>
  <rect x="100" y="70" width="280" height="250" fill="url(#capBl)"/>
  <rect x="100" y="70" width="280" height="250" fill="url(#capTeal)"/>
  <rect x="100" y="70" width="280" height="250" fill="url(#capBotDark)"/>
  <rect x="100" y="272" width="280" height="38" fill="#000" opacity="0.07"/>
</g>
<path d="{P_CAP}" fill="none" stroke="#04080a" stroke-opacity="0.72" stroke-width="3.2" filter="url(#b1)"/>

<!-- cyan rim light on the cap's lower-right bevel -->
<g mask="url(#mCy)">
  <path d="{P_CAP}" fill="none" stroke="#7fe8e4" stroke-opacity="0.55" stroke-width="4" filter="url(#b3)"/>
  <path d="{P_CAP}" fill="none" stroke="#b6f7f2" stroke-opacity="0.55" stroke-width="1.4" filter="url(#b2)"/>
</g>

<!-- cap bevel specular (left edge only) -->
<g mask="url(#mRim)">
  <path d="{P_CAPIN}" fill="none" stroke="#ffffff" stroke-opacity="0.55" stroke-width="3" filter="url(#b3)"/>
  <path d="{P_CAPIN}" fill="none" stroke="#ffffff" stroke-opacity="0.70" stroke-width="1.2" filter="url(#b2)"/>
  <path d="{P_CAPIN}" fill="none" stroke="#ffffff" stroke-opacity="0.88" stroke-width="0.8"/>
</g>

<!-- neon tube -->
<g mask="url(#mR)">
  <path d="{P_NEO_R}" fill="none" stroke="#4fd8d6" stroke-width="8" opacity="0.55" filter="url(#b3)"/>
  <path d="{P_NEO_R}" fill="none" stroke="#8df1ef" stroke-width="3.4" opacity="0.9" filter="url(#b2)"/>
  <path d="{P_NEO_R}" fill="none" stroke="#eafffd" stroke-width="1" opacity="0.55"/>
</g>
<g mask="url(#mB)">
  <path d="{P_NEO_B}" fill="none" stroke="#4fd8d6" stroke-width="8" opacity="0.45" filter="url(#b3)"/>
  <path d="{P_NEO_B}" fill="none" stroke="#8df1ef" stroke-width="3.4" opacity="0.85" filter="url(#b2)"/>
  <path d="{P_NEO_B}" fill="none" stroke="#eafffd" stroke-width="1" opacity="0.45"/>
</g>

<!-- icon -->
<g>
  <g filter="url(#b3)" opacity="0.18">{dots()}</g>
  <g filter="url(#b2)" opacity="0.28">{dots()}</g>
  {dots()}
</g>
</svg>
</body>
</html>
"""

with open("candidate.html", "w") as f:
    f.write(HTML)
print("wrote candidate.html")
