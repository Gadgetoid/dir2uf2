#!/usr/bin/env python3
import io
import json
import struct
import sys


UF2_MAGIC_START0 = 0x0A324655  # "UF2\n"
UF2_MAGIC_START1 = 0x9E5D5157  # Randomly selected
UF2_MAGIC_END    = 0x0AB16F30  # Ditto

FAMILY_ID_RP2040 = 0xe48bff56  # RP2040
FAMILY_ID_PAD    = 0xe48bff57  # ???
FAMILY_ID_RP2350 = 0xe48bff59  # RP2350

FLASH_START_ADDR = 0x10000000

BLOCK_SIZE   = 512
DATA_SIZE    = 256
HEADER_SIZE  = 32
FOOTER_SIZE  = 4
PADDING_SIZE = BLOCK_SIZE - DATA_SIZE - HEADER_SIZE - FOOTER_SIZE
DATA_PADDING = b"\x00" * PADDING_SIZE

BI_MAGIC = b"\xf2\xeb\x88\x71"
BI_END = b"\x90\xa3\x1a\xe7"

GPIO_FUNC_XIP  = 0
GPIO_FUNC_SPI  = 1
GPIO_FUNC_UART = 2
GPIO_FUNC_I2C  = 3
GPIO_FUNC_PWM  = 4
GPIO_FUNC_SIO  = 5
GPIO_FUNC_PIO0 = 6
GPIO_FUNC_PIO1 = 7
GPIO_FUNC_GPCK = 8
GPIO_FUNC_USB  = 9
GPIO_FUNC_NULL = 0xf

TYPE_RAW_DATA        = 1
TYPE_SIZED_DATA      = 2
TYPE_LIST_ZERO_TERMINATED = 3
TYPE_BSON            = 4
TYPE_ID_AND_INT      = 5
TYPE_ID_AND_STRING   = 6

TYPE_BLOCK_DEVICE    = 7
TYPE_PINS_WITH_FUNC  = 8
TYPE_PINS_WITH_NAME  = 9
TYPE_NAMED_GROUP     = 10

ID_PROGRAM_NAME = 0x02031c86
ID_PROGRAM_VERSION_STRING = 0x11a9bc3a
ID_PROGRAM_BUILD_DATE_STRING = 0x9da22254
ID_BINARY_END = 0x68f465de
ID_PROGRAM_URL = 0x1856239a
ID_PROGRAM_DESCRIPTION = 0xb6a07c19
ID_PROGRAM_FEATURE = 0xa1f4b453
ID_PROGRAM_BUILD_ATTRIBUTE = 0x4275f0d3
ID_SDK_VERSION = 0x5360b3ab
ID_PICO_BOARD = 0xb63cffbb
ID_BOOT2_NAME = 0x7f8882e1
ID_FILESYSTEM = 0x1009be7e

ID_MP_BUILTIN_MODULE = 0x4a99d719

IDS = {
    ID_PROGRAM_NAME: "Program Name",
    ID_PROGRAM_VERSION_STRING: "Program Version",
    ID_PROGRAM_BUILD_DATE_STRING: "Build Date",
    ID_BINARY_END: "Binary End Address",
    ID_PROGRAM_URL: "Program URL",
    ID_PROGRAM_DESCRIPTION: "Program Description",
    ID_PROGRAM_FEATURE: "Program Feature",
    ID_PROGRAM_BUILD_ATTRIBUTE: "Program Build Attribute",
    ID_SDK_VERSION: "SDK Version",
    ID_PICO_BOARD: "Pico Board",
    ID_BOOT2_NAME: "Boot Stage 2 Name"
}

TYPES = {
    TYPE_RAW_DATA: "Raw Data",
    TYPE_SIZED_DATA: "Sized Data",
    TYPE_LIST_ZERO_TERMINATED: "Zero Terminated List",
    TYPE_BSON: "BSON",
    TYPE_ID_AND_INT: "ID & Int",
    TYPE_ID_AND_STRING: "ID & Str",
    TYPE_BLOCK_DEVICE: "Block Device",
    TYPE_PINS_WITH_FUNC: "Pins With Func",
    TYPE_PINS_WITH_NAME: "Pins With Name",
    TYPE_NAMED_GROUP: "Named Group"
}

GPIO_FUNCS = {
    GPIO_FUNC_XIP: "XIP",
    GPIO_FUNC_SPI: "SPI",
    GPIO_FUNC_UART: "UART",
    GPIO_FUNC_I2C: "I2C",
    GPIO_FUNC_PWM: "PWM",
    GPIO_FUNC_SIO: "SIO",
    GPIO_FUNC_PIO0: "PIO0",
    GPIO_FUNC_PIO1: "PIO1",
    GPIO_FUNC_GPCK: "GPCK",
    GPIO_FUNC_USB: "USB",
    GPIO_FUNC_NULL: "NULL"
}

