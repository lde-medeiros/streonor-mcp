"""Fail-fast advisory locks shared by cooperating MCP processes."""
from contextlib import contextmanager
from functools import wraps
import inspect
import os
from pathlib import Path
import threading

_threads = threading.RLock()
_held = threading.local()


@contextmanager
def edit_lock(directory):
    path = Path(directory).resolve() / '.streonor-mcp.lock'
    with _threads:
        held = getattr(_held, 'paths', set())
        if path in held:
            yield
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
        locked = False
        try:
            if os.name == 'nt':
                import msvcrt
                if os.fstat(fd).st_size == 0:
                    os.write(fd, b'0')
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            locked = True
            _held.paths = held | {path}
            yield
        except OSError as error:
            if not locked:
                raise RuntimeError('Another MCP process is editing; retry after it finishes') from error
            raise
        finally:
            if locked:
                _held.paths = held
                if os.name == 'nt':
                    os.lseek(fd, 0, os.SEEK_SET)
                    msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)


def serialized_profile_edit(function):
    signature = inspect.signature(function)

    @wraps(function)
    def guarded(*args, **kwargs):
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()
        with edit_lock(bound.arguments['root']):
            return function(*args, **kwargs)
    return guarded
