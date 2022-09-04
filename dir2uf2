#!/usr/bin/env python3

import argparse
import struct
import pathlib
import littlefs


UF2_MAGIC_START0 = 0x0A324655  # "UF2\n"
UF2_MAGIC_START1 = 0x9E5D5157  # Randomly selected
UF2_MAGIC_END    = 0x0AB16F30  # Ditto
FAMILY_ID        = 0xe48bff56  # RP2040
FS_START_ADDR    = 0x1012c000  # Pico W MicroPython LFSV2 offset
FS_SIZE          = 848 * 1024

BLOCK_SIZE = 512
DATA_SIZE = 256
HEADER_SIZE = 32
FOOTER_SIZE = 4
PADDING_SIZE = BLOCK_SIZE - DATA_SIZE - HEADER_SIZE - FOOTER_SIZE
DATA_PADDING = b"\x00" * PADDING_SIZE


def uf2_to_bin(data):
    for offset in range(0, len(data), BLOCK_SIZE):
        start0, start1, flags, addr, size, block_no, num_blocks, family_id = struct.unpack(b"<IIIIIIII", data[offset:offset + HEADER_SIZE])
        if args.debug:
            print(f"Block {block_no}/{num_blocks} addr {addr:08x} size {size}")
        block_data = data[offset + HEADER_SIZE:offset + HEADER_SIZE + DATA_SIZE]
        yield addr, block_data


def bin_to_uf2(sections):
    total_blocks = 0
    block_no = 0

    for section in sections:
        offset, data = section
        total_blocks += (len(data) + (DATA_SIZE - 1)) // DATA_SIZE

    for section in sections:
        offset, data = section

        if args.debug:
            print(f"uf2: Adding {len(data)} bytes at 0x{offset:08x}")

        num_blocks = (len(data) + (DATA_SIZE - 1)) // DATA_SIZE

        flags = 0x0
        if FAMILY_ID:
            flags |= 0x2000

        for index in range(num_blocks):
            ptr = DATA_SIZE * index

            chunk = data[ptr:ptr + DATA_SIZE].rjust(DATA_SIZE, b"\x00")

            header = struct.pack(
                b"<IIIIIIII",
                UF2_MAGIC_START0, UF2_MAGIC_START1, flags,
                ptr + offset, DATA_SIZE, block_no, total_blocks,
                FAMILY_ID)

            footer = struct.pack(b"<I", UF2_MAGIC_END)

            block = header + chunk + DATA_PADDING + footer

            block_no += 1

            if len(block) != BLOCK_SIZE:
                raise RuntimeError("Invalid block size")

            yield block


parser = argparse.ArgumentParser()
parser.add_argument("--filename", type=pathlib.Path, default="filesystem", help="Output filename.")
parser.add_argument("--fs-start", type=int, default=FS_START_ADDR, help="Filesystem offset.")
parser.add_argument("--fs-size", type=int, default=FS_SIZE, help="Filesystem size.")
parser.add_argument("--block-size", type=int, default=4096, help="LFS block size in Kb.")
parser.add_argument("--read-size", type=int, default=256, help="LFS read size in Kb.")
parser.add_argument("--prog-size", type=int, default=32, help="LFS prog size in Kb.")
parser.add_argument("--manifest", default=None, help="Manifest to filter copied files.")
parser.add_argument("--append-to", type=pathlib.Path, default=None, help="uf2 file to append filesystem.")
parser.add_argument("--debug", action="store_true", help="Debug output.")
parser.add_argument("--verbose", action="store_true", help="Verbose output.")
parser.add_argument("source_dir", type=pathlib.Path, help="Source directory.")
args = parser.parse_args()

block_count = args.fs_size / args.block_size
if block_count * args.block_size != args.fs_size:
    print("image size should be a multiple of block size")
    exit(1)

lfs = littlefs.LittleFS(
    block_size=args.block_size,
    block_count=block_count,
    read_size=args.read_size,
    prog_size=args.prog_size,
)

source_dir = args.source_dir
output_filename = args.filename


def copy_files(todo):
    for src in todo:
        if src.is_dir():
            dst = src.relative_to(source_dir)
            if args.verbose:
                print(f"- mkdir: {dst}")
            lfs.mkdir(str(dst))
        if src.is_file():
            dst = src.relative_to(source_dir)
            if args.verbose:
                print(f"- copy: {src} to {dst}")
            with lfs.open(str(dst), "wb") as outfile:
                with open(src, "rb") as infile:
                    outfile.write(infile.read())


if args.manifest is None:
    print(f"Copying directory: {args.source_dir}")
    # Walk the entire source dir and copy *everything*
    copy_files(source_dir.glob("**/*"))

else:
    print(f"Using manifest: {args.manifest}")
    # Copy files/globs listed in the manifest relative to the source dir
    todo = open(args.manifest, "r").read().split("\n")
    for item in todo:
        dir = pathlib.Path(item).parent
        try:
            lfs.mkdir(str(dir))
        except FileExistsError:
            pass
        copy_files(source_dir.glob(item))


# Write a .bin with *just* the filesystem
bin_filename = output_filename.with_suffix(".bin")

with open(bin_filename, "wb") as f:
    f.write(lfs.context.buffer)

print(f"Written: {bin_filename}")


# Write a .uf2 with *just* the filesystem
uf2_filename = output_filename.with_suffix(".uf2")

with open(uf2_filename, "wb") as f:
    for block in bin_to_uf2([(FS_START_ADDR, lfs.context.buffer)]):
        f.write(block)

print(f"Written: {uf2_filename}")


if args.append_to is not None:
    if not args.append_to.is_file():
        raise RuntimeError(f"Could not find {args.append_to}")

    uf2_append_filename = output_filename.with_name(f"{args.append_to.stem}-{uf2_filename.stem}.uf2")

    print(f"Appending to {args.append_to}")

    append_to = open(args.append_to, "rb").read()

    # Read the first block address, this will be the base offset
    start_addr = next(uf2_to_bin(append_to))[0]

    # Read the .uf2 contents to binary
    data = b"".join(map(lambda b: b[1], uf2_to_bin(append_to)))

    # Figure out how much padding we need
    fw_size = args.fs_start - start_addr

    # Pad the supplied firmware up to our filesystem range
    # We *could* create a .uf2 without this padding, supplying the
    # firmware & filesystem blocks with different range offsets.
    # However while this works fine in Picotool - which detects
    # and writes each sequential range of data - it completely
    # fails to write the second set (filesystem) in the RP2040
    # bootloader.
    # So, humph, we'll just pad and concat the two which makes
    # for a bigger, but actually compatible .uf2.
    data = data.ljust(fw_size, b"\xff")

    # Add our filesystem onto the data
    data += lfs.context.buffer

    # Pack data into a uf2 at offset start_addr
    # This will be FS_START_ADDR if we're not appending.
    with open(uf2_append_filename, "wb") as f:
        for block in bin_to_uf2([(start_addr, data)]):
            f.write(block)

    print(f"Written: {uf2_append_filename}")
