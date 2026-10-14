import sys, pymupdf
from PIL import Image
pdf=sys.argv[1]; pages=[int(x) for x in sys.argv[2].split(',')]; out=sys.argv[3]
d=pymupdf.open(pdf); ims=[]
for p in pages:
    d[p-1].get_pixmap(dpi=62).save('_s.png'); ims.append(Image.open('_s.png').copy())
w,h=ims[0].size; cols=min(len(ims),4); rows=(len(ims)+cols-1)//cols
c=Image.new('RGB',(w*cols,h*rows),'white')
for i,im in enumerate(ims): c.paste(im,((i%cols)*w,(i//cols)*h))
c.save(out); print(c.size)
