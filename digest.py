#!/usr/bin/env python
# Calculate (multiple) digest(s) for file(s)
#
# Author: Peter Wu <peter@lekensteyn.nl>
# Licensed under the MIT license <http://opensource.org/licenses/MIT>

from __future__ import print_function
import hashlib
import sys
from threading import Thread
try:
    from queue import Queue
except:
    # Python 2 compatibility
    from Queue import Queue

def read_blocks(filename):
    if filename == '-':
        f = sys.stdin
        # Python 3 compat: read binary instead of unicode
        if hasattr(f, 'buffer'):
            f = f.buffer
    else:
        f = open(filename, 'rb')
    try:
        megabyte = 2 ** 20
        while True:
            data = f.read(megabyte)
            if not data:
                break
            yield data
    finally:
        f.close()

class Hasher(object):
    '''Calculate multiple hash digests for a piece of data.'''
    def __init__(self, algos):
        self.algos = algos
        self._hashes = {}
        for algo in self.algos:
            self._hashes[algo] = getattr(hashlib, algo)()

    def update(self, data):
        for h in self._hashes:
            h.update(data)

    def hexdigests(self):
        '''Yields the algorithm and the calculated hex digest.'''
        for algo in self.algos:
            digest = self._hashes[algo].hexdigest()
            yield algo, digest

class MtHasher(Hasher):
    # Queue size. Memory usage is this times block size (1M)
    QUEUE_SIZE = 10
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
        while True:
            data = q.get()
            # Treat an empty value as terminator
            if not data:
                break
            h.update(data)

    def update(self, data):
        if data:
            for q in self._queues.values():
                q.put(data)

    def hexdigests(self):
        # Wait until all calculations are done and yield the results in meantime
        for algo in self.algos:
            q = self._queues[algo]
            q.put(b'') # Terminate
            self._threads[algo].join()
            assert q.empty()
        return super(MtHasher, self).hexdigests()

try:
    supported_algos = hashlib.algorithms_guaranteed
except:
    supported_algos = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512')

def print_usage():
    dgst_opts = ' '.join('[-{0}]'.format(algo) for algo in supported_algos)
    print('Usage: python digest.py {} [FILE]...'.format(dgst_opts),
          file=sys.stderr)

def main(*argv):
    filenames = []
    algos = []

    if any(help_arg in argv for help_arg in ('-h', '--help')):
        print_usage()
        return 1

    for arg in argv:
        if arg.startswith('-') and arg != '-':
            algo = arg.lstrip('-')  # Strip leading '-'
            if algo in supported_algos:
                # Preserve ordering, ignore duplicates
                if not algo in algos:
                    algos.append(algo)
            else:
                print('Unsupported algo:', algo, file=sys.stderr)
        else:
            filenames.append(arg)

    if not algos:
        print('Missing digest!', file=sys.stderr)
        print_usage()
        return 1

    # Assume stdin if no file is given
    if not filenames:
        filenames.append('-')

    # Calculate digest(s) for each file
    for filename in filenames:
        hasher = MtHasher(algos)

        # Try to read the file and update the hash states
        try:
            for data in read_blocks(filename):
                hasher.update(data)
        except OSError as e:
            print('digest: {0}: {1}'.format(filename, e.strerror))
            continue

        for algo, digest in hasher.hexdigests():
            print('{0}  {1}'.format(digest, filename))

if __name__ == '__main__':
    sys.exit(main(*sys.argv[1:]))
