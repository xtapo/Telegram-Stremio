"""Extract standard Nero NRG Audio CD tracks into lossless, playable WAV files.

NRG images put their track descriptors at the end of the file.  DAOI/DAOX
(disc-at-once) and ETNF/ETN2 (track-at-once) describe the byte ranges of the
tracks; audio sectors contain 44.1 kHz, stereo, signed 16-bit PCM.  ISO
conversion is deliberately not used, since ISO cannot represent CD-DA tracks.
"""

from pathlib import Path
import struct
import wave


class NRGError(ValueError):
    """The image is malformed or uses an unsupported NRG audio layout."""


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
            destination.mkdir(parents=True, exist_ok=True)
            for number, start, length, sector_size in tracks:
                output = destination / f"Track {number:02d}.wav"
                if output.exists():
                    raise NRGError(f"Trùng số track NRG: {number}.")
                created.append(output)
                source.seek(start)
                sectors_left = length // sector_size
                with wave.open(str(output), "wb") as wav:
                    wav.setnchannels(2)
                    wav.setsampwidth(2)
                    wav.setframerate(44100)
                    while sectors_left:
                        block_count = min(sectors_left, 256)
                        raw = source.read(block_count * sector_size)
                        if len(raw) != block_count * sector_size:
                            raise NRGError("Dữ liệu âm thanh NRG bị cắt.")
                        if sector_size == 2448:
                            raw = b"".join(raw[i:i + 2352]
                                           for i in range(0, len(raw), 2448))
                        wav.writeframesraw(raw)
                        sectors_left -= block_count
        return [str(path) for path in created]
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
