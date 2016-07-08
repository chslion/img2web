#!/usr/bin/python
# -*- coding: utf-8 -*-
import argparse
import os
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont, ImageEnhance


def sum_array(data):
    s = 0
    for x in data:
        s += x
    return s

"""
does not work w/ python 3, since PIL has some bugs...
"""

"""
* Returns an image with reduced opacity. Taken from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/362879
* edited by chslion
* returns watermarked img file
* it contains no exif data
"""
def watermark(image, opacity):
    scale = 0.1
    fontfile = "UbuntuMono-R.ttf"
    text = "alexander.jaehnel"

    width, height = image.size

    # skip small images
    if width < 100 or height < 100:
        return image


    # ===calc histogram of original
    # to black/white    
    img_bw = image.convert("L")
    hist = img_bw.histogram()

    # determine text color
    black = hist[0:128]
    white = hist[128:256]

    sblack = sum_array(black)
    swhite = sum_array(white)

    if sblack > swhite:
        color = (255, 255, 255)

        maxblack = hist[0:64]
        minblack = hist[64:128]

        sblack_min = sum_array(minblack)
        sblack_max = sum_array(maxblack)

        if sblack_max > sblack_min:
            opacity /= 2
            print("image seems very dark, using white text with: {} opacity".format(opacity))
        else:
            print("image seems dark, using white text with: {} opacity".format(opacity))

    elif sblack < swhite:
        color = (0, 0, 0)

        minwhite = hist[128:192]
        maxwhite = hist[192:256]

        swhite_min = sum_array(minwhite)
        swhite_max = sum_array(maxwhite)

        if swhite_max > swhite_min:
            opacity *= 2
            print("image seems very light, using dark text with: {} opacity".format(opacity))
        else:
            print("image seems light, using dark text with: {} opacity".format(opacity))
    else:
        color = (128, 128, 128)

        print("image is equally dark/light, using gray text")

    if opacity > 1.0:
        opacity = 1.0
    elif opacity < 0.0:
        opacity = 0.0

    font_size = int(scale*height)
    font = ImageFont.truetype(fontfile, font_size)

    if image.mode != "RGBA":
        image = image.convert("RGBA")


    # watermark layer takes biggest dimension
    # so rotation fills whole image 
    maxdim = max(width, height)*2
    textlayer = Image.new("RGBA", [maxdim, maxdim], (0,0,0,0))

    textdraw = ImageDraw.Draw(textlayer)

    wm_width, wm_height = textdraw.textsize(text, font=font)
    # textsize does not give correct height for ttf
    offset = font.getoffset(text)
    wm_width += offset[0]
    wm_height += offset[1]

    # lower right corner
    # textpos = [
    #     image.size[0] - textsize[0] - offset[0],
    #     image.size[1] - textsize[1] - offset[1]
    # ]
    # textdraw.text([0,0], text, font=font, fill=color)
    maxx = (int)(maxdim/wm_width)
    maxy = (int)(maxdim/wm_height)

    # render font in a checkered layout
    for y in range(maxy):
        y_odd = y % 2 == 0
        for x in range(maxx):
            # x is odd?
            x_odd = x % 2 == 0

            check = x_odd
            if not y_odd:
                check = not check

            if check:
                textdraw.text([x*wm_width, y*wm_height], text, font=font, fill=color)

    # rotate
    textlayer = textlayer.rotate(45, Image.BICUBIC)

    # crop to original size, from center
    # import pdb; pdb.set_trace()
    cropx = textlayer.size[0] / 2 - width / 2
    cropy = textlayer.size[1] / 2 - height / 2
    textlayer = textlayer.crop([cropx, cropy, cropx + width, cropy + height])

    if opacity > 0.0 and opacity < 1.0:
        if textlayer.mode != 'RGBA':
            textlayer = textlayer.convert('RGBA')
        else:
            textlayer = textlayer.copy()
        alpha = textlayer.split()[3]
        alpha = ImageEnhance.Brightness(alpha).enhance(opacity)
        textlayer.putalpha(alpha)

    # overlay onto original image
    return Image.composite(textlayer, image, textlayer)


# process_image("/hom/lion/foo.png", "..")
def process_image(path, target_path, width, alpha):
    fname = os.path.basename(path)
    fname, fext = os.path.splitext(fname)

    # convert uppercase extension
    fext = fext.lower()

    if not (fext == ".png" or fext == ".jpg"):        
        print("skip invalid image: {}".format(path))
        return

    # skip processed images
    if fname.lower().endswith("_web"):
        print("skip processed image: {}".format(path))
        return
    
    print("processing: {}".format(path))
    
    target_path = os.path.join(target_path, "{}_web{}".format(fname, fext))

    im = Image.open(path)
    # apply watermark
    wm = watermark(im, alpha)     

    # do not scale up
    if im.size[0] > width:
        # scale down to width(eg 1024) but keep HEIGHT in ratio    
        wm.thumbnail([width, im.size[1]])
    
    # save image with no ADDITIONAL compression
    if fext == ".jpg":
        wm.save(target_path, "jpeg", quality=100)
    else:
        wm.save(target_path, "png")

def run():
    parser = argparse.ArgumentParser(
        description="Watermark Creator"
    )

    parser.add_argument("-o", "--opacity", type=float, dest="opacity", default=0.1)
    parser.add_argument("-w", "--width", type=int, dest="width", default=1024)    
    parser.add_argument("-r", "--res", type=str, dest="res_path", default="res")
    # parser.add_argument("path", type=str)
    parser.add_argument("target_path", type=str)
    cfg = parser.parse_args()

    print("img2web 1.0")
	
    res_path = os.path.join(cfg.target_path, cfg.res_path)

    if os.path.isfile(res_path):

        process_image(                
                res_path,
                cfg.target_path,                
                cfg.width,                
                cfg.opacity                
            )

    elif os.path.isdir(res_path):

        for folder_item in os.listdir(res_path):

            if os.path.isdir(folder_item):
                continue

            process_image(                
                os.path.join(res_path, folder_item),
                cfg.target_path,
                cfg.width,
                cfg.opacity           
            )

    else:
        print("invalid path, file or directory expected")

if __name__ == "__main__":
    run()
