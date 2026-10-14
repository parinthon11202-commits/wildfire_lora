"""Render an editable draw.io Gateway flowchart and a thesis-ready PNG."""

from __future__ import annotations

from math import atan2, cos, pi, sin
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "figures"
STEM = "figure-3-7-gateway-data-flow"
W, H, SCALE = 1800, 2420, 2
INK = "#202124"
FONT = r"C:\Windows\Fonts\tahoma.ttf"
BOLD = r"C:\Windows\Fonts\tahomabd.ttf"

img = Image.new("RGB", (W * SCALE, H * SCALE), "white")
draw = ImageDraw.Draw(img)
regular = ImageFont.truetype(FONT, 32 * SCALE)
small = ImageFont.truetype(FONT, 27 * SCALE)
bold = ImageFont.truetype(BOLD, 34 * SCALE)
caption = ImageFont.truetype(FONT, 30 * SCALE)

# Coordinates are in the unscaled page space. Shapes follow the monochrome
# academic style of the Sensor Node decision flowchart.
nodes = [
    ("start", "ellipse", 900, 75, 200, 70, ["เริ่มต้น"]),
    ("setup", "rect", 900, 220, 760, 115,
     ["เริ่ม LoRa และ Wi-Fi"]),
    ("receive", "diamond", 900, 425, 590, 160,
     ["ได้รับแพ็กเก็ต", "ผ่าน LoRa หรือไม่?"]),
    ("read", "rect", 900, 630, 760, 120,
     ["อ่านข้อความและอ่าน RSSI/SNR", "จากวิทยุ LoRa"]),
    ("poll", "rect", 1535, 630, 460, 125,
     ["networkTask ดึงคำสั่งค้าง", "จาก Backend ทุก 30 วินาที"]),
    ("cmd", "diamond", 900, 850, 590, 170,
     ["ชนิดแพ็กเก็ต", "เป็น cmd_ack หรือไม่?"]),
    ("cmd_report", "rect", 275, 1040, 480, 135,
     ["ตรวจคำสั่งที่รอ", "ถ้าตรงกัน นำผลเข้าคิวรายงาน"]),
    ("cmd_return", "ellipse", 275, 1170, 82, 82, ["R"]),
    ("sensor", "diamond", 900, 1110, 590, 170,
     ["ชนิดแพ็กเก็ต", "เป็นข้อมูลเซนเซอร์ (s) หรือไม่?"]),
    ("ack", "rect", 1510, 1290, 490, 125,
     ["ส่ง rx_ack ให้ Sensor Node", "ยืนยันว่ารับผ่าน LoRa แล้ว"]),
    ("augment", "rect", 900, 1465, 780, 130,
     ["เพิ่ม RSSI/SNR ลงใน JSON", "และส่งคำสั่ง GPS ที่ค้างอยู่ (ถ้ามี)"]),
    ("queue", "rect", 900, 1660, 750, 115,
     ["นำแพ็กเก็ตเข้าคิวส่ง Backend", "แล้ววนกลับไปรับ LoRa ต่อ"]),
    ("queued", "diamond", 900, 1850, 590, 160,
     ["เข้าคิว HTTP", "ได้สำเร็จหรือไม่?"]),
    ("drop", "rect", 285, 2040, 480, 115,
     ["คิวเต็ม/ไม่พร้อม", "บันทึกข้อความว่าแพ็กเก็ตถูกทิ้ง"]),
    ("drop_return", "ellipse", 285, 2150, 82, 82, ["R"]),
    ("return", "ellipse", 900, 2040, 82, 82, ["R"]),
    ("network", "rect", 1510, 1820, 490, 145,
     ["networkTask อ่านข้อมูลจากคิว", "แล้ว HTTPS POST ไป Backend"]),
]

def px(v):
    return round(v * SCALE)


def centered(lines, cx, cy, font=regular, spacing=7):
    bounds = [draw.textbbox((0, 0), line, font=font) for line in lines]
    heights = [b[3] - b[1] for b in bounds]
    total = sum(heights) + spacing * SCALE * (len(lines) - 1)
    yy = px(cy) - total / 2
    for line, b, height in zip(lines, bounds, heights):
        draw.text((px(cx) - (b[2] - b[0]) / 2, yy - b[1]), line, font=font, fill=INK)
        yy += height + spacing * SCALE


