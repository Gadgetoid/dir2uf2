# MicroPython LittleFS V2 - Directory to .uf2

Pack a directory of files (optionally filtered via a manifest) into a LFSV2 filesystem and save as .uf2 for flashing to the Pico.

Needs LittleFS-Python:
 - https://pypi.org/project/littlefs-python/
 - https://github.com/jrast/littlefs-python


## Current Limitations

Only supports the Pico W:

- Fixed filesystem size of 848k
- Fixed offset 0x1012c000 (flash starts at 0x10000000)
- Outputs .uf2 with Pico family ID (non-generic, blocked from flashing to other boards???)

## Usage

```
usage: dir2uf2 [-h] [--filename FILENAME] [--block-size BLOCK_SIZE] [--read-size READ_SIZE] [--prog-size PROG_SIZE] [--manifest MANIFEST] source_dir

positional arguments:
  source_dir            Source directory.

options:
  -h, --help            show this help message and exit
  --filename FILENAME   Output filename.
  --block-size BLOCK_SIZE
                        LFS block size in Kb.
  --read-size READ_SIZE
                        LFS read size in Kb.
  --prog-size PROG_SIZE
                        LFS prog size in Kb.
  --manifest MANIFEST   Manifest to filter copied files.
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
