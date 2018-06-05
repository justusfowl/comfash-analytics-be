from colorthief import ColorThief

from colormap import rgb2hex


def get_colors(file_name):

    color_thief = ColorThief(file_name)

    palette = color_thief.get_palette(color_count=6)

    colors = []

    for p in palette:
        colors.append(rgb2hex(p[0], p[1], p[2]))

    return colors