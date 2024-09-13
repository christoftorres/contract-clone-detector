#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json

class colors:
    INFO = '\033[94m'
    OK = '\033[92m'
    FAIL = '\033[91m'
    END = '\033[0m'

def main():
    results_path = "results/ccd_results.json"
    if len(sys.argv) == 2:
        results_path = sys.argv[1]

    ccd_results = dict()
    if os.path.exists(results_path):
        with open(results_path, "r") as f:
             ccd_results = json.load(f)

    smartembed_results = dict()
    if os.path.exists("results/smartembed_results.json"):
        with open("results/smartembed_results.json", "r") as f:
             smartembed_results = json.load(f)

    results = dict()
    for honeypot in smartembed_results:
        if honeypot in ["tool", "similarity_score", "ngram_size", "ngram_threshold", "levenshtein_threshold"]:
            continue
        if honeypot not in results:
            results[honeypot] = dict()
            results[honeypot]["ccd"] = dict()
            results[honeypot]["ccd"]["true_positives"] = 0
            results[honeypot]["ccd"]["false_positives"] = 0
            results[honeypot]["ccd"]["false_negatives"] = 0
            results[honeypot]["smartembed"] = dict()
            results[honeypot]["smartembed"]["true_positives"] = 0
            results[honeypot]["smartembed"]["false_positives"] = 0
            results[honeypot]["smartembed"]["false_negatives"] = 0
        if honeypot in ccd_results:
            for contract in ccd_results[honeypot]:
                results[honeypot]["ccd"]["true_positives"] += ccd_results[honeypot][contract]["true_positives"]
                results[honeypot]["ccd"]["false_positives"] += ccd_results[honeypot][contract]["false_positives"]
                results[honeypot]["ccd"]["false_negatives"] += ccd_results[honeypot][contract]["false_negatives"]
        if honeypot in smartembed_results:
            for contract in smartembed_results[honeypot]:
                results[honeypot]["smartembed"]["true_positives"] += smartembed_results[honeypot][contract]["true_positives"]
                results[honeypot]["smartembed"]["false_positives"] += smartembed_results[honeypot][contract]["false_positives"]
                results[honeypot]["smartembed"]["false_negatives"] += smartembed_results[honeypot][contract]["false_negatives"]

    print("".ljust(28), "SmartEmbed".ljust(10), "ccd".ljust(20))
    print()
    print("Honeypot Type".ljust(28), "TP".rjust(4)+"FP".rjust(4), "TP".rjust(5)+"FP".rjust(4))
    print("-----------------------------------------------")
    smartembed_total_tp, ccd_total_tp = 0, 0
    smartembed_total_fp, ccd_total_fp = 0, 0
    smartembed_total_fn, ccd_total_fn = 0, 0
    for honeypot in results:
        smartembed_total_tp += results[honeypot]["smartembed"]["true_positives"]
        ccd_total_tp += results[honeypot]["ccd"]["true_positives"]

        smartembed_total_fp += results[honeypot]["smartembed"]["false_positives"]
        ccd_total_fp += results[honeypot]["ccd"]["false_positives"]

        smartembed_total_fn += results[honeypot]["smartembed"]["false_negatives"]
        ccd_total_fn += results[honeypot]["ccd"]["false_negatives"]
        print(honeypot.replace("_", " ").title().ljust(28), str(results[honeypot]["smartembed"]["true_positives"]).rjust(4)+" "+str(results[honeypot]["smartembed"]["false_positives"]).rjust(3), str(results[honeypot]["ccd"]["true_positives"]).rjust(5)+" "+str(results[honeypot]["ccd"]["false_positives"]).rjust(3))
    print("-----------------------------------------------")
    print("Total".ljust(28), str(smartembed_total_tp).rjust(4)+" "+str(smartembed_total_fp).rjust(3), str(ccd_total_tp).rjust(5)+" "+str(ccd_total_fp).rjust(3))
    print()

    if smartembed_total_tp > 0 or smartembed_total_fp > 0:
        smartembed_precision = smartembed_total_tp/(smartembed_total_tp+smartembed_total_fp)
    else:
        smartembed_precision = 0.0
    if ccd_total_tp > 0 or ccd_total_fp > 0:
        ccd_precision = ccd_total_tp/(ccd_total_tp+ccd_total_fp)
    else:
        ccd_precision = 0.0
    print("Precision".ljust(28), '{0:.6f}'.format(smartembed_precision).ljust(9), '{0:.6f}'.format(ccd_precision))

    if smartembed_total_tp > 0 or smartembed_total_fn > 0:
        smartembed_recall = smartembed_total_tp/(smartembed_total_tp+smartembed_total_fn)
    else:
        smartembed_recall = 0.0
    if ccd_total_tp > 0 or ccd_total_fn > 0:
        ccd_recall = ccd_total_tp/(ccd_total_tp+ccd_total_fn)
    else:
        ccd_recall = 0.0
    print("Recall".ljust(28), '{0:.6f}'.format(smartembed_recall).ljust(9), '{0:.6f}'.format(ccd_recall))

    if smartembed_precision > 0 or smartembed_recall > 0:
        smartembed_f2   = (1+  2**2)*((smartembed_precision*smartembed_recall)/((  2**2)*smartembed_precision+smartembed_recall))
        smartembed_f1   = (1+  1**2)*((smartembed_precision*smartembed_recall)/((  1**2)*smartembed_precision+smartembed_recall))
        smartembed_f0_5 = (1+0.5**2)*((smartembed_precision*smartembed_recall)/((0.5**2)*smartembed_precision+smartembed_recall))
    else:
        smartembed_f2 = 0.0
        smartembed_f1 = 0.0
        smartembed_f0_5 = 0.0
    if ccd_precision > 0 or ccd_recall > 0:
        ccd_f2   = (1+  2**2)*((ccd_precision*ccd_recall)/((  2**2)*ccd_precision+ccd_recall))
        ccd_f1   = (1+  1**2)*((ccd_precision*ccd_recall)/((  1**2)*ccd_precision+ccd_recall))
        ccd_f0_5 = (1+0.5**2)*((ccd_precision*ccd_recall)/((0.5**2)*ccd_precision+ccd_recall))
    else:
        ccd_f2 = 0.0
        ccd_f1 = 0.0
        ccd_f0_5 = 0.0
    print()
    print("F2-Score".ljust(28), '{0:.6f}'.format(smartembed_f2).ljust(9), '{0:.6f}'.format(ccd_f2))
    print("F1-Score".ljust(28), '{0:.6f}'.format(smartembed_f1).ljust(9), '{0:.6f}'.format(ccd_f1))
    print("F0.5-Score".ljust(28), '{0:.6f}'.format(smartembed_f0_5).ljust(9), '{0:.6f}'.format(ccd_f0_5))

if __name__ == "__main__":
    main()
