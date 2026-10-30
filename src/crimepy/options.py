"""Default settings of crimepy.

They can be changed for a whole session (for example,
`crimepy.options.DATA_FOLDER = 'D:/crime'`), and every function that uses one
also takes it as an argument.

Contents:
    CHUNK_SIZE: the number of records that are parsed at once.
    DATA_FOLDER: where downloads and converted tables are saved, if not in
        amos's workspace.
    DATA_SUBFOLDER: the folder of the data folder of amos's workspace in
        which they are saved otherwise.
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
# environment variable, if it is set. Otherwise (`None`), they are saved in
# the `DATA_SUBFOLDER` of the data folder of amos's workspace, beside the
# "code" folder (see `utilities.data_folder`), where amos projects look for
# data too.
DATA_FOLDER: pathlib.Path | str | None = os.environ.get('CRIMEPY_DATA')
# The folder of the data folder of amos's workspace in which crimepy saves
# data (so NIBRS is in "data/crime/nibrs").
DATA_SUBFOLDER: str = 'crime'
# Seconds to wait for a server to respond before giving up.
TIMEOUT: float = 60.0
# Sent with every request, since some servers refuse requests without one.
USER_AGENT: str = 'crimepy (https://github.com/WithPrecedent/crimepy)'
