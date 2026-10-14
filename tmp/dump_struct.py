import docx
from docx.oxml.ns import qn
d = docx.Document(r"D:\denos\hp1\tmp\t.docx")
body = d.element.body
for i, el in enumerate(body):
    tag = el.tag.split('}')[1]
    if tag == 'p':
        p = docx.text.paragraph.Paragraph(el, d)
        txt = p.text.strip()
        flags = []
        if el.find('.//' + qn('w:sectPr')) is not None: flags.append('SECT')
        if any(b.get(qn('w:type')) == 'page' for b in el.iter(qn('w:br'))): flags.append('PGBRK')
        if el.find('.//' + qn('w:pageBreakBefore')) is not None: flags.append('PBB')
        if el.find('.//' + qn('w:drawing')) is not None: flags.append('IMG')
        if el.find('.//' + qn('w:fldChar')) is not None or el.find('.//' + qn('w:instrText')) is not None: flags.append('FLD')
        print(i, 'P', p.style.name, flags, txt[:70])
    elif tag == 'tbl':
        t = docx.table.Table(el, d)
        print(i, 'TBL', len(t.rows), 'x', len(t.columns), '|', t.rows[0].cells[0].text[:30], '|', t.style.name if t.style else None)
    else:
        print(i, tag)
