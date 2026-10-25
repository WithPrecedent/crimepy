"""Shared fixtures: small NIBRS master files.

Most records are copied from the FBI's master files for 2004 (fixed-length
records, with three batch header records for each agency) and 2025
(variable-length records, with one batch header record). A few are made with
`_record`, from the positions in the FBI's record descriptions, so that the
agencies have populations and monthly activity and an incident has a known
offender and an arrest. The 2004 file is a zip archive compressed with
Deflate, and the 2025 file is compressed with Deflate64, as the CDE
compressed some years.
"""

from __future__ import annotations

import pathlib
import struct
import zipfile
import zlib

import inflate64
import pytest



def _record(start: str, fields: dict[int, str]) -> str:
    """Returns a record from its first characters and fields.

    Args:
        start: the first characters of the record (its segment level and
            more).
        fields: the text of each field, by its first position in the FBI's
            record descriptions (counted from 1).

    Returns:
        The record.

    """
    width = max([len(start), *(p - 1 + len(t) for p, t in fields.items())])
    characters = list(start.ljust(width))
    for position, text in fields.items():
        characters[position - 1:position - 1 + len(text)] = list(text)
    return ''.join(characters)


RECORDS_2004: list[str] = [
    'B101ALAST0000            20050822        ALABAMA HIGHWAY PATROL        AL8D634N         3490005M',
    'B201ALAST0000            000000000      000000000000000000      000000000000000000      000000000000000000      000000000',
    'B301ALAST0000            000000000      000000000  002004',
    _record('B102AZ0111300', {
        26: '20060302', 34: '19960101', 42: 'TEMPE', 72: 'AZ', 74: '2',
        76: '8', 77: '4', 78: '1', 79: 'Y', 89: '3060', 93: '015A',
        97: 'A'}),
    _record('B202AZ0111300', {
        26: '000158880', 35: '013', 38: '090', 41: '000141865'}),
    _record('B302AZ0111300', {
        50: '12', 52: '12', 54: '2004', 58: ' Y ' * 12, 94: '013'}),
    '0102AZ0111300 E0DROSC-2 N20040701R  010010100    N',
    '0202AZ0111300 E0DROSC-2 N20040701220CN  2400F            88',
    '0302AZ0111300 E0DROSC-2 N20040701720000001500',
    '0402AZ0111300 E0DROSC-2 N20040701001220                           B',
    '0502AZ0111300 E0DROSC-2 N2004070100',
    '0102AZ0111300 E0DROSCQ2 N20040701 11010010101    N',
    '0202AZ0111300 E0DROSCQ2 N2004070113BCN  20   N  40       88',
    _record('0402AZ0111300 E0DROSCQ2 N20040701', {
        34: '001', 37: '13B', 67: 'I', 68: '29', 70: 'M', 71: 'W', 72: 'N',
        73: 'R', 79: 'M', 84: '01', 86: 'SE'}),
    _record('0502AZ0111300 E0DROSCQ2 N20040701', {
        34: '01', 36: '31', 38: 'F', 39: 'W'}),
    _record('0602AZ0111300 E0DROSCQ2 N20040701', {
        34: '01', 36: 'E0DROSLT2 N', 48: '20040703', 56: 'T', 57: 'N',
        58: '13B', 61: '01', 67: '31', 69: 'F', 70: 'W', 71: 'N', 72: 'R'}),
    '0702AZ01113001T1M1VF3TX I2004072601    S90D01    18MWNN',
    'W102AZ0111300 T0IRESC12 N20020902 16000000000    B2004120811A',
    'W302AZ0111300 60DROSL62 N        51300000013520040923                                                 220',
    'W602AZ0111300 604AVSC-2 N        01 604AVSC-2 N20041228ON13B01    32MANR N13B']

RECORDS_2025: list[str] = [
    _record('BH50AK0010200000000000000', {
        34: '20210101', 42: 'FAIRBANKS', 72: 'AK', 74: '4', 76: '9', 77: '4',
        78: '1', 79: 'Y', 89: '3030', 93: '020A', 97: 'A', 106: '000031961',
        115: '00', 118: '258', 121: '000000000', 226: '12', 228: '12',
        230: '2025', 234: ' Y ' * 12, 270: '090'}),
    '0150AK0010200C30BRCZ9728N20250301 16010010100    N                                      N',
    '0250AK0010200C30BRCZ9728N2025030113CCN  08   N           88',
    '0450AK0010200C30BRCZ9728N2025030100113C                           I25FWNR          01OK',
    '0550AK0010200C30BRCZ9728N202503010125FIN',
    '0750AK00102000L1G0BRVSCTD2025020301    O90C01    30MINN']


def _pad(records: list[str], width: int | None) -> bytes:
    """Returns records as the text of a master file."""
    lines = [r.ljust(width) if width else r for r in records]
    return ('\r\n'.join(lines) + '\r\n').encode('latin-1')


def write_deflate64_zip(path: pathlib.Path, name: str, data: bytes) -> None:
    """Writes a zip archive with one member compressed with Deflate64."""
    deflater = inflate64.Deflater()
    compressed = deflater.deflate(data) + deflater.flush()
    crc = zlib.crc32(data)
    encoded = name.encode()
    local = struct.pack(
        '<IHHHHHIIIHH', 0x04034B50, 21, 0, 9, 0, 0, crc, len(compressed),
        len(data), len(encoded), 0) + encoded
    central = struct.pack(
        '<IHHHHHHIIIHHHHHII', 0x02014B50, 21, 21, 0, 9, 0, 0, crc,
        len(compressed), len(data), len(encoded), 0, 0, 0, 0, 0, 0) + encoded
    end = struct.pack(
        '<IHHHHIIH', 0x06054B50, 0, 0, 1, 1, len(central),
        len(local) + len(compressed), 0)
    path.write_bytes(local + compressed + central + end)


@pytest.fixture
def data_folder(tmp_path: pathlib.Path) -> pathlib.Path:
    """Returns a data folder with the master files of 2004 and 2025."""
    raw = tmp_path / 'nibrs' / 'raw'
    raw.mkdir(parents = True)
    with zipfile.ZipFile(raw / 'nibrs-2004.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('NIBRS04.ENC', _pad(RECORDS_2004, 132))
    write_deflate64_zip(
        raw / 'nibrs-2025.zip', 'nibrs-2025.txt', _pad(RECORDS_2025, None))
    return tmp_path


@pytest.fixture
def master_2004(data_folder: pathlib.Path) -> pathlib.Path:
    """Returns the path of the 2004 master file."""
    return data_folder / 'nibrs' / 'raw' / 'nibrs-2004.zip'


@pytest.fixture
def master_2025(data_folder: pathlib.Path) -> pathlib.Path:
    """Returns the path of the 2025 master file (compressed with Deflate64)."""
    return data_folder / 'nibrs' / 'raw' / 'nibrs-2025.zip'