def arrow(points, label=None, label_at=None, dashed=False):
    xy = [(px(x), px(y)) for x, y in points]
    if dashed:
        for p, q in zip(xy, xy[1:]):
            length = ((q[0]-p[0])**2 + (q[1]-p[1])**2)**0.5
            if not length:
                continue
            for off in range(0, int(length), 22 * SCALE):
                a, b = off / length, min(off + 12 * SCALE, length) / length
                draw.line(((p[0]+(q[0]-p[0])*a, p[1]+(q[1]-p[1])*a),
                           (p[0]+(q[0]-p[0])*b, p[1]+(q[1]-p[1])*b)), fill=INK, width=3 * SCALE)
    else:
        draw.line(xy, fill=INK, width=3 * SCALE, joint="curve")
    (x1, y1), (x2, y2) = points[-2:]
    angle = atan2(y2-y1, x2-x1)
    tip = (px(x2), px(y2))
    length, spread = 16, pi / 7
    wings = [(px(x2-length*cos(angle-sign*spread)), px(y2-length*sin(angle-sign*spread)))
             for sign in (-1, 1)]
    draw.polygon([tip, *wings], fill=INK)
    if label and label_at:
        draw.text((px(label_at[0]), px(label_at[1])), label, font=small, fill=INK)


edges = [
    ("start", "setup", [(900, 110), (900, 162)], None, None, False),
    ("setup", "receive", [(900, 278), (900, 345)], None, None, False),
    ("setup", "poll", [(1280, 220), (1535, 220), (1535, 568)], None, None, True),
    ("receive", "receive", [(1195, 425), (1290, 425), (1290, 330), (900, 330), (900, 345)], "ไม่", (1215, 375), False),
    ("receive", "read", [(900, 505), (900, 570)], "ใช่", (920, 515), False),
    ("read", "cmd", [(900, 690), (900, 765)], None, None, False),
    ("cmd", "cmd_report", [(605, 850), (275, 850), (275, 972)], "ใช่", (500, 808), False),
    ("cmd_report", "cmd_return", [(275, 1108), (275, 1129)], None, None, False),
    ("cmd", "sensor", [(900, 935), (900, 1025)], "ไม่ใช่", (920, 960), False),
    ("sensor", "ack", [(1195, 1110), (1510, 1110), (1510, 1228)], "ใช่", (1240, 1068), False),
    ("sensor", "augment", [(900, 1195), (900, 1400)], "ไม่ใช่", (920, 1210), False),
    ("ack", "augment", [(1510, 1353), (1510, 1390), (1290, 1390), (1290, 1465)], None, None, False),
    ("augment", "queue", [(900, 1530), (900, 1603)], None, None, False),
    ("queue", "queued", [(900, 1718), (900, 1770)], None, None, False),
    ("queued", "network", [(1195, 1850), (1265, 1850)], None, None, True),
    ("queued", "drop", [(605, 1850), (285, 1850), (285, 1983)], "ไม่", (520, 1805), False),
    ("drop", "drop_return", [(285, 2098), (285, 2109)], None, None, False),
    ("queued", "return", [(900, 1930), (900, 1999)], "ใช่", (920, 1940), False),
]

for _, _, points, label, label_at, dashed in edges:
    arrow(points, label, label_at, dashed)

for ident, kind, cx, cy, width, height, lines in nodes:
    x1, y1, x2, y2 = map(px, (cx-width/2, cy-height/2, cx+width/2, cy+height/2))
    if kind == "ellipse":
        draw.ellipse((x1, y1, x2, y2), fill="white", outline=INK, width=3*SCALE)
    elif kind == "diamond":
        vertices = [(px(cx), y1), (x2, px(cy)), (px(cx), y2), (x1, px(cy))]
        draw.polygon(vertices, fill="white", outline=INK)
        draw.line(vertices + [vertices[0]], fill=INK, width=3*SCALE)
    else:
        draw.rectangle((x1, y1, x2, y2), fill="white", outline=INK, width=3*SCALE)
    centered(lines, cx, cy, bold if ident == "start" else small if kind == "ellipse" or ident in ("cmd_report", "ack", "drop", "network", "poll") else regular)

draw.text((px(90), px(2220)),
          "R = วนกลับไปดูแล Wi-Fi/LoRa และรอรับแพ็กเก็ต • Gateway ทำงานต่อเนื่อง ไม่เข้า Deep Sleep",
          font=small, fill=INK)
draw.text((px(90), px(2265)),
          "rx_ack ยืนยันการรับทาง LoRa เท่านั้น; คิวเต็มหรือ POST ไม่สำเร็จอาจทำให้ข้อมูลไม่ถึง Backend",
          font=small, fill=INK)
