"""Gateway flowchart checked against gateway/*.ino and gateway/*.h.

The solid path is the LoRa loop; dashed paths show the independent network
task.  Both the PNG and editable Draw.io document use the same node/edge data.
"""

from __future__ import annotations

from math import atan2, cos, pi, sin
from pathlib import Path
import xml.etree.ElementTree as ET

from PIL import Image, ImageDraw, ImageFont


BASE = Path(__file__).resolve().parents[1] / "docs" / "figures"
STEM = "figure-3-7-gateway-verified"
WIDTH, HEIGHT, SCALE = 2100, 2450, 2
INK = "#1d1d1d"
image = Image.new("RGB", (WIDTH * SCALE, HEIGHT * SCALE), "white")
canvas = ImageDraw.Draw(image)
font = ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", 31 * SCALE)
small = ImageFont.truetype(r"C:\Windows\Fonts\tahoma.ttf", 25 * SCALE)
title_font = ImageFont.truetype(r"C:\Windows\Fonts\tahomabd.ttf", 32 * SCALE)


def p(value):
    return round(value * SCALE)


def text_in(lines, x, y, chosen_font=font):
    measurements = [canvas.textbbox((0, 0), line, font=chosen_font) for line in lines]
    spacing = 7 * SCALE
    height = sum(box[3] - box[1] for box in measurements) + spacing * (len(lines) - 1)
    top = p(y) - height / 2
    for line, box in zip(lines, measurements):
        canvas.text((p(x) - (box[2] - box[0]) / 2, top - box[1]), line,
                    fill=INK, font=chosen_font)
        top += box[3] - box[1] + spacing


nodes = [
    ("start", "ellipse", 900, 75, 210, 70, ["เริ่มต้น"]),
    ("setup", "rect", 900, 215, 800, 115,
     ["เริ่ม LoRa และ Wi-Fi", "เริ่มงานส่งข้อมูลไป Backend เบื้องหลัง"]),
    ("poll", "rect", 1690, 215, 600, 120,
     ["งานเบื้องหลัง: ดึงคำสั่งค้าง", "จาก Backend ทุก 30 วินาที"]),
    ("listen", "diamond", 900, 420, 650, 150,
     ["มีแพ็กเก็ตเข้าทาง LoRa หรือไม่?"]),
    ("read", "rect", 900, 630, 780, 105,
     ["อ่านแพ็กเก็ตและค่า RSSI/SNR"]),
    ("cmd", "diamond", 900, 825, 650, 150,
     ["เป็นข้อความตอบรับคำสั่ง", "(cmd_ack) หรือไม่?"]),
    ("cmd_work", "rect", 300, 1040, 440, 150,
     ["ถ้าคำสั่งตรงกับที่รอ", "นำผลเข้าคิวรายงาน Backend", "ถ้าไม่ตรง ให้ละเลย"]),
    ("sensor", "diamond", 900, 1065, 650, 150,
     ["เป็นแพ็กเก็ตข้อมูลเซนเซอร์", "(ชนิด s) หรือไม่?"]),
    ("ack", "rect", 1690, 1270, 560, 130,
     ["พยายามส่ง rx_ack กลับโหนด", "ว่ารับผ่าน LoRa แล้ว"]),
    ("augment", "rect", 900, 1405, 820, 120,
     ["เพิ่ม RSSI/SNR ใน JSON", "ส่งคำสั่งที่รอของโหนด (ถ้ามี)"]),
    ("enqueue", "rect", 900, 1605, 760, 105,
     ["นำแพ็กเก็ตเข้าคิวส่ง Backend"]),
    ("queued", "diamond", 900, 1795, 650, 140,
     ["เข้าคิวสำเร็จหรือไม่?"]),
    ("dropped", "rect", 315, 2000, 500, 125,
     ["คิวไม่พร้อม/เต็ม: บันทึก Log", "แพ็กเก็ตนี้ถูกทิ้ง"]),
    ("http", "rect", 1690, 1795, 590, 170,
     ["งานเบื้องหลังหยิบจากคิว", "แล้วพยายาม HTTPS POST", "ถ้าไม่สำเร็จ บันทึก Log"]),
    ("return", "rect", 900, 2185, 680, 110,
     ["เปิดรับ LoRa ต่อ แล้ววนรอบใหม่"]),
]

