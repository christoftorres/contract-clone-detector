#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import csv
import json
import time
import shlex
import argparse
import subprocess

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from CCD.utils import settings

class colors:
    INFO = '\033[94m'
    OK = '\033[92m'
    FAIL = '\033[91m'
    END = '\033[0m'

DEBUG = False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--clean", action="store_true", help="Override existing results.")
    parser.add_argument(
        "--ngram-size", type=int, help="N-gram sized for storing and matching fingerprints (default: '"+str(settings.NGRAM_SIZE)+"')")
    parser.add_argument(
        "--ngram-threshold", type=float, help="N-gram threshold for matching fingerprints (default: '"+str(settings.NGRAM_THRESHOLD)+"')")
    parser.add_argument(
        "--levenshtein-threshold", type=float, help="Levenshtein threshold for matching fingerprints (default: '"+str(settings.LEVENSHTEIN_TRESHOLD)+"')")
    args = parser.parse_args()

    ngram_size = settings.NGRAM_SIZE
    if args.ngram_size:
        ngram_size = args.ngram_size

    ngram_threshold = settings.NGRAM_THRESHOLD
    if args.ngram_threshold:
        ngram_threshold = args.ngram_threshold

    levenshtein_threshold = settings.LEVENSHTEIN_TRESHOLD
    if args.levenshtein_threshold:
        levenshtein_threshold = args.levenshtein_threshold

    print("N-gram size:", colors.INFO+str(ngram_size)+colors.END+",", "N-gram threshold:", colors.INFO+str(ngram_threshold)+colors.END+",", "Levenshtein threshold:", colors.INFO+str(levenshtein_threshold)+colors.END)

    if args.clean:
        if os.path.exists("results/ccd_similarities_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json"):
            os.remove("results/ccd_similarities_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json")
        if os.path.exists("results/ccd_results_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json"):
            os.remove("results/ccd_results_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json")

    if not os.path.exists("results"):
        os.makedirs("results")

    all_contracts = list()
    for path, _, files in os.walk("dataset/honeypots/source_code"):
        for name in files:
            if name.endswith(".sol"):
                all_contracts.append(os.path.join(path, name))

    similarities = dict()
    if os.path.exists("results/ccd_similarities_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json"):
        with open("results/ccd_similarities_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json", "r") as f:
            similarities = json.load(f)

    for contract in all_contracts:
        if contract.replace("..", "") in similarities:
            if DEBUG:
                print("Skipping '"+colors.INFO+contract+colors.END+"'")
            continue
        print("Analyzing '"+colors.INFO+contract+colors.END+"'")
        start = time.time()
        proc = subprocess.Popen(shlex.split("python3 ../CCD/CCD.py -m "+contract+" --elasticsearch-index honeybadger-index --ngram-size "+str(ngram_size)+" --ngram-threshold "+str(ngram_threshold)+" --levenshtein-threshold "+str(levenshtein_threshold)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        result = dict()
        for line in out.decode("utf-8").split("\n"):
            findings = re.compile("[+-]?([0-9]*[.]?[0-9]+) .*? [+-]?([0-9]*[.]?[0-9]+) .*? (0x[a-fA-F0-9]{40}) .*? (.+)\/([^\/]+)").findall(line.replace("\t", ""))
            if len(findings) == 1:
                result[os.path.join(findings[0][3], findings[0][4]).replace("..", "")] = findings[0][1]
        if err:
            print(colors.FAIL+err.decode("utf-8")+colors.END)
        print("Analyzing '"+colors.INFO+contract+colors.END+"' took:", colors.INFO+str(time.time() - start)+colors.END, "second(s).")
        similarities[contract.replace("..", "")] = result

    with open("results/ccd_similarities_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json", "w") as f:
        json.dump(similarities, f, indent=4)

    labels = dict()
    for path, _, files in os.walk("dataset/honeypots/labels"):
        for name in files:
            if name.endswith(".csv"):
                honeypot = name.replace(".csv", "")
                labels[honeypot] = dict()
                with open(os.path.join(path, name), "r") as f:
                    reader = csv.reader(f)
                    next(reader)
                    for row in reader:
                        labels[honeypot][row[0]] = True if row[1] == "TRUE" else False

    results = dict()
    results["tool"] = "CCD"
    results["ngram_size"] = ngram_size
    results["ngram_threshold"] = ngram_threshold
    results["levenshtein_threshold"] = levenshtein_threshold
    for contract in similarities:
        honeypot = contract.replace("/dataset/honeypots/source_code/", "").split("/")[0]
        if not honeypot in results:
            results[honeypot] = dict()
        address = contract.split("/")[-1].replace(".sol", "")
        results[honeypot][address] = dict()
        results[honeypot][address]["true_positives"] = 0
        results[honeypot][address]["false_positives"] = 0
        results[honeypot][address]["true_negatives"] = 0
        results[honeypot][address]["false_negatives"] = 0
        addresses_found = set()
        for contract2 in similarities[contract]:
            address2 = contract2.split("/")[-1].replace(".sol", "")
            addresses_found.add(address2)
            # Detect false positives
            if not address2 in labels[honeypot] or (address2 in labels[honeypot] and labels[honeypot][address2] == False):
                results[honeypot][address]["false_positives"] += 1
            # Detect true positives
            else:
                results[honeypot][address]["true_positives"] += 1
        for address3 in labels[honeypot]:
            if not address3 in addresses_found:
                # Detect false negatives
                if labels[honeypot][address3] == True:
                    results[honeypot][address]["false_negatives"] += 1
                # Detect true negatives
                else:
                    results[honeypot][address]["true_negatives"] += 1

    with open("results/ccd_results_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json", "w") as f:
        json.dump(results, f, indent=4)

    print("Done.")

if __name__ == "__main__":
    main()
