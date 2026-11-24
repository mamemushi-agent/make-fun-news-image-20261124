#!/usr/bin/env python3
"""Deterministically generate entry.png (v2): 24 November 2026 world news.

Pure Python 3 standard library only. No network, no randomness, no clock.
Text is drawn with a small 5x7 bitmap font defined below (ASCII only).
40 stories: 6 fuller top stories + 34 compact one-line items in 7 regional
sections. All items are from named sources dated 24 Nov 2026 (see REPORT.md).
Run:  python3 main.py   -> writes ./entry.png in the current working folder.
"""
import struct
import zlib

W = 1024
H = 1024

PAPER = (247, 243, 232)
INK = (22, 22, 22)
GREY = (90, 90, 90)
WHITE = (255, 255, 255)
RED = (176, 32, 40)
DARK = (45, 45, 45)

# ---------------------------------------------------------------- font (5x7)
# Each glyph: 7 strings of 5 chars, '#' = on. (Same font as v1, our own code.)
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", ".#.#.", "..#..", "..#..", "..#..", ".#.#.", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "#.#.#", "##..#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "2": (".###.", "#...#", "....#", "..##.", ".#...", "#....", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "..#..", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", ".##..", ".##..", ".#..."),
    "'": (".##..", ".##..", ".#...", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", "#####", ".....", ".....", "....."),
    ":": (".....", ".##..", ".##..", ".....", ".##..", ".##..", "....."),
    "$": (".####", "#.#..", "#.#..", ".###.", "..#.#", "..#.#", "####."),
    "%": ("##..#", "##.#.", "....#", "...#.", "..#..", ".#...", "#..##"),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
}

# ---------------------------------------------------------------- canvas
buf = bytearray(W * H * 3)


def fill_rect(x, y, w, h, color):
    r, g, b = color
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            buf[i] = r
            buf[i + 1] = g
            buf[i + 2] = b


def text_width(text, scale):
    return len(text) * 6 * scale - scale if text else 0


def draw_text(x, y, text, scale, color):
    for ch in text:
        glyph = FONT[ch]
        for row in range(7):
            line = glyph[row]
            for col in range(5):
                if line[col] == "#":
                    fill_rect(x + col * scale, y + row * scale, scale, scale, color)
        x += 6 * scale
    return x


def draw_text_bold1(x, y, text, color):
    """Scale-1 text with a 1px horizontal double-strike for legibility."""
    for ch in text:
        glyph = FONT[ch]
        for row in range(7):
            line = glyph[row]
            for col in range(5):
                if line[col] == "#":
                    fill_rect(x + col, y + row, 2, 1, color)
        x += 6
    return x


