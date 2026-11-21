"""Read staged Windows UDF images using libudfread's public API."""

from contextlib import contextmanager
import ctypes as c

from studio_device_safety import UnsafeTarget


class DirectoryEntry(c.Structure):
    _fields_ = [('kind', c.c_uint), ('name', c.c_char_p)]


class UdfReader:
    def __init__(self):
        self.api = c.CDLL('libudfread.so.0')
        handle = c.c_void_p
        for name, output, inputs in (
            ('init', handle, []),
            ('open', c.c_int, [handle, c.c_char_p]),
            ('close', None, [handle]),
            ('opendir', handle, [handle, c.c_char_p]),
            ('readdir', c.POINTER(DirectoryEntry), [handle, c.POINTER(DirectoryEntry)]),
            ('closedir', None, [handle]),
            ('file_open', handle, [handle, c.c_char_p]),
            ('file_close', None, [handle]),
            ('file_size', c.c_int64, [handle]),
            ('file_read', c.c_ssize_t, [handle, handle, c.c_size_t]),
        ):
            function = getattr(self.api, 'udfread_' + name)
            function.restype = output
            function.argtypes = inputs
        self.volume = None

    @contextmanager
    def open(self, snapshot):
        self.volume = self.api.udfread_init()
        if not self.volume:
            raise UnsafeTarget('Could not initialize the Windows ISO reader.')
        try:
            if self.api.udfread_open(self.volume, f'/proc/self/fd/{snapshot.fileno()}'.encode()) < 0:
                raise UnsafeTarget('Could not read the Windows ISO UDF volume. Verify its SHA-256 or download a fresh copy.')
            yield self
        finally:
            self.api.udfread_close(self.volume)
            self.volume = None

    def walk(self):
        pending = ['/']
        while pending:
            path = pending.pop()
            directory = self.api.udfread_opendir(self.volume, path.encode())
            if not directory:
                raise UnsafeTarget('Could not read a directory in the Windows ISO.')
            directories, files = [], []
            try:
                entry = DirectoryEntry()
                while self.api.udfread_readdir(directory, c.byref(entry)):
                    if entry.name in (b'.', b'..'):
                        continue
                    if entry.kind not in (1, 2) or not entry.name:
                        raise UnsafeTarget('The Windows ISO contains an unsupported UDF entry.')
                    try:
                        name = entry.name.decode()
                    except UnicodeDecodeError as exc:
                        raise UnsafeTarget('The Windows ISO contains an unsupported UDF filename.') from exc
                    (directories if entry.kind == 1 else files).append(name)
                    if len(directories) + len(files) > 100000:
                        raise UnsafeTarget('The Windows installer ISO has too many files.')
            finally:
                self.api.udfread_closedir(directory)
            # The caller validates names before traversal resumes.
            yield path, directories, files
            pending.extend(path.rstrip('/') + '/' + name for name in directories)

    @contextmanager
    def open_file(self, path):
        handle = self.api.udfread_file_open(self.volume, path.encode())
        if not handle:
            raise UnsafeTarget('Could not open a file in the Windows ISO.')
        try:
            yield handle
        finally:
            self.api.udfread_file_close(handle)

    def size(self, path):
        with self.open_file(path) as handle:
            return self.api.udfread_file_size(handle)

    def copy(self, path, output):
        with self.open_file(path) as handle:
            buffer = c.create_string_buffer(1024 * 1024)
            while output.remaining:
                count = self.api.udfread_file_read(handle, buffer, min(len(buffer), output.remaining))
                if count <= 0:
                    raise UnsafeTarget('Could not read the complete file from the Windows ISO.')
                output.write(buffer[:count])
