#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

from smartembed import SmartEmbed

class colors:
    INFO = '\033[94m'
    OK = '\033[92m'
    FAIL = '\033[91m'
    END = '\033[0m'

def main():
    if len(sys.argv) != 3:
        print(colors.FAIL+"Error: Please provide two files to be compared: 'python "+sys.argv[0]+" <solidity_file> <list_of_solidity_files>'"+colors.END)
        sys.exit(-1)

    se = SmartEmbed()
    # read contract1 from file
    contract1 = open(sys.argv[1], "r").read()
    # get vector representation for contract1
    vector1 = se.get_vector(contract1)
    with open(sys.argv[2], "r") as f:
        solidity_files = f.read().splitlines()
        for solidity_file in solidity_files:
            # read contract2 from file
            contract2 = open(solidity_file, "r").read()
            # get vector representation for contract2
            vector2 = se.get_vector(contract2)
            # estimate similarity between contract1 and contract2
            similarity = se.get_similarity(vector1, vector2)
            print("Similarity "+solidity_file+":", similarity)

if __name__ == "__main__":
    main()
