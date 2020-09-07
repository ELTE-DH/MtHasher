#!/usr/bin/env python
# Calculate (multiple) digest(s) for file(s)
#
# Author: Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>
# Original source: https://git.lekensteyn.nl/scripts/tree/digest.py

import sys
import hashlib
from threading import Thread
from queue import Queue


def read_blocks(filename):
    if filename == '-':
        f = sys.stdin.buffer  # read binary instead of unicode
    else:
        f = open(filename, 'rb')
    try:
        megabyte = 2 ** 20
        data = f.read(megabyte)
        while len(data) > 0:
            yield data
            data = f.read(megabyte)
    finally:
        f.close()


class Hasher(object):
    """Calculate multiple hash digests for a piece of data"""

    def __init__(self, algos):
        self.algos = algos
        self._hashes = {}
        for algo in self.algos:
            self._hashes[algo] = getattr(hashlib, algo)()

    def update(self, data):
        for h in self._hashes:
            h.update(data)

    def header(self):
        """First element is the filename, then come the names of the algos"""

        algos = list(self.algos)
        algos.insert(0, 'filename')
        return tuple(algos)

    def hexdigests(self):
        """Returns the calculated hex digests"""

        return (self._hashes[algo].hexdigest() for algo in self.algos)


class MtHasher(Hasher):
    QUEUE_SIZE = 10  # Queue size. Memory usage is this times block size (1M)

    def __init__(self, algos):
        super(MtHasher, self).__init__(algos)
        self._queues = {}
        self._threads = {}
        for algo in algos:
            t = Thread(target=self._queue_updater, args=(algo,), name=algo)
            self._queues[algo] = Queue(MtHasher.QUEUE_SIZE)
            self._threads[algo] = t
            t.start()

    def _queue_updater(self, algo):
        q = self._queues[algo]
        h = self._hashes[algo]
        data = q.get()
        while len(data) > 0:  # Treat an empty value as terminator
            h.update(data)
            data = q.get()

    def update(self, data):
        if len(data) > 0:
            for q in self._queues.values():
                q.put(data)

    def hexdigests(self):
        """Wait until all calculations are done and yield the results in meantime"""

        for algo in self.algos:
            q = self._queues[algo]
            q.put(b'')  # Terminate
            self._threads[algo].join()
            assert q.empty()
        return super(MtHasher, self).hexdigests()


# All guaranteed, except varable length hashes...
algorithms_guaranteed = hashlib.algorithms_guaranteed - {'shake_128', 'shake_256'}


def print_usage():
    dgst_opts = ' '.join('[-{0}]'.format(algo) for algo in algorithms_guaranteed)
    print(f'Usage: python {sys.argv[0]} {dgst_opts} [FILE]...', file=sys.stderr)


def main(*argv):
    filenames = []
    algos = set()

    # TODO argparse
    if any(help_arg in argv for help_arg in ('-h', '--help')):
        print_usage()
        return 1

    for arg in argv:
        if arg.startswith('-') and arg != '-':
            algo = arg.lstrip('-')  # Strip leading '-'
            if algo in algorithms_guaranteed:  # Preserve ordering, ignore duplicates
                algos.add(algo)
            else:
                print('Unsupported algo:', algo, file=sys.stderr)
        else:
            filenames.append(arg)

    if len(algos) == 0:
        print('Missing digest!', file=sys.stderr)
        print_usage()
        return 1

    if len(filenames) == 0:
        filenames.append('-')  # Assume stdin if no file is given

    for filename in filenames:  # Calculate digest(s) for each file
        hasher = MtHasher(algos)
        try:  # Try to read the file and update the hash states
            for data in read_blocks(filename):
                hasher.update(data)
        except OSError as e:
            print('digest: ', filename, ': ', e.strerror, sep='')
            continue

        print(*hasher.header())
        print(filename, *hasher.hexdigests(), sep='\t')


if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
