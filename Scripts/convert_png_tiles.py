# This script reads a PNG file containing a single row of 26 x 26 tiles and outputs binary data.
# NumPy and PyPNG are required as dependencies.
#
# Specify an input PNG file and an optional output file as arguments.
# If an output file is not given, the binary data will be written in the console.
#
# The original graphic format is 4 bits per pixel, with each byte representing two pixels stacked vertically. 
# The left nybble represents the lower pixel and the right nybble represents the upper pixel.
# 13 rows of these bytes create a 26 x 26 tile.
# 
# To create replacement tiles, create a non-transparent image with the following palette:
# 00 10 20 30 40 50 60 70 80 90 A0 B0 C0 D0 E0 F0
#
# Although the resulting image will be grayscale, this image should be saved as 8-bit RGB.
# Image editors will frequently override indexed palettes when converting to grayscale,
# so creating RGB images is recommended to guarantee the palette will not be changed.
# The first channel (red) of this file will be read and used as pixel data.
#
# Overwrite SKFONT.CG with the output starting at the tile offset to replace.

import struct
import sys
import numpy as np
import png

def main():

    if len(sys.argv) < 2:
        print("Specify input PNG file.")
        return

    with open(sys.argv[1],"rb") as input_file:
        output = b''

        # Read image and split into equal number of 26 x 13 arrays.
        image = png.Reader(file=input_file).asDirect()
        image_2d = np.empty((image[1],image[0]),dtype="uint8")
        rows = image[2]
        try:
            for i in range(image[1]):
                current_row = next(rows)
                image_2d[i] = current_row[0::3] # Read only red channel.

            # Split into individual tiles.
            tiles = np.hsplit(image_2d,image[0] / 26)
            for i in tiles:
                # Bitwise shift 4 to the right to obtain 0-F value for each pixel.
                tile = np.right_shift(i,4)

                # Divide each tile into 26 x 2 arrays.
                tile_row_pairs = np.vsplit(tile,13)

                for row_pair in tile_row_pairs:    
                    for column in range(0,26):
                        # Upper pixel is right nybble; lower pixel is left nybble.
                        upper_pixel = row_pair[0][column]
                        lower_pixel = row_pair[1][column] << 4
                        pixels = upper_pixel + lower_pixel

                        output += struct.pack("=B",pixels)

        except ValueError:
            print("Input PNG file must be 8-bit, no transparency, and have a height of 26 pixels and width a multiple of 26 pixels.")
            return

        if len(sys.argv) >= 3:
            with open(sys.argv[2],"wb") as output_file:
                output_file.write(output)
                print(f"Paste the contents of {sys.argv[2]} into SKFONT.CG starting at the tile(s) to replace.")

        else:
            print(output.hex())
            print("\nPaste the above hex into SKFONT.CG starting at the tile(s) to replace.")


if __name__ == "__main__":
    main()
