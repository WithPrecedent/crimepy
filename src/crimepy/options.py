"""Default settings of crimepy.

They can be changed for a whole session (for example,
`crimepy.options.DATA_FOLDER = 'D:/crime'`), and every function that uses one
also takes it as an argument.

Contents:
    CHUNK_SIZE: the number of records that are parsed at once.
    DATA_FOLDER: where downloads and converted tables are saved.
    TIMEOUT: seconds to wait for a server before giving up.
    USER_AGENT: how crimepy introduces itself to servers.

"""

from __future__ import annotations

import os
import pathlib

# The number of records of a master file that are parsed at once. A NIBRS
# master file has tens of millions of records, so they are parsed in chunks to
# limit the memory used. Larger chunks are a little faster and use more
# memory (about 1 GB for 2 million records).
CHUNK_SIZE: int = 1_000_000
# Where downloads and converted tables are saved: the "CRIMEPY_DATA"
# environment variable, if it is set, and otherwise a "crimepy_data" folder in
# the user's home folder.
DATA_FOLDER: pathlib.Path | str = os.environ.get(
    'CRIMEPY_DATA', pathlib.Path.home() / 'crimepy_data')
# Seconds to wait for a server to respond before giving up.
TIMEOUT: float = 60.0
# Sent with every request, since some servers refuse requests without one.
USER_AGENT: str = 'crimepy (https://github.com/WithPrecedent/crimepy)'
