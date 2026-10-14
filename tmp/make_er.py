import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

W, GAPX, GAPY = 2.05, 0.8, 0.62
LINE_H = 0.175

E = {  # name: (col, row, [attributes])
    "CATEGORY":   (0, 0, ["PK category_id", "name"]),
    "BOOK":       (1, 0, ["PK book_id", "title", "FK category_id"]),
    "BOOK_AUTHOR": (2, 0, ["PK,FK book_id", "PK,FK author_id"]),
    "PUBLISHER":  (0, 1, ["PK publisher_id", "name", "city"]),
    "EDITION":    (1, 1, ["PK edition_id", "FK book_id", "FK publisher_id", "isbn (unique)", "edition_no, pub_year"]),
    "AUTHOR":     (2, 1, ["PK author_id", "name", "country"]),
    "COPY":       (1, 2, ["PK copy_id", "FK edition_id", "accession_no (unique)", "shelf, status"]),
    "RESERVATION": (2, 2, ["PK reservation_id", "FK edition_id", "FK member_id", "queue_no, status", "FK copy_id"]),
    "STAFF":      (0, 3, ["PK staff_id", "username", "role"]),
    "ISSUE":      (1, 3, ["PK issue_id", "FK copy_id, FK member_id", "FK issued_by", "issue_date, due_date", "return_date"]),
    "MEMBER":     (2, 3, ["PK member_id", "card_no, email (unique)", "FK member_type", "expiry_date, status"]),
    "FINE":       (1, 4, ["PK fine_id", "FK issue_id (unique)", "days_late, amount", "paid_amount"]),
    "MEMBER_POLICY": (2, 4, ["PK member_type", "max_books", "loan_days", "fine_per_day"]),
    "DIGITAL_RESOURCE": (0, 5, ["PK resource_id", "title, resource_type", "FK publisher_id", "licence_end"]),
    "DIGITAL_ACCESS_LOG": (1, 5, ["PK log_id", "FK resource_id", "FK member_id", "accessed_at, minutes_used"]),
}
# (a, b, label, card at a, card at b, rad)
R = [
    ("CATEGORY", "BOOK", "has", "1", "N", 0), ("BOOK", "BOOK_AUTHOR", "", "1", "N", 0),
    ("AUTHOR", "BOOK_AUTHOR", "", "1", "N", 0), ("BOOK", "EDITION", "has", "1", "N", 0),
    ("PUBLISHER", "EDITION", "publishes", "1", "N", 0), ("EDITION", "COPY", "has", "1", "N", 0),
    ("EDITION", "RESERVATION", "reserved in", "1", "N", 0), ("MEMBER", "RESERVATION", "makes", "1", "N", 0),
    ("COPY", "ISSUE", "lent in", "1", "N", 0), ("MEMBER", "ISSUE", "borrows", "1", "N", 0),
    ("STAFF", "ISSUE", "records", "1", "N", 0), ("ISSUE", "FINE", "may cause", "1", "0..1", 0),
    ("MEMBER_POLICY", "MEMBER", "governs", "1", "N", 0), ("MEMBER", "DIGITAL_ACCESS_LOG", "uses", "1", "N", 0),
    ("DIGITAL_RESOURCE", "DIGITAL_ACCESS_LOG", "used in", "1", "N", 0),
    ("PUBLISHER", "DIGITAL_RESOURCE", "supplies", "1", "N", 0.5),
]
HEIGHTS = {k: LINE_H * (len(v[2]) + 1) + 0.12 for k, v in E.items()}
rowh = {}
for k, (c, r, a) in E.items():
    rowh[r] = max(rowh.get(r, 0), HEIGHTS[k])
ytop, y = {}, 0
for r in sorted(rowh):
    ytop[r] = y
    y -= rowh[r] + GAPY
box = {}
for k, (c, r, a) in E.items():
    x = 0.7 + c * (W + GAPX)
    h = HEIGHTS[k]
    yc = ytop[r] - rowh[r] / 2
    box[k] = (x, yc - h / 2, W, h)

fig, ax = plt.subplots(figsize=(7.4, 8.6))
ax.set_xlim(-1.25, 0.7 + 3 * W + 2 * GAPX + 0.15)
ax.set_ylim(y + GAPY - 0.1, 0.25)
ax.axis("off")


def centre(k):
    x, y0, w, h = box[k]
    return x + w / 2, y0 + h / 2


def edge_point(k, toward):
    x, y0, w, h = box[k]
    cx, cy = centre(k)
    dx, dy = toward[0] - cx, toward[1] - cy
    t = min((w / 2) / abs(dx) if dx else 9e9, (h / 2) / abs(dy) if dy else 9e9)
    return cx + dx * t, cy + dy * t


for a, b, label, ca, cb, rad in R:
    pa, pb = edge_point(a, centre(b)), edge_point(b, centre(a))
    if rad:
        xa, ya = box[a][0], box[a][1] + box[a][3] / 2          # leave from the left side
        xb, yb = box[b][0], box[b][1] + box[b][3] / 2
        pa, pb = (xa, ya), (xb, yb)
    ax.add_patch(FancyArrowPatch(pa, pb, arrowstyle="-", lw=0.9, color="#4b5563",
                                 connectionstyle=f"arc3,rad={rad}", zorder=1))
    for (p, q, c) in ((pa, pb, ca), (pb, pa, cb)):
        t = 0.16 / max(((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5, 0.01)
        ax.text(p[0] + (q[0] - p[0]) * t + (-0.12 if rad else 0), p[1] + (q[1] - p[1]) * t + 0.07, c,
                fontsize=6.5, color="#b91c1c", ha="center", va="center", fontweight="bold",
                bbox=dict(fc="white", ec="none", pad=0.4), zorder=3)
    horizontal = abs(pa[1] - pb[1]) < 0.05
    if label and not rad and not horizontal:
        mx, my = (pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2
        ax.text(mx, my, label, fontsize=6, style="italic", ha="center", va="center", color="#374151",
                bbox=dict(fc="white", ec="none", pad=0.6), zorder=3)
    if label and rad:
        ax.text(box[a][0] - 0.28, (pa[1] + pb[1]) / 2, label, fontsize=6, style="italic", rotation=90,
                ha="center", va="center", color="#374151")

for k, (c, r, attrs) in E.items():
    x, y0, w, h = box[k]
    ax.add_patch(Rectangle((x, y0), w, h, fc="#f8fafc", ec="#1f2a44", lw=1.1, zorder=2))
    ax.add_patch(Rectangle((x, y0 + h - LINE_H - 0.06), w, LINE_H + 0.06, fc="#1f2a44", ec="#1f2a44", zorder=2))
    ax.text(x + w / 2, y0 + h - (LINE_H + 0.06) / 2, k, color="white", fontsize=6.8, fontweight="bold",
            ha="center", va="center", zorder=3)
    for i, a in enumerate(attrs):
        ax.text(x + 0.08, y0 + h - (LINE_H + 0.06) - 0.03 - LINE_H * (i + 0.55), a, fontsize=6.3,
                fontweight="bold" if a.startswith("PK") else "normal", ha="left", va="center", zorder=3,
                family="DejaVu Sans")

fig.savefig(r"D:\denos\hp1\tmp\er.png", dpi=220, bbox_inches="tight", pad_inches=0.05)
print("saved")