BINARY_INFO_BLOCK_DEV_FLAG_READ = 1 << 0      # if not readable, then it is basically hidden, but tools may choose to avoid overwriting it
BINARY_INFO_BLOCK_DEV_FLAG_WRITE = 1 << 1     #
BINARY_INFO_BLOCK_DEV_FLAG_REFORMAT = 1 << 2  # may be reformatted..

BINARY_INFO_BLOCK_DEV_FLAG_PT_UNKNOWN = 0 << 4  # unknown free to look
BINARY_INFO_BLOCK_DEV_FLAG_PT_MBR = 1 << 4      # expect MBR
BINARY_INFO_BLOCK_DEV_FLAG_PT_GPT = 2 << 4      # expect GPT
BINARY_INFO_BLOCK_DEV_FLAG_PT_NONE = 3 << 4     # no partition table

ALWAYS_A_LIST = ("NamedGroup", "BlockDevice", "ProgramFeature")


class MemoryReader():
    def __init__(self, mem, global_offset=FLASH_START_ADDR):
        self.mem = mem
        self.offset = 0
        self.buf_len = 16
        self.global_offset = global_offset
        self.buf = bytearray(self.buf_len)

    def seek(self, offset):
        self.offset = offset

    def read(self, length):
        buf = bytearray(length) if length > self.buf_len else self.buf
        for i in range(length):
            buf[i] = self.mem[self.global_offset + self.offset]
            self.offset += 1
        return bytes(buf[:length])


class UF2Reader(io.BytesIO):
    def __init__(self, filepath):
        sections = self.uf2_to_bin(filepath)
        bin = b""
        for section in sections:
            section_index, start_addr, family_id, flags, num_blocks, block_data = section
            if family_id in (FAMILY_ID_RP2040, FAMILY_ID_RP2350):
                bin = block_data
                break
        io.BytesIO.__init__(self, bin)

    def uf2_to_bin(self, filepath):
        with open(filepath, "rb") as file:
            section_index = 0

            while data := file.read(BLOCK_SIZE):
                start0, start1, flags, addr, size, block_no, num_blocks, family_id = struct.unpack(b"<IIIIIIII", data[0:HEADER_SIZE])

                if block_no == 0:
                    # Seek back to the start of this block!
                    file.seek(file.tell() - BLOCK_SIZE)
                    # uf2_section_data is a generator but we must return a
                    # list since the file is closed/out of scope.
                    yield section_index, addr, family_id, flags, num_blocks, b"".join(self.uf2_section_data(file))
                    section_index += 1

    def uf2_section_data(self, file):
        count = 0
        while data := file.read(BLOCK_SIZE):
            start0, start1, flags, addr, size, block_no, num_blocks, family_id = struct.unpack(b"<IIIIIIII", data[0:HEADER_SIZE])

            if block_no == 0 and count > 0:
                # We've run into the next section...
                # Seek back to the start of this block!
                file.seek(file.tell() - BLOCK_SIZE)
                break

            yield data[HEADER_SIZE:HEADER_SIZE + DATA_SIZE]

            count += 1