# Each edge: source, target, polyline, branch label, label coordinate, dashed.
edges = [
    ("start", "setup", [(900, 110), (900, 158)], None, None, False),
    ("setup", "listen", [(900, 273), (900, 345)], None, None, False),
    ("setup", "poll", [(1300, 215), (1390, 215)], None, None, True),
    ("listen", "listen", [(1225, 420), (1330, 420), (1330, 310), (900, 310), (900, 345)], "ไม่", (1240, 375), False),
    ("listen", "read", [(900, 495), (900, 578)], "ใช่", (925, 515), False),
    ("read", "cmd", [(900, 683), (900, 750)], None, None, False),
    ("cmd", "cmd_work", [(575, 825), (300, 825), (300, 965)], "ใช่", (495, 780), False),
    ("cmd_work", "listen", [(300, 1115), (300, 1155), (55, 1155)], None, None, False),
    ("cmd", "sensor", [(900, 900), (900, 990)], "ไม่ใช่", (925, 925), False),
    ("sensor", "ack", [(1225, 1065), (1690, 1065), (1690, 1205)], "ใช่", (1250, 1020), False),
    ("sensor", "augment", [(900, 1140), (900, 1345)], "ไม่ใช่", (925, 1180), False),
    ("ack", "augment", [(1690, 1335), (1690, 1405), (1310, 1405)], None, None, False),
    ("augment", "enqueue", [(900, 1465), (900, 1553)], None, None, False),
    ("enqueue", "queued", [(900, 1658), (900, 1725)], None, None, False),
    ("queued", "dropped", [(575, 1795), (315, 1795), (315, 1938)], "ไม่", (490, 1745), False),
    ("queued", "return", [(900, 1865), (900, 2130)], "ใช่", (925, 1895), False),
    ("queued", "http", [(1225, 1795), (1395, 1795)], None, None, True),
    ("dropped", "return", [(315, 2063), (315, 2185), (560, 2185)], None, None, False),
    ("return", "listen", [(900, 2240), (900, 2285), (55, 2285), (55, 420), (575, 420)], None, None, False),
]


def line(points, label=None, label_xy=None, dashed=False, head=True):
    scaled = [(p(x), p(y)) for x, y in points]
    if dashed:
        for a, b in zip(scaled, scaled[1:]):
            distance = ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5
            for offset in range(0, int(distance), 25 * SCALE):
                t1 = offset / distance
                t2 = min(offset + 13 * SCALE, distance) / distance
                canvas.line(((a[0] + (b[0]-a[0])*t1, a[1] + (b[1]-a[1])*t1),
                             (a[0] + (b[0]-a[0])*t2, a[1] + (b[1]-a[1])*t2)),
                            fill=INK, width=3 * SCALE)
    else:
        canvas.line(scaled, fill=INK, width=3 * SCALE, joint="curve")
    if head:
        (x1, y1), (x2, y2) = points[-2:]
        angle = atan2(y2-y1, x2-x1)
        length = 18
        spread = pi / 7
        canvas.polygon([(p(x2), p(y2)),
                        (p(x2 - length*cos(angle-spread)), p(y2 - length*sin(angle-spread))),
                        (p(x2 - length*cos(angle+spread)), p(y2 - length*sin(angle+spread)))], fill=INK)
    if label and label_xy:
        canvas.text((p(label_xy[0]), p(label_xy[1])), label, fill=INK, font=small)


# The far-left rail is the actual loop back to listening, with joins for
# command acknowledgments and queue failures.
line([(55, 2285), (55, 420), (575, 420)], head=True)
line([(900, 2240), (900, 2285), (55, 2285)], head=False)
for source, target, points, label, label_xy, dashed in edges[:-1]:
    line(points, label, label_xy, dashed)

for ident, kind, x, y, width, height, lines in nodes:
    left, top, right, bottom = (p(x-width/2), p(y-height/2),
                                p(x+width/2), p(y+height/2))
    if kind == "rect":
        canvas.rectangle((left, top, right, bottom), fill="white", outline=INK, width=3*SCALE)
    elif kind == "ellipse":
        canvas.ellipse((left, top, right, bottom), fill="white", outline=INK, width=3*SCALE)
    else:
        polygon = [(p(x), top), (right, p(y)), (p(x), bottom), (left, p(y))]
        canvas.polygon(polygon, fill="white", outline=INK)
        canvas.line(polygon + [polygon[0]], fill=INK, width=3*SCALE)
    text_in(lines, x, y, title_font if ident == "start" else small if ident in ("poll", "cmd_work", "ack", "dropped", "http") else font)

