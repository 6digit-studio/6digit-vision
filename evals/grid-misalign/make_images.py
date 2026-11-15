"""Build defect.png + control.png for evals/grid-misalign.

Mock "Members" admin page: app bar, a column-header strip, and six
member cards in a single column. Every card should share the same left
edge, the same right edge, the same height, uniform gaps, and the same
interior column positions (avatar / name+email / role / status pill /
overflow dots). Nothing overflows, nothing overlaps — the only crime is
that the spacing is a few pixels wrong, over and over.

THE DEFECT (defect.png): the per-row values an agent ships when it
hardcodes margins instead of using a spacing scale —

- inter-card gaps:        17, 9, 15, 11, 14   (control: 12 x5)
- header->card1 gap:      21                  (control: 16)
- card right edges:       header -4, cards 3&6 -6   (control: all flush)
- interior drift per row: avatar/name/role/pill/dots each off by 1-6px,
                          in varying directions, plus 1-2px vertical
                          baseline wobble on name/role text
- header labels:          MEMBER +2, ROLE -3, STATUS -5 from their
                          data columns

control.png: the same scene on a strict grid — every value above at
the canonical position. Identical strings, colors, sizes, canvas.

Run from repo root:  uv run --with pillow python3 evals/grid-misalign/make_images.py
"""

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent

W, H = 1080, 640
PAGE = (238, 240, 245)
CARD = (255, 255, 255)
BORDER = (226, 229, 234)
INK = (31, 41, 55)
BODY = (75, 85, 99)
FAINT = (107, 114, 128)
BTN_BG = (243, 244, 246)
BLUE = (37, 99, 235)
WHITE = (255, 255, 255)

FONT_DIR = "/System/Library/Fonts/Supplemental"


def font(name: str, size: int):
    return ImageFont.truetype(f"{FONT_DIR}/{name}", size)


F_TITLE = font("Arial Bold.ttf", 22)
F_NAME = font("Arial Bold.ttf", 16)
F_EMAIL = font("Arial.ttf", 12)
F_ROLE = font("Arial.ttf", 14)
F_PILL = font("Arial Bold.ttf", 12)
F_HEAD = font("Arial Bold.ttf", 11)
F_AV = font("Arial Bold.ttf", 15)
F_BTN = font("Arial Bold.ttf", 14)

# ---- grid constants (the spacing scale the control obeys) ----
COL_X, COL_W = 48, 984
CARD_RIGHT = COL_X + COL_W                    # 1032
CARD_H = 64
CARD_R = 10
AV_X = 20                                     # avatar left, rel. card
TXT_X = 80                                    # name/email left
ROLE_X = 440                                  # role column left
DOTS_W = 32                                   # overflow "..." button
PAD_R = 20                                    # right padding
DOTS_X = COL_W - PAD_R - DOTS_W               # 932
PILL_RIGHT = DOTS_X - 12                      # pill right edge = 920

APPBAR_H = 60
HEAD_Y, HEAD_H = 76, 34                       # column-header strip
CARD_TOP0 = 126                               # first card top (gap 16)
GAP = 12                                      # uniform card gap

MEMBERS = [
    ("Ada Lovelace",       "ada@analytical.io",    "Engineering", "Active",  "AL", (100, 116, 139)),
    ("Grace Hopper",       "grace@navy.mil",       "Design",      "Invited", "GH", (13, 148, 136)),
    ("Alan Turing",        "alan@bletchley.dev",   "Engineering", "Active",  "AT", (180, 83, 9)),
    ("Katherine Johnson",  "kat@orbit.gov",        "Data",        "Active",  "KJ", (190, 24, 93)),
    ("Margaret Hamilton",  "marg@apollo.mit",      "Engineering", "Invited", "MH", (109, 40, 217)),
    ("Radia Perlman",      "radia@bridges.net",    "Data",        "Active",  "RP", (21, 128, 61)),
]
PILL_STYLE = {
    "Active":  ((220, 252, 231), (21, 128, 61)),
    "Invited": ((254, 243, 199), (146, 64, 14)),
}

