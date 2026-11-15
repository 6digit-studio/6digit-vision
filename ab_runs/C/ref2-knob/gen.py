#!/usr/bin/env python3
"""Generate candidate.html -- HTML+CSS+inline SVG recreation of reference.png (438x393)."""

W, H = 438, 393

PLATE_PATH = open('_work/plate_path.txt').read().strip()

# well: measured 102.5,81 .. 362,318 radius ~72
WELL = dict(x=102.5, y=81.0, w=259.5, h=237.0, r=72)
# face: measured 112.5,84.5 .. 347,290 with per-corner radii
FACE = dict(x=112.5, y=84.5, w=234.5, h=205.5, rt=65, rr=58, rb=50, rl=54)

SP_ROWS = [144.5,151.3,157.9,164.8,171.6,178.5,185.4,192.4,199.2,205.6,212.5,219.5,226.4]
SP_COLS = [173.5,181.4,189.4,197.4,205.0,212.6,220.5]
OCC = [(6,6),(5,6),(4,6),(3,6),(0,6),(0,6),(0,6),(0,6),(0,6),(3,6),(4,6),(5,6),(6,6)]
SPEAKER = [(SP_COLS[c], SP_ROWS[r]) for r,(a,b) in enumerate(OCC) for c in range(a,b+1)]
WAVE = [
    (236,169),(244,176),(244,183),(244,190),(237,198),
    (259,156),(259,163),(267,170),(267,176),(267,183),(267,190),(267,197),(259,204),(259,211),
    (275,140),(275,147),(282,148),(282,155),(282,162),(290,169),(290,175),(291,182),
    (291,188),(292,195),(285,201),(283,210),(275,217),(283,217),(275,224),
]
DOTS = SPEAKER + WAVE


def face_path(d=0.0):
    """Face rounded-rect path, optionally offset outward by d (radii grow by d)."""
    x, y = FACE['x'] - d, FACE['y'] - d
    w, h = FACE['w'] + 2 * d, FACE['h'] + 2 * d
    rt, rr, rb, rl = FACE['rt'] + d, FACE['rr'] + d, FACE['rb'] + d, FACE['rl'] + d
    return (f"M{x+rl:.1f},{y:.1f} H{x+w-rr:.1f} A{rr:.1f},{rr:.1f} 0 0 1 {x+w:.1f},{y+rr:.1f} "
            f"V{y+h-rb:.1f} A{rb:.1f},{rb:.1f} 0 0 1 {x+w-rb:.1f},{y+h:.1f} "
            f"H{x+rl:.1f} A{rl:.1f},{rl:.1f} 0 0 1 {x:.1f},{y+h-rl:.1f} "
            f"V{y+rt:.1f} A{rt:.1f},{rt:.1f} 0 0 1 {x+rl:.1f},{y:.1f} Z")


def well_path():
    return (f"M{WELL['x']+WELL['r']:.1f},{WELL['y']:.1f} "
            f"H{WELL['x']+WELL['w']-WELL['r']:.1f} A{WELL['r']},{WELL['r']} 0 0 1 {WELL['x']+WELL['w']:.1f},{WELL['y']+WELL['r']} "
            f"V{WELL['y']+WELL['h']-WELL['r']:.1f} A{WELL['r']},{WELL['r']} 0 0 1 {WELL['x']+WELL['w']-WELL['r']:.1f},{WELL['y']+WELL['h']} "
            f"H{WELL['x']+WELL['r']:.1f} A{WELL['r']},{WELL['r']} 0 0 1 {WELL['x']:.1f},{WELL['y']+WELL['h']-WELL['r']} "
            f"V{WELL['y']+WELL['r']:.1f} A{WELL['r']},{WELL['r']} 0 0 1 {WELL['x']+WELL['r']:.1f},{WELL['y']:.1f} Z")


def tube_parts(d):
    """Glow-path parts: bottom run + corner + right run, offset outward by d."""
    bot = 298.5 + d
    rgt = 356.5 + d
    r = 39.0 + d
    cy = bot - r
    a = f"M132,{bot:.1f} H{rgt-r:.1f} A{r:.1f},{r:.1f} 0 0 0 {rgt:.1f},{cy:.1f} V250"
    b = f"M{rgt:.1f},252 V104"
    return a, b


def rim_path():
    i = 4.2
    x, y = FACE['x'] + i, FACE['y'] + i
    w, h = FACE['w'] - 2 * i, FACE['h'] - 2 * i
    rt, rb = FACE['rt'] - i, FACE['rb'] - i
    k = 0.7071
    return (f"M{x+rt-rt*k:.1f},{y+rt-rt*k:.1f} A{rt:.1f},{rt:.1f} 0 0 0 {x:.1f},{y+rt:.1f} "
            f"V{y+h-rb:.1f} A{rb:.1f},{rb:.1f} 0 0 0 {x+rb-rb*k:.1f},{y+h-rb+rb*k:.1f}")


def dots(rx=1.15):
    return "\n".join(f'<rect x="{x-2.85:.1f}" y="{y-2.85:.1f}" width="5.7" height="5.7" rx="{rx}"/>'
                     for (x, y) in DOTS)


