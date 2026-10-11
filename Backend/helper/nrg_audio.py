"""Extract standard Nero NRG Audio CD tracks into lossless, playable WAV files.

NRG images put their track descriptors at the end of the file.  DAOI/DAOX
(disc-at-once) and ETNF/ETN2 (track-at-once) describe the byte ranges of the
tracks; audio sectors contain 44.1 kHz, stereo, signed 16-bit PCM.  ISO
conversion is deliberately not used, since ISO cannot represent CD-DA tracks.
"""

from pathlib import Path
import binascii
import re
import struct

_MAX_CDTEXT_BYTES = 8 * 256 * 18


class NRGError(ValueError):
    """The image is malformed or uses an unsupported NRG audio layout."""


def _decode_cdtext(value: bytes, encoding: str) -> str:
    if value in (b"\t", b"\t\t", b"\0\t"):
        return "\t"  # CD-TEXT abbreviation: same value as preceding track.
    try:
        # Some software writes UTF-8 even though the standard says Latin-1.
        if encoding == "latin-1":
            try:
                text = value.decode("utf-8")
            except UnicodeDecodeError:
                text = value.decode("latin-1")
        else:
            text = value.decode(encoding)
        text = text.strip()
    except (LookupError, UnicodeDecodeError):
        return ""
    return text if all(char.isprintable() for char in text) else ""


def _parse_cdtext(payload: bytes) -> dict[int, dict]:
    """Parse CD-TEXT title/performer packs (18 bytes each) from a NRG CDTX chunk.

    Pack text is NUL-separated and may cross pack boundaries; track 0 holds
    album metadata. Block 0 is preferred over alternate language blocks.
    """
    if not payload or len(payload) % 18 or len(payload) > _MAX_CDTEXT_BYTES:
        return {}

    text_packs: dict[tuple[int, int], list] = {}
    charsets = {}
    seen = set()
    for index in range(0, len(payload), 18):
        pack = payload[index:index + 18]
        kind, track, sequence, descriptor = pack[:4]
        block = (descriptor >> 4) & 7
        # Some image writers omit CRC (zero). Reject damaged nonzero CRCs.
        crc = struct.unpack(">H", pack[16:])[0]
        if crc and crc != (binascii.crc_hqx(pack[:16], 0) ^ 0xffff):
            continue
        identity = (block, kind, sequence)
        if identity in seen:
            continue
        seen.add(identity)
        if kind == 0x8F and track == 0:
            charsets[block] = {0: "latin-1", 1: "latin-1", 0x80: "shift_jis"}.get(pack[4])
        elif kind in (0x80, 0x81) and track <= 99:
            text_packs.setdefault((block, kind), []).append(
                (sequence, track, descriptor & 15, pack[4:16], bool(descriptor & 0x80))
            )

    blocks = sorted({block for block, _ in text_packs})
    for block in blocks:
        album = {}
        tracks: dict[int, dict] = {}
        encoding = charsets.get(block, "latin-1")
        if encoding is None:
            continue
        for kind, field in ((0x80, "title"), (0x81, "artist")):
            current_track = None
            pending = bytearray()
            previous_sequence = -1
            previous_double_byte = False
            valid = False
            for sequence, first_track, position, content, double_byte in sorted(text_packs.get((block, kind), [])):
                continuing = (bool(pending) and current_track == first_track
                              and sequence == previous_sequence + 1
                              and double_byte == previous_double_byte and position > 0)
                if not continuing:
                    current_track = first_track
                    pending.clear()
                    # A continuation without its beginning must not become a title.
                    valid = position == 0
                previous_sequence = sequence
                previous_double_byte = double_byte
                step = 2 if double_byte else 1
                for pos in range(0, len(content), step):
                    char = content[pos:pos + step]
                    if char != b"\0" * step:
                        pending.extend(char)
                        continue
                    value = _decode_cdtext(bytes(pending), encoding) if valid else ""
                    if value:
                        if value == "\t":
                            previous = tracks.get(current_track - 1, {}).get(field, "")
                            value = previous
                        if value and current_track == 0:
                            album[field] = value
                        elif value and 1 <= current_track <= 99:
                            tracks.setdefault(current_track, {})[field] = value
                    pending.clear()
                    current_track += 1
                    valid = True

        if album or tracks:
            # Track 0 is disc metadata. Never use the album title as a song title.
            disc_info = {}
            if album.get("title"):
                disc_info["album"] = album["title"]
            if album.get("artist"):
                disc_info["artist"] = album["artist"]
            return {0: disc_info, **tracks}
    return {}


