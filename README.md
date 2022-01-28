# MtHasher

Calculate multiple hash digests for a piece of data in parallel, one algo/thread.

Based on the code of Peter Wu <peter@lekensteyn.nl> (https://git.lekensteyn.nl/scripts/tree/digest.py).

# Usage

## From CLI

Add data over STDIN and/or as arguments and select the desired algorithms:

```bash
cat data.txt | python3 -m mthasher -i data2.txt - --sha1 --sha256 -o checksums.txt
```

At least one algorithm is mandatory and by default the script reads from STDIN and writes to STDOUT.

## From Python

### The exposed API is the following

- `ALGORITHMS_GUARANTEED`: The tuple of the supported algorithms
- `Hasher()`: Single-threaded hasher, takes an iterable (e.g. list of algorithms to use)
- `MtHasher()` Multi-threaded hasher, takes an iterable (e.g. list of algorithms to use)

### Both hashers expose the following API

- `header`: tuple of header elements ("filename" and the list of algorithms in the supplied order)
- `algos`: tuple of supplied algorithms
- `hash_file()`: Takes a filename or a file-like object on bytes, returns the digest tuple in same order as header (the filename is omited)
- `hash_multiple_files()`:Takes an iterable of filenames or file-like objects on bytes,returns the generator of filename + digest tuples in same order as header, one for every input object

### Example

```python
from io import BytesIO

from mthasher import MtHasher

hasher = MtHasher(('sha1', 'md5'))
filename_header, sha1_header, md5_header = hasher.header
sha1_digest, md5_digest = hasher.hash_file('data.txt')
for filename, sha1_digest, md5_digest in hasher.hash_multiple_files(('data.txt', open('data2.txt', 'rb'), '-', BytesIO('bytesstring'))):
    # First the header and then the digests
    print(filename, sha1_digest, md5_digest, sep='\t')
```

## Supported algorithms

- md5
- sha1
- sha224
- sha256
- sha384
- sha512
- sha3_224
- sha3_256
- sha3_384
- sha3_512
- blake2b
- blake2s

# License

Licensed under the MIT license <http://opensource.org/licenses/MIT>