centered(["ผังการรับและส่งต่อข้อมูลของ Gateway (ที่มา: ผู้จัดทำ)"], 900, 2350, caption)
OUT.mkdir(parents=True, exist_ok=True)
img.save(OUT / f"{STEM}.png", dpi=(220, 220))

mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "agent": "Codex"})
diagram = ET.SubElement(mxfile, "diagram", {"id": "gateway-data-flow", "name": "Gateway"})
model = ET.SubElement(diagram, "mxGraphModel", {"page": "1", "pageScale": "1",
                                               "pageWidth": str(W), "pageHeight": str(H), "grid": "1"})
root = ET.SubElement(model, "root")
ET.SubElement(root, "mxCell", {"id": "0"})
ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

for ident, kind, cx, cy, width, height, lines in nodes:
    style = "whiteSpace=wrap;html=1;strokeColor=#202124;fillColor=#ffffff;fontColor=#202124;fontFamily=Tahoma;fontSize=28;strokeWidth=2;"
    if kind == "ellipse":
        style = "ellipse;" + style
    elif kind == "diamond":
        style = "rhombus;" + style
    cell = ET.SubElement(root, "mxCell", {"id": ident, "value": "<br>".join(lines),
                                          "style": style, "vertex": "1", "parent": "1"})
    ET.SubElement(cell, "mxGeometry", {"x": str(cx-width/2), "y": str(cy-height/2),
                                       "width": str(width), "height": str(height), "as": "geometry"})

for n, (source, target, points, label, _, dashed) in enumerate(edges):
    style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;html=1;strokeColor=#202124;strokeWidth=2;endArrow=block;endFill=1;fontFamily=Tahoma;fontSize=24;"
    if dashed:
        style += "dashed=1;dashPattern=6 4;"
    cell = ET.SubElement(root, "mxCell", {"id": f"edge-{n}", "value": label or "", "style": style,
                                          "edge": "1", "parent": "1", "source": source, "target": target})
    geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    if len(points) > 2:
        waypoints = ET.SubElement(geom, "Array", {"as": "points"})
        for x, y in points[1:-1]:
            ET.SubElement(waypoints, "mxPoint", {"x": str(x), "y": str(y)})

note = ET.SubElement(root, "mxCell", {"id": "note", "value":
    "R = วนกลับไปดูแล Wi-Fi/LoRa และรอรับแพ็กเก็ต • Gateway ทำงานต่อเนื่อง ไม่เข้า Deep Sleep",
    "style": "text;html=1;whiteSpace=wrap;align=left;verticalAlign=middle;strokeColor=none;fillColor=none;fontFamily=Tahoma;fontSize=24;",
    "vertex": "1", "parent": "1"})
ET.SubElement(note, "mxGeometry", {"x": "90", "y": "2190", "width": "1600", "height": "65", "as": "geometry"})

delivery_note = ET.SubElement(root, "mxCell", {"id": "delivery_note", "value":
    "rx_ack ยืนยันการรับทาง LoRa เท่านั้น; คิวเต็มหรือ POST ไม่สำเร็จอาจทำให้ข้อมูลไม่ถึง Backend",
    "style": "text;html=1;whiteSpace=wrap;align=left;verticalAlign=middle;strokeColor=none;fillColor=none;fontFamily=Tahoma;fontSize=24;",
    "vertex": "1", "parent": "1"})
ET.SubElement(delivery_note, "mxGeometry", {"x": "90", "y": "2235", "width": "1600", "height": "65", "as": "geometry"})

figure_caption = ET.SubElement(root, "mxCell", {"id": "caption", "value":
    "ผังการรับและส่งต่อข้อมูลของ Gateway (ที่มา: ผู้จัดทำ)",
    "style": "text;html=1;whiteSpace=wrap;align=center;verticalAlign=middle;strokeColor=none;fillColor=none;fontFamily=Tahoma;fontSize=28;",
    "vertex": "1", "parent": "1"})
ET.SubElement(figure_caption, "mxGeometry", {"x": "250", "y": "2310", "width": "1300", "height": "80", "as": "geometry"})

ET.indent(mxfile)
ET.ElementTree(mxfile).write(OUT / f"{STEM}.drawio", encoding="utf-8", xml_declaration=True)
print(OUT / f"{STEM}.png")
print(OUT / f"{STEM}.drawio")
