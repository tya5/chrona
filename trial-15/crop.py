import sys
from PIL import Image
f,x0,y0,x1,y1,out=sys.argv[1:7]; s=float(sys.argv[7]) if len(sys.argv)>7 else 2
im=Image.open(f).crop((int(x0),int(y0),int(x1),int(y1)))
im=im.resize((int(im.width*s),int(im.height*s)),Image.LANCZOS); im.save(out)