canvas.text((p(115), p(2335)),
            "เส้นประ = งานเครือข่ายเบื้องหลัง • rx_ack ยืนยันเพียงว่า Gateway รับผ่าน LoRa",
            font=small, fill=INK)
canvas.text((p(115), p(2380)),
            "เข้าคิวสำเร็จยังไม่ยืนยันว่า Backend รับข้อมูล; POST ล้มเหลวไม่มีการส่งแพ็กเก็ตซ้ำ",
            font=small, fill=INK)

BASE.mkdir(parents=True, exist_ok=True)
image.save(BASE / f"{STEM}.png", dpi=(220, 220))

mxfile = ET.Element("mxfile", {"host": "app.diagrams.net", "agent": "Codex"})
diagram = ET.SubElement(mxfile, "diagram", {"id": "gateway-verified", "name": "Gateway verified"})
model = ET.SubElement(diagram, "mxGraphModel", {"page": "1", "pageScale": "1",
                                               "pageWidth": str(WIDTH), "pageHeight": str(HEIGHT)})
root = ET.SubElement(model, "root")
ET.SubElement(root, "mxCell", {"id": "0"})
ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
for ident, kind, x, y, width, height, lines in nodes:
    shape = "rhombus;" if kind == "diamond" else "ellipse;" if kind == "ellipse" else ""
    style = (shape + "whiteSpace=wrap;html=1;strokeColor=#1d1d1d;fillColor=#ffffff;"
             "fontColor=#1d1d1d;fontFamily=Tahoma;fontSize=28;strokeWidth=2;")
    cell = ET.SubElement(root, "mxCell", {"id": ident, "value": "<br>".join(lines),
                                          "style": style, "vertex": "1", "parent": "1"})
    ET.SubElement(cell, "mxGeometry", {"x": str(x-width/2), "y": str(y-height/2),
                                       "width": str(width), "height": str(height), "as": "geometry"})

for index, (source, target, points, label, _, dashed) in enumerate(edges):
    style = ("edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;strokeColor=#1d1d1d;"
             "strokeWidth=2;endArrow=block;endFill=1;fontFamily=Tahoma;fontSize=24;")
    if dashed:
        style += "dashed=1;dashPattern=6 4;"
    cell = ET.SubElement(root, "mxCell", {"id": f"edge-{index}", "value": label or "",
                                          "style": style, "edge": "1", "parent": "1"})
    geom = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.SubElement(geom, "mxPoint", {"x": str(points[0][0]), "y": str(points[0][1]),
                                    "as": "sourcePoint"})
    ET.SubElement(geom, "mxPoint", {"x": str(points[-1][0]), "y": str(points[-1][1]),
                                    "as": "targetPoint"})
    if len(points) > 2:
        middle = ET.SubElement(geom, "Array", {"as": "points"})
        for x, y in points[1:-1]:
            ET.SubElement(middle, "mxPoint", {"x": str(x), "y": str(y)})

for ident, value, y in [
    ("legend1", "เส้นประ = งานเครือข่ายเบื้องหลัง • rx_ack ยืนยันเพียงว่า Gateway รับผ่าน LoRa", 2310),
    ("legend2", "เข้าคิวสำเร็จยังไม่ยืนยันว่า Backend รับข้อมูล; POST ล้มเหลวไม่มีการส่งแพ็กเก็ตซ้ำ", 2355),
]:
    cell = ET.SubElement(root, "mxCell", {"id": ident, "value": value,
        "style": "text;html=1;whiteSpace=wrap;align=left;verticalAlign=middle;strokeColor=none;fillColor=none;fontFamily=Tahoma;fontSize=24;",
        "vertex": "1", "parent": "1"})
    ET.SubElement(cell, "mxGeometry", {"x": "115", "y": str(y), "width": "1870", "height": "65", "as": "geometry"})

ET.indent(mxfile)
ET.ElementTree(mxfile).write(BASE / f"{STEM}.drawio", encoding="utf-8", xml_declaration=True)
print(BASE / f"{STEM}.png")
print(BASE / f"{STEM}.drawio")
