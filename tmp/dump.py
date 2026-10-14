import re, zipfile
z = zipfile.ZipFile(r"D:\denos\hp1\tmp\t.docx")
print(z.namelist())
x = z.read("word/document.xml").decode("utf8")
print(len(x))
body = x
for p in re.findall(r"<w:p[ >].*?</w:p>", body, flags=re.S):
    t = "".join(re.findall(r"<w:t[^>]*>([^<]*)</w:t>", p))
    st = re.search(r'w:pStyle w:val="([^"]+)"', p)
    print(("[" + st.group(1) + "] " if st else "") + t)