# ---- defect deltas ----
# gaps[i] = space after card i (header->card1 handled separately)
DEF_GAPS = [17, 9, 15, 11, 14]          # control: [12]*5
DEF_HEAD_GAP = 21                        # control: 16
DEF_WIDTHS = [984, 984, 978, 984, 984, 978]   # control: all 984
DEF_HEAD_W = 980                         # control: 984

# per-row interior offsets: (av_dx, txt_dx, role_dx, pill_dr, dots_dx,
#                            av_dy, pill_dy, dots_dy, name_dy, role_dy)
ZERO = (0,) * 10
DEF_OFFSETS = [
    ZERO,                                            # row 1: on-grid anchor
    (3, 1, 0, -4, -3, 1, -2, 1, 0, 0),                # row 2
    (-2, -2, 5, 2, 0, -1, 1, -1, 0, 2),               # row 3
    (5, 3, -1, -6, 4, 0, -1, 2, 0, -1),               # row 4
    (-3, -1, 2, 3, -2, 2, 0, -2, -1, 1),              # row 5
    (2, 4, -4, -2, 1, -2, 2, 0, 0, -2),               # row 6
]
DEF_HEAD_LBL = {"member": 2, "role": -3, "status": -5}   # control: all 0


def rounded(d, box, radius, **kw):
    d.rounded_rectangle(box, radius=radius, **kw)


def draw_appbar(d):
    d.rectangle([0, 0, W, APPBAR_H], fill=CARD)
    d.line([0, APPBAR_H, W, APPBAR_H], fill=BORDER, width=1)
    d.text((48, 19), "Members", font=F_TITLE, fill=INK)
    # "Invite member" button, right side of content column
    label = "Invite member"
    lw = d.textlength(label, font=F_BTN)
    bw, bh = lw + 36, 36
    bx0 = COL_X + COL_W - PAD_R - bw
    by0 = 12
    rounded(d, (bx0, by0, bx0 + bw, by0 + bh), 9, fill=BLUE)
    d.text((bx0 + 18, by0 + (bh - 19) / 2), label, font=F_BTN,
           fill=WHITE)
    # small admin avatar left of the button
    ax = bx0 - 14 - 34
    d.ellipse([ax, 13, ax + 34, 47], fill=(203, 213, 225),
              outline=BORDER)
    d.text((ax + 10, 18), "AK", font=F_PILL, fill=FAINT)


def draw_header(d, width, lbl_off):
    "Column-header strip: labels sit on the same columns as the data."
    x1 = COL_X + width
    rounded(d, (COL_X, HEAD_Y, x1, HEAD_Y + HEAD_H), 8,
            fill=CARD, outline=BORDER, width=1)
    ty = HEAD_Y + (HEAD_H - 13) / 2

    def right_aligned(text, right_edge):
        tw = d.textlength(text, font=F_HEAD)
        d.text((right_edge - tw, ty), text, font=F_HEAD, fill=FAINT)

    d.text((COL_X + TXT_X + lbl_off["member"], ty), "MEMBER",
           font=F_HEAD, fill=FAINT)
    d.text((COL_X + ROLE_X + lbl_off["role"], ty), "ROLE",
           font=F_HEAD, fill=FAINT)
    right_aligned("STATUS", COL_X + PILL_RIGHT + lbl_off["status"])