def draw_centered(cx, y, text, scale, color):
    draw_text(cx - text_width(text, scale) // 2, y, text, scale, color)


def wrap(text, max_chars):
    lines = []
    cur = ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if len(trial) <= max_chars:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- content
# Top stories: the six verified Reuters items from v1 (see v1 REPORT.md).
TOP = [
    (
        "CHINA - POLITICS", (176, 32, 40),
        "CHINA PROBES POLITBURO MEMBER CHEN JINING",
        "XINHUA SAID SHANGHAI PARTY CHIEF CHEN IS UNDER INVESTIGATION, "
        "THE 4TH TOP LEADER PROBED SINCE 2025.",
    ),
    (
        "TECH - MARKETS", (23, 64, 140),
        "NVIDIA SHARES JUMP AS HUANG RETURNS AS CEO",
        "NVIDIA REINSTATED JENSEN HUANG AS CHIEF EXECUTIVE. ITS SHARES "
        "SURGED OVER 31 PCT AS AI STOCKS RALLIED.",
    ),
    (
        "EUROPE - PHARMA", (96, 48, 140),
        "SANOFI TO BUY INSMED FOR $41 BILLION",
        "FRANCE'S SANOFI WILL PAY $175 A SHARE IN CASH FOR THE US "
        "DRUGMAKER, A PREMIUM OF 46 PCT.",
    ),
    (
        "JAPAN - ECONOMY", (0, 105, 105),
        "JAPAN FACTORY ACTIVITY GROWS IN NOVEMBER",
        "THE FLASH MANUFACTURING PMI ROSE TO 53.7 FROM 53.3 ON CHIP "
        "AND ELECTRONICS DEMAND.",
    ),
    (
        "MIDEAST - DIPLOMACY", (150, 100, 20),
        "US ENVOY DOUBTS ISRAEL AID WILL END THIS YEAR",
        "AMBASSADOR HUCKABEE QUESTIONED A PROMISE TO END $3.8 BILLION "
        "IN YEARLY US MILITARY AID.",
    ),
    (
        "SOUTH ASIA - LABOUR", (30, 115, 60),
        "GARMENT WORKERS CLASH WITH POLICE OVER PAY",
        "BANGLADESH PROTESTS SHUT DOZENS OF FACTORIES AS POLICE FIRED "
        "TEAR GAS IN AN INDUSTRIAL BELT.",
    ),
]

# Compact one-line items by region. All Reuters, 24 Nov 2026 (see REPORT.md).
SECTIONS = [
    ("ASIA-PACIFIC", (0, 105, 105), [
        "US BLACKLISTS SINGAPORE FIRM MEGASPEED OVER CHIPS",
        "MALAYSIA PLANS CARBON HUBS, $40 BLN BY 2050",
        "INDIA TEEN, 15, SMASHES 204 OFF 53 BALLS",
        "AIRLINES RETHINK JET FINANCING AS FUEL COSTS BITE",
    ]),
    ("NORTH AMERICA", (23, 64, 140), [
        "US SET TO UNVEIL NEW TARIFFS AFTER CAPACITY PROBE",
        "US CONSUMER CONFIDENCE JUMPS TO 103.3, 2-YEAR HIGH",
        "SCHUMER ACCUSES NVIDIA CEO OF EXPORT-LAW BREACH",
        "US BIRD FLU: 3 CASES, 1 DEATH IN WASHINGTON",
        "IMMIGRANTS SUE TO BLOCK MEDICAID CUTS",
        "CANADA COURTS MEMBERS FOR GLOBAL DEFENCE BANK",
    ]),
    ("EUROPE", (96, 48, 140), [
        "PUTIN VOWS REPLY TO UKRAINE HITS ON OIL PLANTS",
        "EU LEANS TO INCLUDE UK EVS IN MADE-IN-EUROPE PLAN",
        "GERMAN MILITARY SATELLITE PLAN TO COST 15 BLN EUROS",
        "GERMAN IFO BUSINESS MORALE RISES TO 90.6",
        "UK HEAT DEATHS HIT RECORD 5,258 IN 2026",
        "NORWAY, UKRAINE EXPAND ANTI-DRONE COOPERATION",
    ]),
    ("MIDDLE EAST", (150, 100, 20), [
        "ISRAEL: EISENKOT SIGNS FIRST COALITION PACT",
        "HOUTHIS NEAR ADEN, ARMY SAYS CITY WILL NOT FALL",
        "ISRAELI STRIKE KILLS HAMAS SECURITY CHIEF IN GAZA",
        "SAUDI 2027 BUDGET SEES 190 BLN RIYAL DEFICIT",
        "IRAQ PM ORDERS TAKEOVER OF KURD OIL, CROSSINGS",
    ]),
    ("AFRICA", (30, 115, 60), [
        "NIGERIA: TINUBU ASKS TO TRIM 2026 BUDGET",
        "NIGERIA CENTRAL BANK HOLDS KEY RATE AT 23 PCT",
        "CONGO MINING FORUM UNVEILS $965 MLN FINANCING",
        "175 MIGRANTS MISSING AFTER SENEGAL BOAT VANISHES",
        "SENEGAL RESTORED AS AFCON CHAMPIONS BY CAS",
    ]),
    ("LATIN AMERICA", (176, 32, 40), [
        "BRAZIL LOWER HOUSE PASSES FISCAL PACKAGE",
        "MEXICO INFLATION AT 3.96 PCT, SIX-MONTH HIGH",
        "ARGENTINA ACTIVITY FALLS 1.2 PCT IN SEPTEMBER",
        "BRAZIL TAX TAKE HITS RECORD 294 BLN REAIS",
        "RARE SPIX'S MACAW CHICK HATCHES AT SAO PAULO ZOO",
    ]),
    ("GLOBAL - SCIENCE, CLIMATE, SPORT", (70, 70, 70), [
        "OLDEST QUASAR SPOTTED, 13.1 BLN YEARS OLD",
        "COP31 CLIMATE TALKS END WITHOUT A DEAL",
        "DAVIS CUP: CZECHS LEAD CANADA IN QUARTERS",
    ]),
]

LEFT = 24
RIGHT = W - 24
COLW = (RIGHT - LEFT - 16) // 2  # compact column width


def check_content():
    texts = ["THE WORLD IN ONE IMAGE", "24 NOVEMBER 2026",
             "TUESDAY - 40 STORIES FROM AROUND THE GLOBE", "TOP STORIES",
             "ALL ITEMS FROM REUTERS, 24 NOV 2026"]
    for tag, _c, head, body in TOP:
        texts += [tag, head, body]
        if len(wrap(head, 38)) > 2:
            raise ValueError("top headline too long: " + head)
        if len(wrap(body, 76)) > 3:
            raise ValueError("top body too long: " + head)
    for name, _c, items in SECTIONS:
        texts.append(name)
        for it in items:
            texts.append(it)
            if text_width(it, 1) > COLW - 14:
                raise ValueError("compact item too wide: " + it)
    for t in texts:
        for ch in t:
            if ch not in FONT:
                raise ValueError("missing glyph: %r" % ch)


def main():
    check_content()
    fill_rect(0, 0, W, H, PAPER)

    # outer frame
    fill_rect(10, 10, W - 20, 4, INK)
    fill_rect(10, H - 14, W - 20, 4, INK)
    fill_rect(10, 10, 4, H - 20, INK)
    fill_rect(W - 14, 10, 4, H - 20, INK)

    # masthead
    draw_centered(W // 2, 24, "THE WORLD IN ONE IMAGE", 4, INK)
    fill_rect(40, 60, W - 80, 3, INK)
    draw_centered(W // 2, 72, "24 NOVEMBER 2026", 7, RED)
    draw_centered(W // 2, 132, "TUESDAY - 40 STORIES FROM AROUND THE GLOBE", 2, GREY)
    fill_rect(40, 154, W - 80, 5, INK)

    # ---- top stories ----
    y = 166
    fill_rect(LEFT, y, RIGHT - LEFT, 20, INK)
    draw_text(LEFT + 10, y + 3, "TOP STORIES", 2, WHITE)
    y += 28
    gap = 10
    cell_w = (RIGHT - LEFT - gap) // 2
    cell_h = 80
    for idx, (tag, color, head, body) in enumerate(TOP):
        cx = LEFT + (idx % 2) * (cell_w + gap)
        cy = y + (idx // 2) * (cell_h + 8)
        fill_rect(cx, cy, cell_w, cell_h, WHITE)
        fill_rect(cx, cy, cell_w, 2, INK)
        fill_rect(cx, cy + cell_h - 2, cell_w, 2, INK)
        fill_rect(cx, cy, 2, cell_h, INK)
        fill_rect(cx + cell_w - 2, cy, 2, cell_h, INK)
        fill_rect(cx + 2, cy + 2, cell_w - 4, 15, color)
        draw_text(cx + 10, cy + 6, tag, 1, WHITE)
        yy = cy + 22
        for line in wrap(head, 38):
            draw_text(cx + 10, yy, line, 2, INK)
            yy += 16
        yy += 2
        for line in wrap(body, 76):
            draw_text(cx + 10, yy, line, 1, DARK)
            yy += 9
    y += 3 * cell_h + 2 * 8 + 10

    # ---- compact regional sections ----
    for name, color, items in SECTIONS:
        fill_rect(LEFT, y, RIGHT - LEFT, 20, color)
        draw_text(LEFT + 10, y + 3, name, 2, WHITE)
        y += 26
        rows = (len(items) + 1) // 2
        for r in range(rows):
            for c in range(2):
                i = r * 2 + c
                if i >= len(items):
                    break
                ix = LEFT + c * (COLW + 16)
                fill_rect(ix + 1, y + 2, 4, 4, color)
                draw_text_bold1(ix + 12, y, items[i], INK)
            y += 13
        y += 8

    # footer
    fill_rect(40, y + 2, W - 80, 3, INK)
    draw_centered(W // 2, y + 12, "ALL ITEMS FROM REUTERS, 24 NOV 2026", 2, GREY)
    if y + 30 > H - 20:
        raise ValueError("layout overflow: footer at %d" % y)

    # ---- encode PNG (filter 0 per scanline, zlib) ----
    raw = bytearray()
    row_bytes = W * 3
    for yy in range(H):
        raw.append(0)
        raw += buf[yy * row_bytes:(yy + 1) * row_bytes]

    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        return out

    png = bytearray()
    png += b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")

    with open("entry.png", "wb") as f:
        f.write(png)


if __name__ == "__main__":
    main()
