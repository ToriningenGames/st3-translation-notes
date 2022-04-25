# This script reads a CSV file in the translate subdirectory and inserts the strings within into a LIPSYNC*.LIP with a corresponding filename in the source subdirectory.
# It outputs files in the 'output' subdirectory with extension .LIP.

import os
import sys
import csv
import struct
from utils import *

path = os.path.realpath(os.path.dirname(sys.argv[0]))
translate_path = os.path.join(path,"translate")
lip_path = os.path.join(path,"source")
output_path = os.path.join(path,"output")

# Adjust this value to the desired number of frames between text characters.
DELAY = 3

def main():

    # Only process CSV files for which a LIP file with the same base name exists.
    for translate_file in os.listdir(translate_path):
        translate_base_name = os.path.splitext(translate_file)[0]
        if os.path.splitext(translate_file)[1] == ".csv" and os.path.isfile(lip_source := os.path.join(lip_path,translate_base_name)):
            with open(lip_source,"rb") as lip_file:

                # Check signature.
                if lip_file.read(4) != b'ALPD':
                    print(f"{lip_file}: Not LIP file.")
                    continue

                # Set address and limits.
                file_size = struct.unpack("<I",lip_file.read(4))[0]
                line_count = struct.unpack("<I",lip_file.read(4))[0]

                # Copy padding.
                lip_file.seek(file_size + 8)
                padding = lip_file.read()

                # Set current_offset to first offset in list.
                new_offsets = bytearray()
                new_strings = bytearray()

                # Assume first offset is located in second 4-byte value of first entry in offset table.
                lip_file.seek(16)
                current_offset = struct.unpack("<I",lip_file.read(4))[0]

                # Read CSV file.
                # Order is: Voice index, Text offset, Text, LIP commands offset, LIP commands
                with open(os.path.join(translate_path,translate_file),encoding="utf-8") as file:
                    csv_file = csv.reader(file,delimiter="|")

                    for i in csv_file:
                        # Encode current string from csv.
                        # new_offsets will contain triplets of voice index, text offset, and LIP command offset.
                        voice_index = struct.pack("<I",int(i[0]))
                        new_offsets += voice_index
                        cmd_sequence = ''
                        new_cmd_sequence = ''

                        # Check if entire line consists of ASCII characters and assume line was altered.
                        if i[2].isascii():
                            
                            line_encoded = ascii_to_sjis(i[2],line_id=i[1])

                            # The lip movement commands are a sequence of numbers 1-7. Digit 7 writes
                            # characters to screen after a digit 1-6.
                            # Remove all 7s from the sequence and reinsert them later.
                            new_cmd_sequence = i[4].replace('7','')
                            last_char = i[4][-1]

                            # Divide cmd_sequence into groups of digits equal to DELAY.
                            new_cmd_sequence = [new_cmd_sequence[i:i + DELAY] for i in range(0,len(new_cmd_sequence),DELAY)]
                            # If number of cmd_sequence groups is less than length of string, pad it with
                            # the last character.
                            if len(new_cmd_sequence) < len(i[2]):
                                if len(new_cmd_sequence[-1]) < DELAY:
                                    new_cmd_sequence[-1] += last_char * (DELAY - len(new_cmd_sequence[-1]))
                                for i in range(len(i[2]) - len(new_cmd_sequence)):
                                    new_cmd_sequence.append(last_char * DELAY)

                            # Insert one 7 in each group of digits, to draw one text character.
                            for i in range(len(new_cmd_sequence)):
                                cmd_sequence += new_cmd_sequence[i] + '7'

                            # Ensure last character is not a 7 and that length of new cmd_sequence is even.
                            if cmd_sequence[-1] == '7':
                                cmd_sequence += last_char

                            if len(cmd_sequence) % 2 != 0:
                                cmd_sequence += last_char

                        # Otherwise, assume string is unchanged Japanese text and encode string and lip command sequence as-is.
                        else:
                            
                            line_encoded = i[2].encode(encoding="shift_jis_2004") + b'\x00'
                            cmd_sequence = i[4]

                        cmd_sequence_encoded = bytes.fromhex(cmd_sequence) + b'\x00'

                        new_strings += line_encoded + cmd_sequence_encoded

                        # Increase next offset by the length of the string in bytes.
                        new_offsets += struct.pack("<I",current_offset)
                        current_offset += len(line_encoded)

                        new_offsets += struct.pack("<I",current_offset)
                        current_offset += len(cmd_sequence_encoded)

                # Output new offset table and strings.
                output_binary = bytearray()

                # Calculate new file size and repack line_count.
                while True:
                    new_strings += b'\x40'
                    if (len(new_offsets + new_strings) + 8) % 4 == 0:
                        new_length = struct.pack("<I",len(new_offsets + new_strings) + 4)
                        break

                # TODO: Subtract from padding area to offset new data, or remove padding completely.

                output_binary += b'ALPD' + new_length + struct.pack("<I",line_count) + new_offsets + new_strings + padding

                with open(os.path.join(output_path,translate_base_name),"wb") as output_file:
                    output_file.write(output_binary)
                    print(f"{translate_base_name}: {len(output_binary)} ({hex(len(output_binary))}) bytes written.")


if __name__ == "__main__":
    main()