def read_nrg_cdtext(image_path: str) -> dict[int, dict]:
    """Return track CD-TEXT from Nero images, or {} if it is absent/unsupported."""
    try:
        with open(image_path, "rb") as source:
            source.seek(0, 2)
            size = source.tell()
            if size < 16:
                return {}
            source.seek(-12, 2)
            footer = source.read(12)
            if footer[:4] == b"NER5":
                start, end = struct.unpack(">Q", footer[4:])[0], size - 12
            elif footer[4:8] == b"NERO":
                start, end = struct.unpack(">I", footer[8:])[0], size - 8
            else:
                return {}
            if start <= 0 or start >= end:
                return {}
            pos = start
            for _ in range(10000):
                if pos + 8 > end:
                    break
                source.seek(pos)
                header = source.read(8)
                kind, length = header[:4], struct.unpack(">I", header[4:])[0]
                pos += 8
                if pos + length > end:
                    break
                if kind == b"END!":
                    break
                if kind == b"CDTX":
                    if length > _MAX_CDTEXT_BYTES:
                        return {}
                    parsed = _parse_cdtext(source.read(length))
                    if not parsed:
                        return {}
                    disc_info = parsed.get(0, {})
                    result = {}
                    for number, *_ in _read_audio_tracks(source):
                        info = {**disc_info, **parsed.get(number, {})}
                        if info:
                            result[number] = {**info, "track": str(number)}
                    return result
                pos += length
    except (OSError, ValueError, struct.error):
        pass
    return {}


def _track_filename(number: int, title: str) -> str:
    """Generate a filesystem-safe track filename, keeping a numeric prefix."""
    clean = re.sub(r'[<>:"/\\|?*\x00-\x1f]', " ", title)
    clean = re.sub(r"\s+", " ", clean).strip(" .")[:110].rstrip(" .")
    return f"{number:02d} - {clean}.wav" if clean else f"Track {number:02d}.wav"


def _wav_info_chunk(metadata: dict) -> bytes:
    """Keep UTF-8 metadata before PCM so the existing RIFF tag reader sees it."""
    payload = b"INFO"
    for key, kind in (("title", b"INAM"), ("artist", b"IART"), ("album", b"IPRD"), ("track", b"ITRK")):
        if metadata.get(key):
            data = metadata[key].encode("utf-8") + b"\0"
            payload += kind + struct.pack("<I", len(data)) + data + b"\0" * (len(data) % 2)
    return b"LIST" + struct.pack("<I", len(payload)) + payload if len(payload) > 4 else b""


