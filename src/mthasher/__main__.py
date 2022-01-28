#!/usr/bin/env python3
# -*- coding: utf-8, vim: expandtab:ts=4 -*-

import sys
from argparse import ArgumentParser, FileType

from .digest import MtHasher, ALGORITHMS_GUARANTEED


def parse_args():
    parser = ArgumentParser(description='Calculate one or more hashes for one or more files, one algo/thread')
    algo_group = parser.add_argument_group('Available hash algorithms')
    for algo in ALGORITHMS_GUARANTEED:
        algo_group.add_argument(f'--{algo}', help=f'{algo} hash algorithm', action='store_true', default=False)
    parser.add_argument('-i', '--input', dest='input_files', nargs='+', default=['-'],
                        help='Input files instead of STDIN (STDIN is denoted with -)', metavar='FILES')
    parser.add_argument('-o', '--output', dest='output_stream',  type=FileType('w'), default=sys.stdout,
                        help='Use output file instead of STDOUT', metavar='FILE')

    opts = vars(parser.parse_args())
    algos = tuple(algo for algo in ALGORITHMS_GUARANTEED if opts[algo])
    if len(algos) == 0:
        parser.print_help(sys.stderr)
        exit(2)

    return algos, tuple(opts['input_files']), opts['output_stream']


def entrypoint(algos, filenames, output_stream):
    hasher = MtHasher(algos)
    for output_line in hasher.hash_multiple_files(filenames):
        print(*output_line, sep='\t', file=output_stream)
    output_stream.close()


def main():
    algos, filenames, output_stream = parse_args()
    entrypoint(algos, filenames, output_stream)


if __name__ == '__main__':
    main()
