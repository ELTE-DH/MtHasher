#!/usr/bin/env python3
# Calculate (multiple) digest(s) for file(s)
#
# Original Author: Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>
# Original source: https://git.lekensteyn.nl/scripts/tree/digest.py
# This version of the code is available at: https://github.com/ELTE-DH/mthasher/

import sys
import hashlib
from io import BufferedReader, BytesIO
from threading import Thread
from queue import Queue


# All guaranteed, except variable length hashes...
ALGORITHMS_GUARANTEED = tuple(sorted(hashlib.algorithms_guaranteed - {'shake_128', 'shake_256'}))


class Hasher:
    """Calculate multiple hash digests for a piece of data"""

    def __init__(self, algos=ALGORITHMS_GUARANTEED):
        if not set(algos).issubset(ALGORITHMS_GUARANTEED) or len(set(algos)) != len(algos):
            raise ValueError(f'The provided algorithms should not contain duplicates and '
                  f'must be a subset of {ALGORITHMS_GUARANTEED}!')
        header = list(algos)
        header.insert(0, 'filename')
        self.header = tuple(header)  # First element is the filename, then come the names of the algos
        self.algos = tuple(header[1:])

        self._hashers = {}
        self._init_hashers()

    def _init_hashers(self):
        self._hashers = {}
        for algo in self.algos:
            self._hashers[algo] = getattr(hashlib, algo)()

    def _update(self, data):
        for h in self._hashers.values():
            h.update(data)

    def _hexdigests(self):
        """Returns the calculated hex digests"""

        return tuple(self._hashers[algo].hexdigest() for algo in self.algos)

    @staticmethod
    def _read_blocks(input_data, size=2**20):
        """Read (one megabyte) blocks from a bytestream, STDIN or file"""

        if isinstance(input_data, (BufferedReader, BytesIO)):
            f = input_data
            opened = False
        elif input_data == '-':
            f = sys.stdin.buffer  # read binary instead of unicode
            opened = False
        else:
            f = open(input_data, 'rb')
            opened = True

        try:

            data = f.read(size)
            while len(data) > 0:
                yield data
                data = f.read(size)
        finally:
            if opened:
                f.close()

    def hash_file(self, filename_or_bytestream):
        """Try to read the file or bytestream and update the hash states"""

        try:
            for data in self._read_blocks(filename_or_bytestream):
                self._update(data)
        except OSError as e:
            print('digest: ', filename_or_bytestream, ': ', e.strerror, sep='', file=sys.stderr)
            return None
        return self._hexdigests()

    def hash_multiple_files(self, inputs):
        """Hash multiple files sequentially. Yield the header then a filename and digests tuple for each file"""

        yield self.header
        for filename_or_bytestream in inputs:  # Calculate digest(s) for each file
            digests = self.hash_file(filename_or_bytestream)
            if digests is not None:
                yield filename_or_bytestream, *digests


class MtHasher(Hasher):
    """Calculate multiple hash digests for a piece of data in parallel, one algo/thread"""

    QUEUE_SIZE = 10  # Queue size. Memory usage is this times block size (1M)

    def __init__(self, algos=ALGORITHMS_GUARANTEED):
        super(MtHasher, self).__init__(algos)
        self._queues = {}
        self._threads = {}

    def _init_threads(self):
        """Clear hashers, queues and threads and init clean instances"""

        self._init_hashers()
        self._queues = {}
        self._threads = {}

        for algo in self.algos:
            t = Thread(target=self._queue_updater, args=(algo,), name=algo)
            self._queues[algo] = Queue(MtHasher.QUEUE_SIZE)
            self._threads[algo] = t
            t.start()

    def _queue_updater(self, algo):
        q = self._queues[algo]
        h = self._hashers[algo]
        data = q.get()
        while len(data) > 0:  # Treat an empty value as terminator
            h.update(data)
            data = q.get()

    def _update(self, data):
        """Put chunks from hash_file() into the queues"""
        if len(data) > 0:
            for q in self._queues.values():
                q.put(data)

    def _hexdigests(self):
        """Wait until all calculations are done and yield the results in meantime"""

        for algo in self.algos:
            q = self._queues[algo]
            q.put(b'')  # Terminate
            self._threads[algo].join()
            assert q.empty()
        return super(MtHasher, self)._hexdigests()

    def hash_file(self, filename_or_bytestream):
        """Init the threads and calls Hasher.hash_file() for the hashing"""
        self._init_threads()
        return super(MtHasher, self).hash_file(filename_or_bytestream)
