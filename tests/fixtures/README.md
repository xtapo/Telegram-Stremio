`password-album.rar` is a synthetic RAR5 archive created with RAR's `-ma5 -hp`
options (encrypted file names). It contains only `track.wav`, whose test bytes
are `b"RIFF" + b"archive password regression test\n" * 4`, not a playable song.

The test password is ` album pass;$ `, including the leading and trailing spaces.
This fixture contains no user data or real credentials.
