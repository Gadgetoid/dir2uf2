# MicroPython LittleFS V2 - Directory to .uf2

Pack a directory of files (optionally filtered via a manifest) into a LFSV2 filesystem and save as .uf2 for flashing to the Pico.

Needs LittleFS-Python:
 - https://pypi.org/project/littlefs-python/
 - https://github.com/jrast/littlefs-python


## Current Limitations

- Outputs .uf2 with Pico family ID (non-generic, blocked from flashing to other boards???)
- Only compatible with MicroPython >= 1.23.0

## Usage

```
usage: dir2uf2 [-h] [--filename FILENAME] [--fs-start FS_START] [--fs-size FS_SIZE] [--fs-compact] [--block-size BLOCK_SIZE]
               [--read-size READ_SIZE] [--prog-size PROG_SIZE] [--manifest MANIFEST] [--append-to APPEND_TO] [--debug]
               [--verbose]
               source_dir

positional arguments:
  source_dir            Source directory.

options:
  -h, --help            show this help message and exit
  --filename FILENAME   Output filename.
  --fs-start FS_START   Filesystem offset.
  --fs-size FS_SIZE     Filesystem size.
  --fs-compact          Compact filesystem to used blocks.
  --block-size BLOCK_SIZE
                        LFS block size in Kb.
  --read-size READ_SIZE
                        LFS read size in Kb.
  --prog-size PROG_SIZE
                        LFS prog size in Kb.
  --manifest MANIFEST   Manifest to filter copied files.
  --append-to APPEND_TO
                        uf2 file to append filesystem.
  --debug               Debug output.
  --verbose             Verbose output.
```

## Examples

With a manifest:

```
./dir2uf2 --manifest enviro.txt ~/Downloads/enviro-0.0.5
```

Copy entire dir:

```
./dir2uf2 ~/Downloads/enviro-0.0.5
```

Compact filesystem for a (sometimes *much*) smaller .uf2:

```
./dir2uf2 --fs-compact ~/Downloads/enviro-0.0.5
```