class PyDecl:
    def __init__(self, file, debug=False):
        self.entry_parsers = {
            TYPE_ID_AND_INT: self._parse_type_id_and_int,
            TYPE_ID_AND_STRING: self._parse_type_id_and_str,

            TYPE_BLOCK_DEVICE: self._parse_block_device,

            TYPE_NAMED_GROUP: self._parse_named_group,

            TYPE_PINS_WITH_FUNC: self._parse_pins_with_func,
            TYPE_PINS_WITH_NAME: self._parse_pins_with_name,
        }

        self.file = file
        self.debug = debug

    def parse(self):
        self.file.seek(0)

        self.read_until(BI_MAGIC)

        data = self.read_until(BI_END)

        if len(data) != 12:
            return None

        entries_start, entries_end, mapping_table = struct.unpack("III", data)

        if self.debug:
            print(f"entries: {entries_start:04x} to {entries_end:04x}, mapping: {mapping_table:04x}")

        # Convert our start and end positiont to block relative
        entries_start = self.addr_to_bin_offset(entries_start)
        entries_end = self.addr_to_bin_offset(entries_end)
        entries_bytes_len = entries_end - entries_start
        entries_len = entries_bytes_len // 4

        if self.debug:
            print(f"Found {entries_len} entries from {entries_start} to {entries_end}, len {entries_bytes_len}...")

        self.file.seek(entries_start)
        data = self.file.read(entries_bytes_len)

        if len(data) != entries_bytes_len:
            return None

        entries = struct.unpack("I" * entries_len, data)

        if self.debug:
            print(" ".join([f"{entry:04x}" for entry in entries]))

        parsed = {}

        for entry in entries:
            entry_offset = self.addr_to_bin_offset(entry)

            self.file.seek(entry_offset)

            if self.debug:
                print(f"Entry {entry:04x} should be at offset {entry_offset}...")

            if (entry := self.parse_entry()) is not None:
                k, v = entry
                if k in parsed:
                    if k == "Pins":
                        parsed[k].update(v)
                        continue
                    if isinstance(parsed[k], list):
                        parsed[k] += [v]
                    else:
                        parsed[k] = [parsed[k], v]
                else:
                    # Coerce some things into a list, even if there's one entry,
                    # so the output dict is predictable.
                    parsed[k] = [v] if k in ALWAYS_A_LIST else v

        # Ugly hack to move data inside the respective named group...
        if "NamedGroup" in parsed:
            for group in parsed["NamedGroup"]:
                if group["id"] in parsed:
                    group["data"] = parsed[group["id"]]
                    del parsed[group["id"]]

        return parsed

    def addr_to_bin_offset(self, addr):
        return addr - FLASH_START_ADDR

    def bin_offset_to_addr(self, offset):
        return offset + FLASH_START_ADDR

    def data_type_to_str(self, data_type):
        try:
            return TYPES[data_type]
        except KeyError:
            return "Unknown"

    def data_id_to_str(self, data_id):
        try:
            return IDS[data_id]
        except KeyError:
            return "Unknown"

    def is_valid_data_id(self, data_id):
        return data_id in IDS.keys()

    def data_id_to_typename(self, data_id):
        return self.data_id_to_str(data_id).replace(" ", "")

    def _read_until(self, delimiter=b"\x00"):
        while (chunk := self.file.read(len(delimiter))) != delimiter:
            yield chunk

    def read_until(self, delimiter=b"\x00"):
        return b"".join(self._read_until(delimiter))

    def lookup_string(self, address):
        offset = self.addr_to_bin_offset(address)
        self.file.seek(offset)
        data = self.read_until(delimiter=b"\x00")
        return data.decode("utf-8")

    def _parse_type_id_and_int(self, tag):
        data_id_maybe, data_value = struct.unpack("<II", self.file.read(8))

        if self.debug:
            print(f"{tag}: {self.data_id_to_str(data_id_maybe)} ({data_id_maybe:02x}) ({self.data_type_to_str(TYPE_ID_AND_INT)}): {data_value}")

        if self.is_valid_data_id(data_id_maybe):
            return self.data_id_to_typename(data_id_maybe), data_value
        else:
            return data_id_maybe, data_value

    def _parse_type_id_and_str(self, tag):
        data_id_maybe, str_addr = struct.unpack("<II", self.file.read(8))
        data_value = self.lookup_string(str_addr)

        if self.debug:
            print(f"{tag}: {self.data_id_to_str(data_id_maybe)} ({data_id_maybe:02x}) ({self.data_type_to_str(TYPE_ID_AND_STRING)}): {data_value}")

        if self.is_valid_data_id(data_id_maybe):
            return self.data_id_to_typename(data_id_maybe), data_value
        else:
            return data_id_maybe, data_value

    def _parse_block_device(self, tag):
        name_addr, start_addr, size, more_info_addr, flags = struct.unpack("<IIIIH", self.file.read(18))
        name = self.lookup_string(name_addr)

        if self.debug:
            print(f"{tag}: Block Device: {name} 0x{start_addr:04x} {size / 1024.0:0.2f}k")

        if more_info_addr:
            pass

        return "BlockDevice", {"name": name, "address": start_addr, "size": size, "flags": flags}

    def _parse_named_group(self, tag):
        parent_id, flags, group_tag, group_id, label_addr = struct.unpack("<IHHII", self.file.read(16))
        label = self.lookup_string(label_addr)

        return "NamedGroup", {"label": label, "parent": parent_id, "flags": flags, "tag": group_tag, "id": group_id}

    def _parse_pins_with_func(self, tag):
        pin_encoding = struct.unpack("<I", self.file.read(4))[0]
        encoding_type = pin_encoding & 0b111
        func = (pin_encoding & 0b1111000) >> 3
        func_name = GPIO_FUNCS.get(func)

        pin_encoding >>= 7
        pins = []

        if encoding_type == 0b001:    # Individual pins
            for _ in range(5):
                pins.append(pin_encoding & 0b11111)
                pin_encoding >>= 5
        elif encoding_type == 0b010:  # Range of pins
            pin_end = pin_encoding & 0b11111
            pin_start = (pin_encoding >> 5) & 0b11111
            pins = list(range(pin_start, pin_end + 1))

        result = {}
        for pin in pins:
            result[pin] = {"function": func_name}

        return "Pins", result

    def _parse_pins_with_name(self, tag):
        pin_mask, name_addr = struct.unpack("<II", self.file.read(8))
        name = self.lookup_string(name_addr)
        pin_no = bin(pin_mask)[::-1].index("1")  # YOLO
        return "Pins", {pin_no: {"name": name}}

    def parse_entry(self, include_tags=("RP", "MP")):
        data_type, tag = struct.unpack("<H2s", self.file.read(4))

        if tag.decode("utf-8") in include_tags:
            try:
                return self.entry_parsers[data_type](tag)
            except KeyError:
                if self.debug:
                    sys.stderr.write(f"ERROR: No parser found for: {self.data_type_to_str(data_type)}\n")


