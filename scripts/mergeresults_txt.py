#!/usr/bin/env python
"""This script merges a number of resultsets saved in pickle format into a
single pickle file.
"""
import argparse

from icarus.registry import RESULTS_READER, RESULTS_WRITER

__all__ = ['merge_results_txt']

read = RESULTS_READER['TXT']
write = RESULTS_WRITER['TXT']


def merge_results_txt(inputs, output):
    """Merge a list of resultsets, saved as pickle into a single pickle file.

    If output file exists, it is overwritten.

    Parameters
    ----------
    input : list
        List of all text file names of the input resultsets
    output : str
        File name of the output text file
    """
    write(sum((read(i) for i in inputs[1:]), read(inputs[0])), output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", dest="output",
                        help='The output results file',
                        required=True)
    parser.add_argument("inputs",
                        help="The simulation configuration file", nargs="+")
    args = parser.parse_args()
    merge_results_txt(args.inputs, args.output)


if __name__ == "__main__":
    main()
