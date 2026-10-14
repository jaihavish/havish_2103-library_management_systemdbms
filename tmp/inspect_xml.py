import docx, re
d = docx.Document(r"D:\denos\hp1\tmp\t.docx")
body = list(d.element.body)
from lxml import etree
def show(i, n=1800):
    x = etree.tostring(body[i], encoding="unicode")
    x = re.sub(r'xmlns:\w+="[^"]+"\s*', '', x)
    print(i, x[:n], '\n')
for i in (68, 159, 148, 151, 163, 183, 184, 333, 301, 302):
    show(i, 1500)
t = d.tables
print(len(t))
tb = body[170]
x = etree.tostring(tb, encoding="unicode"); x = re.sub(r'xmlns:\w+="[^"]+"\s*', '', x)
print(x[:4500])