if __name__ == "__main__":
    import argparse
    import pathlib

    def valid_file(suffixes):
        def _valid_file(file):
            file = pathlib.Path(file)
            if not file.exists():
                raise argparse.ArgumentTypeError(f"{file} does not exist!")
            if file.suffix.lower() not in suffixes:
                raise argparse.ArgumentTypeError(f"{file.suffix.lower()} format not supported!")
            return file if file.exists() else None
        return _valid_file

    def print_size(size_bytes):
        if size_bytes >= 10486:
            return f"{size_bytes / 1024 / 1024:.2f}MB"
        return f"{size_bytes / 1024:.2f}Kb"

    class BlockDevice:
        def __init__(self, name, address, size, flags):
            self.name = name
            self.address = address
            self.size = size
            self.flags = flags

        def __lt__(self, other):
            return self.address < other.address

        def __repr__(self):
            perms = []
            if self.flags & BINARY_INFO_BLOCK_DEV_FLAG_READ:
                perms.append("read")
            if self.flags & BINARY_INFO_BLOCK_DEV_FLAG_WRITE:
                perms.append("write")
            if self.flags & BINARY_INFO_BLOCK_DEV_FLAG_REFORMAT:
                perms.append("reformat")
            return f"{self.name}: 0x{self.address:04x} {print_size(self.size)} ({", ".join(perms)})"

    parser = argparse.ArgumentParser()
    parser.add_argument("--verify", action="store_true", default=False, help="Perform basic verification.")
    parser.add_argument("--to-json", action="store_true", default=False, help="Output data as JSON.")
    parser.add_argument("--debug", action="store_true", default=False, help="Verbose debug output.")
    parser.add_argument("files", type=valid_file(('.uf2', '.bin')), nargs="+", help="Files to parse.")
    args = parser.parse_args()

    validation_errors = False

    for filename in args.files:
        print(f"\nProcessing: {filename}")

        py_decl = PyDecl(UF2Reader(filename) if filename.suffix.lower() == '.uf2' else open(filename, "rb"), debug=args.debug)
        parsed = py_decl.parse()

        if parsed is None:
            sys.stderr.write(f"ERROR: Failed to parse {filename}\n")
            continue

        if args.to_json:
            print(json.dumps(parsed, indent=4))

        if args.verify:
            binary_end = parsed.get("BinaryEndAddress", 0)
            block_devices = [BlockDevice(**args) for args in parsed.get("BlockDevice", [])]

            print(f"\nFound {len(block_devices)} block device(s):")
            for block_device in block_devices:
                print(block_device)

            # We only need to check the first block device for overlaps
            # this is the one with the lowest address, min uses __lt__
            block_device = min(block_devices)
            print(f"\nChecking {block_device.name}:")

            if block_device.address < binary_end:
                overlap = binary_end - block_device.address
                sys.stderr.write("CRITICAL ERROR: Block device / binary overlap!\n")
                sys.stderr.write(f"Overlap: {overlap:,} bytes, ({print_size(overlap)})\n")
                sys.stderr.write(f"Binary ends at 0x{binary_end:04x}, block device starts at 0x{block_device.address:04x}.\n")
                validation_errors = True
            else:
                remaining = block_device.address - binary_end
                print(f"Remaining: {remaining:,} bytes, ({print_size(remaining)})")
                print(f"Binary ends at 0x{binary_end:04x}, block device starts at 0x{block_device.address:04x}.")

    print("")

    sys.exit(1 if validation_errors else 0)
