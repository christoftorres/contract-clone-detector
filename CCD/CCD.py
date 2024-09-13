#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import csv
import time
import html
import numpy
import ssdeep
import argparse
import traceback
import multiprocessing

from tqdm import tqdm
from polyleven import levenshtein

from utils import settings
from utils.parser import parser
from utils.normalizer import clear_parser_identifiers, normalize_child
from utils.utils import colors, remove_comments, remove_assembly, generate_ngrams
from utils.elasticsearch import load_database_mapping, add_document_to_index, get_document_by_id, get_matching_items_for_fingerprint

def store_fingerprint(file_name):
    start = time.time()
    fingerprint = generate_fingerprint(file_name)
    id = file_name.split("/")[-1].replace(".sol", "")
    results = get_document_by_id(id, index=index)
    if results["hits"]["total"]["value"] > 0:
        if debug:
            print("Already generated and stored fingerprint for '"+colors.INFO+file_name.split("/")[-1]+colors.END+"'!")
    else:
        add_document_to_index(fingerprint, index=index, id=id)
        if debug:
            print("Generated and stored fingerprint for "+colors.OK+"'"+file_name.split("/")[-1]+"'"+colors.END)
    return time.time() - start

def generate_fingerprint(file_name):
    start = time.time()
    result = dict()

    if settings.DEBUG_MODE:
        print("Generating fingerprint...")

    source_code = ""
    with open(file_name, "r") as f:
        source_code = f.read()

    errors = ""

    # Parse source code to obtain abstract syntax tree
    if settings.DEBUG_MODE:
        print("Parsing source code to obtain abstract syntax tree (AST)...")
    source_unit = None
    try:
        source_code = html.unescape(source_code)
        source_code = remove_assembly(source_code)
        source_code = remove_comments(source_code)
        source_code = source_code.replace("\n", "")
        print(colors.FAIL, end="")
        source_unit = parser.parse(source_code, loc=False)
        print(colors.END, end="")
    except Exception as e:
        print(colors.FAIL+traceback.format_exc(), file_name+colors.END)
        print(colors.FAIL+"Parsing error:", str(e)+". Filename:", file_name+colors.END)
        errors += "Parsing error: "+str(e)+" "
        pass
    if settings.DEBUG_MODE and len(errors) == 0:
        print("Successfully parsed source code without errors.")

    # Normalize source code
    if settings.DEBUG_MODE:
        print("Normalizing source code...")
    normalized_source_code = ""
    try:
        lock = multiprocessing.Lock()
        with lock:
            clear_parser_identifiers()
            if source_unit != None:
                for child in source_unit.children:
                    normalized_source_code += normalize_child(child)
    except Exception as e:
        print(traceback.format_exc())
        print(colors.FAIL+"Normalization error:", str(e)+". Filename:", file_name+colors.END)
        errors += "Normalization error: "+str(e)+" "
        pass
    if settings.DEBUG_MODE:
        print("Normalized source code:", colors.INFO+normalized_source_code+colors.END)

    # Generate fingerprint
    sequence = ""
    fingerprint = list()
    contract_level_fingerprint = list()
    function_level_fingerprint = list()
    for character in normalized_source_code:
        if character in ["{", ";", "}"]:
            updates = list()
            if "(" in sequence and ")" in sequence:
                pieces = [x for x in sequence.replace(")", "").split("(") if x]
                pieces = [x for piece in pieces for x in piece.replace("&&", " && ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("||", " || ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace(">=", " >= ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("<=", " <= ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("==", " == ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("!=", " != ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace(">", " > ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("<", " < ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace(".", " . ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("+", " + ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("-", " - ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("/", " / ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("*", " * ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace(",", " , ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("!", " ! ").split(" ")]
                pieces = [x for piece in pieces for x in piece.replace("returns", " returns ").split(" ") if x]
                if settings.DEBUG_MODE:
                    print("Tokens:", pieces)
                hash = "".join([ssdeep.hash(x).split(":")[1] for x in pieces])
                if settings.DEBUG_MODE:
                    print(sequence, " ".join([ssdeep.hash(x).split(":")[1] for x in pieces]), " ".join(["'"+x+"'" for x in pieces]))
            else:
                hash = ssdeep.hash(sequence).split(":")[1]
            updates.append((sequence, hash))
            if function_level_fingerprint and sequence.startswith("contract") or sequence.startswith("library") or sequence.startswith("interface") or sequence.startswith("abstract") or sequence.startswith("function") or sequence.startswith("fallback") or sequence.startswith("constructor") or sequence.startswith("modifier"):
                contract_level_fingerprint.append(function_level_fingerprint)
                function_level_fingerprint = list()
                if settings.DEBUG_MODE:
                    print()
            if contract_level_fingerprint and sequence.startswith("contract") or sequence.startswith("library") or sequence.startswith("interface") or sequence.startswith("abstract"):
                fingerprint.append(contract_level_fingerprint)
                contract_level_fingerprint = list()
                if settings.DEBUG_MODE:
                    print()
            for update in updates:
                if update[1]:
                    function_level_fingerprint.append(update[1])
                    if settings.DEBUG_MODE:
                        print(colors.INFO+"'"+update[0]+"'"+colors.END, "-->", colors.INFO+update[1]+colors.END)
            sequence = ""
        else:
            sequence += character
    if function_level_fingerprint:
        contract_level_fingerprint.append(function_level_fingerprint)
    if contract_level_fingerprint:
        fingerprint.append(contract_level_fingerprint)
    contract_level_fingerprints = list()
    for contract in fingerprint:
        contract_level_fingerprint = ".".join(["".join(f) for f in contract if f])
        if contract_level_fingerprint:
            contract_level_fingerprints.append(contract_level_fingerprint)
    fingerprint = ":".join(contract_level_fingerprints)
    end = time.time()

    size_normalized_source_code = len(normalized_source_code)
    size_fingerprint = len(fingerprint)
    compression_ratio = 0.0
    try:
        compression_ratio = 100 - size_fingerprint / size_normalized_source_code * 100
    except:
        pass

    result["file_name"] = file_name.split("/")[-1]
    result["file_path"] = file_name
    result["fingerprint"] = fingerprint
    result["size_normalized_source_code"] = size_normalized_source_code
    result["size_fingerprint"] = size_fingerprint
    result["compression_ratio"] = compression_ratio
    result["execution_time"] = end - start
    result["errors"] = errors

    if settings.DEBUG_MODE:
        print("Fingerprint generation took:", colors.INFO+str(end - start), "second(s)"+colors.END)
        print("Normalized source code size:", colors.INFO+str(size_normalized_source_code)+colors.END)
        print("Fingerprint size:", colors.INFO+str(size_fingerprint)+colors.END)
        print("Compression ratio:", colors.INFO+str(compression_ratio)+"%"+colors.END)

    return result

def compare(fp1, fp2):
    if settings.DEBUG_MODE:
        start = time.time()

    fp1 = [i.split(".") for i in [h for h in fp1.split(":")]]
    fp2 = [i.split(".") for i in [h for h in fp2.split(":")]]

    if settings.DEBUG_MODE:
        print()
    l4 = list()
    for c1 in fp1:
        l3 = list()
        for c2 in fp2:
            l2 = list()
            if settings.DEBUG_MODE:
                print("Score")
                print("-------------------------------------------------------------------")
                print()
            for f1 in c1:
                l1 = list()
                for f2 in c2:
                    lev_dis = levenshtein(f1, f2)
                    max_lev = max(len(f1), len(f2))
                    score = ((max_lev - lev_dis) / max_lev) * 100.0
                    if settings.DEBUG_MODE:
                        print("{:.2f}".format(score), "\t", f1, f2)
                    l1.append(score)
                if settings.DEBUG_MODE:
                    print("L1", l1, "-->", max(l1))
                    print()
                l2.append(max(l1))
            if len(l2) > 0:
                if settings.DEBUG_MODE:
                    print("-------------------------------------------------------------------")
                    print("L2", l2, "-->", sum(l2) / len(l2))
                l2_sum = 0
                l2_size = 0
                for i in range(len(l2)):
                    l2_sum += len(c1[i]) * (l2[i] / 100)
                    l2_size += len(c1[i])
                l3.append((l2_sum / l2_size) * 100.0)
            else:
                if settings.DEBUG_MODE:
                    print("L2", l2, "-->", 0.0)
                l3.append(0.0)
        if settings.DEBUG_MODE:
            print("L3", "-->", l3)
        l4.append(max(l3))
    if settings.DEBUG_MODE:
        end = time.time()
        print("L4", "-->", l4)
        print()
        print("Comparison took:", end-start, "second(s)")
        print()
    if len(l4) > 0:
        return sum(l4) / len(l4)
    return 0.0

def find_solidity_source_code_files(directory):
    file_paths = list()
    vyper_contracts = list()
    if directory.endswith(".sol"):
        file_paths.append(directory)
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".sol") or file == "source_code":
                file_paths.append(os.path.join(root, file))
                if "vyper" in file.lower():
                    vyper_contracts.append(os.path.join(root, file))
    for vyper_file in vyper_contracts:
        if vyper_file in file_paths:
            file_paths.remove(vyper_file)
    return file_paths

def match_fingerprint(file_path, index):
    start_time = time.time()
    print("Matching '"+colors.INFO+file_path+colors.END+"'...")
    # Generate fingerprint
    fp = generate_fingerprint(file_path)
    if fp["errors"]:
        print(colors.FAIL+"Error while generating fingerprint for '"+file_path+"'!"+colors.END)
        return time.time() - start_time
    # Query Elasticsearch for matches based on n-grams
    matching_items, matching_execution_time = get_matching_items_for_fingerprint(index, fp["fingerprint"], settings.NGRAM_THRESHOLD)
    if settings.DEBUG_MODE:
        print("Found", colors.INFO+str(len(matching_items))+colors.END, "record(s) in", colors.INFO+str(matching_execution_time)+colors.END, "second(s) matching an n-gram threshold of at least", colors.INFO+str(int(settings.NGRAM_THRESHOLD*100))+"%"+colors.END+".")
    # Filter matches based on levenshtein distance
    levenshtein_execution_time_start = time.time()
    similar_items = list()
    for match in matching_items:
        similarity_score = compare(fp["fingerprint"], match[2])
        if similarity_score >= int(settings.LEVENSHTEIN_TRESHOLD*100):
            similar_items.append([match[0], similarity_score, match[1]])
    levenshtein_execution_time_end = time.time()
    # Sort results
    similar_items.sort(reverse=True, key=lambda i: i[0])
    # Output results
    if settings.DEBUG_MODE:
        print("Found", colors.INFO+str(len(similar_items))+colors.END, "record(s) in", colors.INFO+str(levenshtein_execution_time_end-levenshtein_execution_time_start)+colors.END, "second(s) matching a levenshtein threshold of at least", colors.INFO+str(int(settings.LEVENSHTEIN_TRESHOLD*100))+"%"+colors.END+".")
    print("N-gram \t Levenshtein \t Contract Address \t\t\t\t File Path")
    print("----------------------------------------------------------------------------------------------------------------")
    for item in similar_items:
        print("{:.2f}".format(item[0]).rjust(6), "\t", "{:.2f}".format(item[1]).rjust(6), "\t", item[2].split("/")[-1].split("_")[0].replace(".sol", ""), "\t", item[2])
    return time.time() - start_time

def init_process(_index, _debug):
    global index
    global debug

    index = _index
    debug = _debug

def main():
    global args

    print("")
    print("   ________________ ")
    print("  / ____/ ____/ __ \\")
    print(" / /   / /   / / / /")
    print("/ /___/ /___/ /_/ / ")
    print("\____/\____/_____/  ")
    print("")

    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "-g", "--generate-fingerprint", type=str, help="Generate fingerprint from Solidity source code or snippet file (e.g., <source_code_file.sol>)")
    group.add_argument(
        "-s", "--store-fingerprints", type=str, help="Generate fingerprints from folder and store into Elasticsearch (e.g., <source_code_folder>)")
    group.add_argument(
        "-m", "--match-fingerprint", type=str, help="Match fingerprint with fingerprints stored in Elasticsearch")
    group.add_argument(
        "-c", "--compare-fingerprint", type=str, help="Takes as input two Solidity source code or snippet files and compares their fingerprint")
    parser.add_argument(
        "--ngram-size", type=int, help="N-gram sized for storing and matching fingerprints (default: '"+str(settings.NGRAM_SIZE)+"')")
    parser.add_argument(
        "--ngram-threshold", type=float, help="N-gram threshold for matching fingerprints (default: '"+str(settings.NGRAM_THRESHOLD)+"')")
    parser.add_argument(
        "--levenshtein-threshold", type=float, help="Levenshtein threshold for matching fingerprints (default: '"+str(settings.LEVENSHTEIN_TRESHOLD)+"')")
    parser.add_argument(
        "--elasticsearch-host", type=str, help="Elasticsearch host (default: '"+settings.ELASTICSEARCH_HOST+"')")
    parser.add_argument(
        "--elasticsearch-port", type=int, help="Elasticsearch port (default: '"+str(settings.ELASTICSEARCH_PORT)+"')")
    parser.add_argument(
        "--elasticsearch-index", type=str, help="Elasticsearch index")
    parser.add_argument(
        "--debug", action="store_true", help="Print debug information to the console")
    parser.add_argument(
        "-v", "--version", action="version", version="Morpheus version "+colors.INFO+"0.0.1"+colors.END)
    args = parser.parse_args()

    if args.ngram_size:
        settings.NGRAM_SIZE = args.ngram_size

    if args.ngram_threshold:
        settings.NGRAM_THRESHOLD = args.ngram_threshold

    if args.levenshtein_threshold:
        settings.LEVENSHTEIN_TRESHOLD = args.levenshtein_threshold

    if args.elasticsearch_host:
        settings.ELASTICSEARCH_HOST = args.elasticsearch_host

    if args.elasticsearch_port:
        settings.ELASTICSEARCH_PORT = args.elasticsearch_port

    if args.debug:
        settings.DEBUG_MODE = args.debug

    sys.setrecursionlimit(settings.PYTHON_RECURSION_LIMIT)

    if args.generate_fingerprint:
        fp = generate_fingerprint(args.generate_fingerprint)
        print("Fingerpint:", colors.INFO+str(fp["fingerprint"])+colors.END)

    if args.store_fingerprints:
        if not args.elasticsearch_index:
            print(colors.FAIL+"Elasticsearch index missing! Please provide an index via --elasticsearch-index"+colors.END)
        else:
            # Search for files to be fingerprinted
            print("Searching for Solidity source code files to be fingerprinted...")
            file_paths = find_solidity_source_code_files(args.store_fingerprints)
            print("Found", colors.INFO+str(len(file_paths))+colors.END, "Solidity source code files.")
            # Generate fingerprints and store them in Elasticsearch
            print("Running fingerprint generation with "+colors.INFO+str(multiprocessing.cpu_count())+colors.END+" CPUs.")
            if args.store_fingerprints.endswith("/"):
                args.store_fingerprints = args.store_fingerprints[0:len(args.store_fingerprints)-1]
            print("Storing fingerprints to index:", colors.INFO+args.elasticsearch_index+colors.END+".")
            print("Using a tokenizer with an n-gram size of", colors.INFO+str(settings.NGRAM_SIZE)+colors.END+".")
            load_database_mapping(index=args.elasticsearch_index, clear_index=settings.ELASTICSEARCH_CLEAR_INDEX)
            execution_times = []
            if sys.platform.startswith("linux"):
                multiprocessing.set_start_method("fork")
            with multiprocessing.Pool(processes=multiprocessing.cpu_count(), initializer=init_process, initargs=(args.elasticsearch_index, settings.DEBUG_MODE, )) as pool:
                start_total = time.time()
                execution_times += pool.map(store_fingerprint, file_paths)
                end_total = time.time()
                print("Total execution time: "+colors.INFO+str(end_total - start_total)+colors.END)
                if settings.DEBUG_MODE and execution_times:
                    print()
                    print("Max execution time: "+colors.INFO+str(numpy.max(execution_times))+colors.END)
                    print("Mean execution time: "+colors.INFO+str(numpy.mean(execution_times))+colors.END)
                    print("Median execution time: "+colors.INFO+str(numpy.median(execution_times))+colors.END)
                    print("Min execution time: "+colors.INFO+str(numpy.min(execution_times))+colors.END)

    if args.match_fingerprint:
        if not args.elasticsearch_index:
            print(colors.FAIL+"Elasticsearch index missing! Please provide an index via --elasticsearch-index"+colors.END)
        elif os.path.exists(args.match_fingerprint):
            print("Matching fingerprints with n-gram threshold of", colors.INFO+str(settings.NGRAM_THRESHOLD)+colors.END, "and Levenshtein threshold of", colors.INFO+str(settings.LEVENSHTEIN_TRESHOLD)+colors.END)
            file_paths = find_solidity_source_code_files(args.match_fingerprint)
            start_total = time.time()
            for file_path in file_paths:
                match_fingerprint(file_path, args.elasticsearch_index)
            end_total = time.time()
            print("Total execution time: "+colors.INFO+str(end_total - start_total)+colors.END)
        else:
            print(colors.FAIL+"Error: File '"+args.match_fingerprint+"' does not exist!"+colors.END)

    if args.compare_fingerprint:
        file1 = args.compare_fingerprint.split(":")[0]
        file2 = args.compare_fingerprint.split(":")[1]
        fp1 = generate_fingerprint(file1)
        print("Fingerprint 1:", colors.INFO+fp1["fingerprint"]+colors.END)
        fp2 = generate_fingerprint(file2)
        print("Fingerprint 2:", colors.INFO+fp2["fingerprint"]+colors.END)
        print()

        if settings.DEBUG_MODE:
            print("N-gram size:", colors.INFO+str(settings.NGRAM_SIZE)+colors.END)
            ngram_match = ""
            ngram_score = 0
            for ngram in generate_ngrams(fp1["fingerprint"], settings.NGRAM_SIZE):
                if ngram in generate_ngrams(fp2["fingerprint"], settings.NGRAM_SIZE):
                    ngram_match += colors.OK + ngram
                    ngram_score += 1
                else:
                    ngram_match += colors.FAIL + ngram
            ngram_match += colors.END
            print(ngram_match)
            print()

            ngram_score = ngram_score / len(generate_ngrams(fp1["fingerprint"], settings.NGRAM_SIZE)) * 100.0
            print(colors.INFO+"N-gram score:"+colors.END, ngram_score)
            print(colors.INFO+"Levenshtein score:"+colors.END, compare(fp1["fingerprint"], fp2["fingerprint"]))
        else:
            print(colors.INFO+"Similarity score:"+colors.END, compare(fp1["fingerprint"], fp2["fingerprint"]))

if __name__ == "__main__":
    main()