def _tracks_from_chunk(kind: bytes, payload: bytes):
    tracks = []
    if kind in (b"DAOI", b"DAOX"):
        # DAO records start after a duplicate chunk length, UPC, TOC and
        # first/last track number. Each record begins with the track's ISRC.
        # Older DAOI writers use either a 22-byte header / 30-byte record
        # (libcdio) or a 24-byte header / 32-byte record (Nero variants).
        shapes = ((22, 30), (24, 32)) if kind == b"DAOI" else ((22, 42),)
        shape = next((
            (header, record, payload[header - 2], payload[header - 1])
            for header, record in shapes
            if len(payload) >= header and (len(payload) - header) % record == 0
            and 1 <= payload[header - 2] <= payload[header - 1] <= 99
            and (len(payload) - header) // record == payload[header - 1] - payload[header - 2] + 1
        ), None)
        if shape is None:
            raise NRGError("Thông tin track DAO trong NRG không hợp lệ.")
        header_size, record_size, first, last = shape
        count = (len(payload) - header_size) // record_size
        for idx in range(count):
            part = payload[header_size + idx * record_size:header_size + (idx + 1) * record_size]
            if kind == b"DAOX":
                sector_size, mode = struct.unpack_from(">HH", part, 12)
                start, end = struct.unpack_from(">QQ", part, 26)
                audio = mode in (0x0700, 0x1000)
            elif record_size == 30:
                sector_size, mode = struct.unpack_from(">HH", part, 12)
                start, end = struct.unpack_from(">II", part, 22)
                audio = mode in (7, 0x0700, 0x1000)
            else:
                sector_size, mode, _pregap, start, end = struct.unpack_from(">IIIII", part, 12)
                audio = mode in (7, 0x0700, 0x1000)
            if audio:
                tracks.append((first + idx, start, end - start, sector_size))

    elif kind in (b"ETNF", b"ETN2"):
        record_size = 20 if kind == b"ETNF" else 32
        if len(payload) % record_size:
            raise NRGError("Thông tin track ETN trong NRG không hợp lệ.")
        for idx in range(len(payload) // record_size):
            part = payload[idx * record_size:(idx + 1) * record_size]
            if kind == b"ETN2":
                offset, length, mode = struct.unpack_from(">QQI", part)
            else:
                offset, length, mode = struct.unpack_from(">III", part)
            if mode == 7:
                tracks.append((idx + 1, offset, length, 2352))
    return tracks


def _read_audio_tracks(source):
    source.seek(0, 2)
    size = source.tell()
    if size < 16:
        raise NRGError("File NRG không có footer hợp lệ.")
    source.seek(-12, 2)
    footer = source.read(12)
    if footer[:4] == b"NER5":
        metadata_start = struct.unpack(">Q", footer[4:])[0]
        footer_start = size - 12
    elif footer[4:8] == b"NERO":
        metadata_start = struct.unpack(">I", footer[8:])[0]
        footer_start = size - 8
    else:
        raise NRGError("File không phải ảnh đĩa Nero NRG hợp lệ (NERO/NER5).")
    if metadata_start <= 0 or metadata_start >= footer_start:
        raise NRGError("Vị trí metadata NRG không hợp lệ.")

    chunks = {}
    pos = metadata_start
    for _ in range(10000):
        if pos + 8 > footer_start:
            raise NRGError("Metadata NRG bị cắt hoặc không có END!.")
        source.seek(pos)
        header = source.read(8)
        kind, length = header[:4], struct.unpack(">I", header[4:])[0]
        pos += 8
        if pos + length > footer_start:
            raise NRGError("Kích thước chunk NRG vượt quá dữ liệu thực tế.")
        if kind == b"END!":
            break
        if kind in (b"DAOX", b"DAOI", b"ETN2", b"ETNF"):
            if length > 1000000:
                raise NRGError("Bảng track NRG quá lớn.")
            chunks.setdefault(kind, []).append(source.read(length))
        pos += length
    else:
        raise NRGError("Quá nhiều chunk NRG.")

    # Prefer disc-at-once records when multiple kinds occur; their offsets
    # include precise index-1 starts, skipping any pregaps.
    for kind in (b"DAOX", b"DAOI", b"ETN2", b"ETNF"):
        if kind in chunks:
            tracks = []
            for payload in chunks[kind]:
                tracks.extend(_tracks_from_chunk(kind, payload))
            if tracks:
                for number, start, length, sector_size in tracks:
                    if not (1 <= number <= 99 and start >= 0 and length > 0
                            and start + length <= metadata_start):
                        raise NRGError("Offset/độ dài track NRG không hợp lệ.")
                    if sector_size not in (2352, 2448) or length % sector_size:
                        raise NRGError("Track Audio CD có kích thước sector không được hỗ trợ.")
                return tracks
    return []


def extract_nrg_audio(image_path: str, output_dir: str) -> list[str]:
    """Return extracted WAV paths; empty means no supported audio track.

    Raise NRGError for a damaged/unsupported image. No partial WAVs remain if
    extraction fails. Uses streaming reads so large disc images fit in memory.
    """
    destination = Path(output_dir)
    created = []
    try:
        with open(image_path, "rb") as source:
            tracks = _read_audio_tracks(source)
            if not tracks:
                return []
            cdtext = read_nrg_cdtext(image_path)
            destination.mkdir(parents=True, exist_ok=True)
            for number, start, length, sector_size in tracks:
                output = destination / _track_filename(number, cdtext.get(number, {}).get("title", ""))
                if output.exists():
                    raise NRGError(f"Trùng số track NRG: {number}.")
                created.append(output)
                source.seek(start)
                sectors_left = length // sector_size
                info_chunk = _wav_info_chunk(cdtext.get(number, {}))
                pcm_length = sectors_left * 2352
                riff_length = 36 + len(info_chunk) + pcm_length
                if riff_length > 0xffffffff:
                    raise NRGError("Track NRG quá lớn cho định dạng WAV RIFF.")
                with open(output, "wb") as wav:
                    wav.write(b"RIFF" + struct.pack("<I", riff_length) + b"WAVEfmt "
                              + struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16)
                              + info_chunk + b"data" + struct.pack("<I", pcm_length))
                    while sectors_left:
                        block_count = min(sectors_left, 256)
                        raw = source.read(block_count * sector_size)
                        if len(raw) != block_count * sector_size:
                            raise NRGError("Dữ liệu âm thanh NRG bị cắt.")
                        if sector_size == 2448:
                            raw = b"".join(raw[i:i + 2352]
                                           for i in range(0, len(raw), 2448))
                        wav.write(raw)
                        sectors_left -= block_count
        return [str(path) for path in created]
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