core_a, core_b = tube_parts(0)
halo_a, halo_b = tube_parts(1.5)
echo_a, echo_b = tube_parts(9.5)

html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
  html,body{{margin:0;padding:0;width:{W}px;height:{H}px;overflow:hidden;background:#17181f;}}
  svg{{display:block;}}
</style></head><body>
<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <radialGradient id="bgAmb" cx="0.82" cy="0.86" r="0.60">
    <stop offset="0"   stop-color="#2b9089" stop-opacity="0.42"/>
    <stop offset="0.35" stop-color="#1d6b66" stop-opacity="0.20"/>
    <stop offset="0.7" stop-color="#153c3c" stop-opacity="0.06"/>
    <stop offset="1"   stop-color="#17181f" stop-opacity="0"/>
  </radialGradient>

  <linearGradient id="plateG" x1="0" y1="0.5" x2="1" y2="0.5">
    <stop offset="0"    stop-color="#3f4043"/>
    <stop offset="0.20" stop-color="#38393c"/>
    <stop offset="0.58" stop-color="#2a2c2e"/>
    <stop offset="1"    stop-color="#1e2022"/>
  </linearGradient>
  <radialGradient id="plateHi" cx="0.03" cy="0.55" r="0.46">
    <stop offset="0"   stop-color="#c0c0c4" stop-opacity="0.24"/>
    <stop offset="0.45" stop-color="#88888c" stop-opacity="0.07"/>
    <stop offset="1"   stop-color="#000000" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="plateTeal" cx="0.89" cy="0.74" r="0.38">
    <stop offset="0"   stop-color="#3fd6c8" stop-opacity="0.13"/>
    <stop offset="0.5" stop-color="#1f8f88" stop-opacity="0.05"/>
    <stop offset="1"   stop-color="#000000" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="plateTeal2" cx="0.52" cy="0.99" r="0.5">
    <stop offset="0"   stop-color="#3fd6c8" stop-opacity="0.07"/>
    <stop offset="1"   stop-color="#000000" stop-opacity="0"/>
  </radialGradient>

  <linearGradient id="wellG" x1="0" y1="0" x2="0.35" y2="1">
    <stop offset="0"   stop-color="#0c0e13"/>
    <stop offset="0.45" stop-color="#050709"/>
    <stop offset="1"   stop-color="#04070b"/>
  </linearGradient>

  <linearGradient id="faceG" x1="0.25" y1="0" x2="0.6" y2="1">
    <stop offset="0"    stop-color="#2c2e31"/>
    <stop offset="0.08" stop-color="#303235"/>
    <stop offset="0.45" stop-color="#35373a"/>
    <stop offset="1"    stop-color="#333537"/>
  </linearGradient>
  <radialGradient id="faceTeal" cx="1" cy="1" r="0.55">
    <stop offset="0"   stop-color="#5bded3" stop-opacity="0.22"/>
    <stop offset="0.5" stop-color="#2a8d86" stop-opacity="0.07"/>
    <stop offset="1"   stop-color="#000000" stop-opacity="0"/>
  </radialGradient>

  <linearGradient id="tubeBot" x1="130" y1="0" x2="312" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0"    stop-color="#2fa39b" stop-opacity="0"/>
    <stop offset="0.22" stop-color="#3fb8b4" stop-opacity="0.35"/>
    <stop offset="0.52" stop-color="#38bcc4" stop-opacity="0.95"/>
    <stop offset="0.75" stop-color="#55cfd2" stop-opacity="1"/>
    <stop offset="1"    stop-color="#66e2e0" stop-opacity="1"/>
  </linearGradient>
  <linearGradient id="tubeBot2" x1="150" y1="0" x2="330" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0"    stop-color="#2b9a96" stop-opacity="0"/>
    <stop offset="0.3"  stop-color="#3ab4b8" stop-opacity="0.55"/>
    <stop offset="0.7"  stop-color="#4fcfd2" stop-opacity="0.85"/>
    <stop offset="1"    stop-color="#5cdfe0" stop-opacity="0.95"/>
  </linearGradient>
  <linearGradient id="tubeRight" x1="0" y1="246" x2="0" y2="104" gradientUnits="userSpaceOnUse">
    <stop offset="0"    stop-color="#66e2e0" stop-opacity="1"/>
    <stop offset="0.30" stop-color="#49c8c9" stop-opacity="0.90"/>
    <stop offset="0.60" stop-color="#44bcb8" stop-opacity="0.44"/>
    <stop offset="0.86" stop-color="#2a9c98" stop-opacity="0.10"/>
    <stop offset="1"    stop-color="#1d807c" stop-opacity="0"/>
  </linearGradient>
  <linearGradient id="glowBot" x1="126" y1="0" x2="322" y2="0" gradientUnits="userSpaceOnUse">
    <stop offset="0"    stop-color="#2fa79f" stop-opacity="0"/>
    <stop offset="0.22" stop-color="#37b5af" stop-opacity="0.28"/>
    <stop offset="0.62" stop-color="#4fcfc9" stop-opacity="0.55"/>
    <stop offset="1"    stop-color="#63e2da" stop-opacity="0.70"/>
  </linearGradient>
  <linearGradient id="glowRight" x1="0" y1="254" x2="0" y2="100" gradientUnits="userSpaceOnUse">
    <stop offset="0"    stop-color="#63e2da" stop-opacity="0.70"/>
    <stop offset="0.35" stop-color="#46c6c0" stop-opacity="0.40"/>
    <stop offset="0.7"  stop-color="#2ba49e" stop-opacity="0.13"/>
    <stop offset="1"    stop-color="#1b7b77" stop-opacity="0"/>
  </linearGradient>
  <radialGradient id="bloomG" cx="0.5" cy="0.5" r="0.5">
    <stop offset="0"    stop-color="#63e8e0" stop-opacity="0.42"/>
    <stop offset="0.45" stop-color="#2fa8a2" stop-opacity="0.16"/>
    <stop offset="1"    stop-color="#17706c" stop-opacity="0"/>
  </radialGradient>

  <filter id="b1"  x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="0.55"/></filter>
  <filter id="b2"  x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="1.8"/></filter>
  <filter id="b3"  x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="b5"  x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="5"/></filter>
  <filter id="b8"  x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="8"/></filter>
  <filter id="b12" x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="12"/></filter>

  <filter id="t1" filterUnits="userSpaceOnUse" x="0" y="0" width="438" height="393"><feGaussianBlur stdDeviation="0.55"/></filter>
  <filter id="t3" filterUnits="userSpaceOnUse" x="0" y="0" width="438" height="393"><feGaussianBlur stdDeviation="3"/></filter>
  <filter id="t5" filterUnits="userSpaceOnUse" x="0" y="0" width="438" height="393"><feGaussianBlur stdDeviation="5"/></filter>
  <path id="platePath" d="{PLATE_PATH}"/>
  <path id="wellPath" d="{well_path()}"/>
  <path id="facePath" d="{face_path()}"/>
</defs>

<rect width="{W}" height="{H}" fill="#17181f"/>
<rect width="{W}" height="{H}" fill="url(#bgAmb)"/>

<!-- contact shadow under plate -->
<use href="#platePath" fill="none" stroke="#000000" stroke-width="26" opacity="0.55" filter="url(#b12)" transform="translate(2,10)"/>
<use href="#platePath" fill="none" stroke="#000000" stroke-width="10" opacity="0.85" filter="url(#b5)" transform="translate(1,5)"/>
<use href="#platePath" fill="#000000" opacity="0.55" filter="url(#b8)" transform="translate(0,7)"/>

<!-- plate -->
<use href="#platePath" fill="url(#plateG)"/>
<use href="#platePath" fill="url(#plateHi)"/>
<use href="#platePath" fill="url(#plateTeal)"/>
<use href="#platePath" fill="url(#plateTeal2)"/>
<use href="#platePath" fill="none" stroke="#000000" stroke-opacity="0.40" stroke-width="1.6"/>

<!-- well -->
<use href="#wellPath" fill="url(#wellG)"/>

<!-- neon tube -->
<g stroke-linecap="butt">
  <path d="{echo_a}" fill="none" stroke="url(#glowBot)"   stroke-width="9" opacity="0.55" filter="url(#t5)"/>
  <path d="{echo_b}" fill="none" stroke="url(#glowRight)" stroke-width="9" opacity="0.55" filter="url(#b5)"/>
  <path d="{halo_a}" fill="none" stroke="url(#glowBot)"   stroke-width="8" opacity="0.75" filter="url(#t3)"/>
  <path d="{halo_b}" fill="none" stroke="url(#glowRight)" stroke-width="8" opacity="0.75" filter="url(#b3)"/>
  <path d="M140,309 H317 A49,49 0 0 0 366,260 V250" fill="none" stroke="url(#tubeBot2)" stroke-width="3.6" filter="url(#t1)"/>
  <path d="{core_a}" fill="none" stroke="url(#tubeBot)"   stroke-width="4.6" filter="url(#t1)"/>
  <path d="{core_b}" fill="none" stroke="url(#tubeRight)" stroke-width="4.6" filter="url(#t1)"/>
</g>

<!-- face -->
<use href="#facePath" fill="url(#faceG)"/>
<use href="#facePath" fill="url(#faceTeal)"/>
<path d="{rim_path()}" fill="none" stroke="#ffffff" stroke-opacity="0.22" stroke-width="3.2" filter="url(#b3)"/>
<path d="{rim_path()}" fill="none" stroke="#ffffff" stroke-opacity="1" stroke-width="1.8" filter="url(#b1)"/>

<!-- soft bloom over face bottom-right -->
<ellipse cx="338" cy="292" rx="80" ry="56" fill="url(#bloomG)" opacity="0.5" filter="url(#b8)"/>

<!-- icon -->
<g fill="#e9ede6" opacity="0.16" filter="url(#b2)">{dots(1.5)}</g>
<g fill="#eff1eb" filter="url(#b1)">{dots()}</g>
</svg>
</body></html>
"""

with open('candidate.html', 'w') as f:
    f.write(html)
print("wrote candidate.html", len(html), "bytes")