def draw_card(d, idx, top, width, off):
    "One member card. `off` is the 10-tuple of pixel deltas."""
    (av_dx, txt_dx, role_dx, pill_dr, dots_dx,
     av_dy, pill_dy, dots_dy, name_dy, role_dy) = off
    x0, y0 = COL_X, top
    x1, y1 = x0 + width, y0 + CARD_H
    rounded(d, (x0, y0, x1, y1), CARD_R, fill=CARD, outline=BORDER,
            width=1)
    name, email, role, status, ini, acol = MEMBERS[idx]

    # avatar circle + initials
    ax = x0 + AV_X + av_dx
    ay = y0 + 10 + av_dy
    d.ellipse([ax, ay, ax + 44, ay + 44], fill=acol)
    tw = d.textlength(ini, font=F_AV)
    d.text((ax + 22 - tw / 2, ay + 22 - 10), ini, font=F_AV,
           fill=WHITE)

    # name over email — shared text column
    tx = x0 + TXT_X + txt_dx
    d.text((tx, y0 + 15 + name_dy), name, font=F_NAME, fill=INK)
    d.text((tx, y0 + 37), email, font=F_EMAIL, fill=FAINT)

    # role column
    rx = x0 + ROLE_X + role_dx
    d.text((rx, y0 + 25 + role_dy), role, font=F_ROLE, fill=BODY)

    # status pill — right edge anchored to the pill column
    tw = d.textlength(status, font=F_PILL)
    pw = tw + 22
    py = y0 + 20 + pill_dy
    pill_right = x0 + PILL_RIGHT + pill_dr
    px0 = pill_right - pw
    bgc, fgc = PILL_STYLE[status]
    rounded(d, (px0, py, pill_right, py + 24), 12, fill=bgc)
    d.text((px0 + 11, py + 6), status, font=F_PILL, fill=fgc)

    # "..." overflow button — right edge anchored to card padding
    dx0 = x0 + DOTS_X + dots_dx
    dy0 = y0 + 16 + dots_dy
    rounded(d, (dx0, dy0, dx0 + DOTS_W, dy0 + DOTS_W), 9,
            fill=BTN_BG, outline=BORDER, width=1)
    cx, cy = dx0 + DOTS_W / 2, dy0 + DOTS_W / 2
    for ddx in (-8, 0, 8):
        d.ellipse([cx + ddx - 2.3, cy - 2.3, cx + ddx + 2.3,
                   cy + 2.3], fill=FAINT)


def card_tops(gaps, first_gap):
    "6 card tops: first below the header strip, then CARD_H+gap apart."""
    tops = [HEAD_Y + HEAD_H + first_gap]
    for g in gaps:
        tops.append(tops[-1] + CARD_H + g)
    return tops


def render(defect: bool) -> Image.Image:
    img = Image.new("RGB", (W, H), PAGE)
    d = ImageDraw.Draw(img)
    draw_appbar(d)

    gaps = DEF_GAPS if defect else [GAP] * 5
    first_gap = DEF_HEAD_GAP if defect else CARD_TOP0 - (HEAD_Y + HEAD_H)
    widths = DEF_WIDTHS if defect else [COL_W] * 6
    head_w = DEF_HEAD_W if defect else COL_W
    head_lbl = DEF_HEAD_LBL if defect else {"member": 0, "role": 0,
                                            "status": 0}
    offs = DEF_OFFSETS if defect else [ZERO] * 6

    draw_header(d, head_w, head_lbl)
    for i in range(6):
        draw_card(d, i, card_tops(gaps, first_gap)[i], widths[i], offs[i])
    return img


def main() -> None:
    control = render(defect=False)
    defect = render(defect=True)
    control.save(HERE / "control.png")
    defect.save(HERE / "defect.png")

    # ---- self-checks: prove identical content, measure the drift ----
    diff = ImageChops.difference(control, defect)
    bbox = diff.getbbox()
    ndiff = sum(1 for p in diff.getdata() if p != (0, 0, 0))
    print(f"diff bbox={bbox}  changed_px={ndiff} "
          f"({ndiff / (W * H) * 100:.2f}%)")

    tops_c = card_tops([GAP] * 5, CARD_TOP0 - (HEAD_Y + HEAD_H))
    tops_d = card_tops(DEF_GAPS, DEF_HEAD_GAP)
    print("control card tops:", tops_c, " gaps:", [GAP] * 5)
    print("defect  card tops:", tops_d,
          " gaps:", [tops_d[i + 1] - tops_d[i] - CARD_H for i in range(5)])
    print("defect right edges:", [COL_X + w for w in DEF_WIDTHS],
          " header:", COL_X + DEF_HEAD_W)
    print("wrote control.png and defect.png")


if __name__ == "__main__":
    main()
