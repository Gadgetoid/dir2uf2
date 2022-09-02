import argparse
import os
import sys

from littlefs import LittleFS

parser = argparse.ArgumentParser()
parser.add_argument("--img-filename", default="littlefs.img")
parser.add_argument("--img-size", type=int, default=1 * 1024 * 1024)
parser.add_argument("--block-size", type=int, default=4096)
parser.add_argument("--read-size", type=int, default=256)
parser.add_argument("--prog-size", type=int, default=256)
parser.add_argument("source")
args = parser.parse_args()

img_filename = args.img_filename
img_size = args.img_size
block_size = args.block_size
read_size = args.read_size
prog_size = args.prog_size
source_dir = args.source

block_count = img_size / block_size
if block_count * block_size != img_size:
    print("image size should be a multiple of block size")
    exit(1)

fs = LittleFS(
    block_size=block_size,
    block_count=block_count,
    read_size=read_size,
    prog_size=prog_size,
)

# Note: path component separator etc are assumed to be compatible
# between littlefs and host.
for root, dirs, files in os.walk(source_dir):
    print(f"root {root} dirs {dirs} files {files}")
    for dir in dirs:
        path = os.path.join(root, dir)
        relpath = os.path.relpath(path, start=source_dir)
        print(f"Mkdir {relpath}")
        fs.mkdir(relpath)
    for f in files:
        path = os.path.join(root, f)
        relpath = os.path.relpath(path, start=source_dir)
        print(f"Copying {path} to {relpath}")
        with open(path, "rb") as infile:
            with fs.open(relpath, "wb") as outfile:
                outfile.write(infile.read())

with open(img_filename, "wb") as f:
    f.write(fs.context.buffer)
