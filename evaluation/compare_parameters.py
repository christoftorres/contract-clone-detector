#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import csv
import shlex
import seaborn
import subprocess
import matplotlib
import matplotlib.pyplot as plt

seaborn.set(font_scale=1.8)
seaborn.set_style("whitegrid", {"axes.grid": False})

class colors:
    INFO = "\033[94m"
    OK = "\033[92m"
    FAIL = "\033[91m"
    END = "\033[0m"

NGRAM_SIZES = [3, 5, 7]
NGRAM_THRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9]
LEVENSHTEIN_TRESHOLDS = [0.5, 0.6, 0.7, 0.8, 0.9]

DEBUG = False

def main():
    max_precision = 0.0
    max_precision_parameters = (0, 0.0, 0.0)
    max_recall = 0.0
    max_recall_parameters = (0, 0.0, 0.0)

    best_f1_score = 0.0
    best_precision = 0.0
    best_recall = 0.0
    best_parameters = (0, 0.0, 0.0)

    for ngram_size in NGRAM_SIZES:
        print("Indexing dataset with n-gram size", colors.INFO+str(ngram_size)+colors.END, "on elasticsearch...")
        proc = subprocess.Popen(shlex.split("python3 ../CCD/CCD.py -s dataset/honeypots/source_code --elasticsearch-index honeybadger-index --ngram-size "+str(ngram_size)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if err:
            print(colors.FAIL+str(err.decode("utf-8"))+colors.END)
            sys.exit(-1)
        if DEBUG and out:
            print(out.decode("utf-8"))
        print()

        with open("precision_recall_ngram_size_"+str(ngram_size)+".csv", "w") as f:
            writer = csv.writer(f)
            writer.writerow(["N-gram Threshold", "Levenshtein Threshold", "Precision", "Recall"])
            precision_points = dict()
            recall_points = dict()
            for ngram_threshold in NGRAM_THRESHOLDS:
                precision_points[ngram_threshold] = list()
                recall_points[ngram_threshold] = list()
                for levenshtein_threshold in LEVENSHTEIN_TRESHOLDS:
                    print("Evaluating n-gram threshold", colors.INFO+str(ngram_threshold)+colors.END, "and Levenshtein threshold", colors.INFO+str(levenshtein_threshold)+colors.END)
                    if not (os.path.exists("results/ccd_results_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json") and os.path.exists("results/ccd_similarities_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json")):
                        proc = subprocess.Popen(shlex.split("python3 evaluate_ccd.py --clean --ngram-size "+str(ngram_size)+" --ngram-threshold "+str(ngram_threshold)+" --levenshtein-threshold "+str(levenshtein_threshold)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                        out, err = proc.communicate()
                        if err:
                            print(colors.FAIL+str(err.decode("utf-8"))+colors.END)
                            sys.exit(-2)
                        else:
                            if DEBUG and out:
                                print(out.decode("utf-8"))
                    proc = subprocess.Popen(shlex.split("python3 compare_results.py results/ccd_results_"+str(ngram_size)+"_"+str(ngram_threshold)+"_"+str(levenshtein_threshold)+".json"), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    out, err = proc.communicate()
                    if err:
                        print(colors.FAIL+str(err.decode("utf-8"))+colors.END)
                        sys.exit(-2)
                    if DEBUG and out:
                        print(out.decode("utf-8"))
                    smartembed_precision = None
                    smartembed_recall = None
                    precision = None
                    recall = None
                    f1_score = None
                    for line in out.decode("utf-8").split("\n"):
                        if line.startswith("Precision"):
                            smartembed_precision = float(line.split(" ")[-3])
                            precision = float(line.split(" ")[-1])
                        if line.startswith("Recall"):
                            smartembed_recall = float(line.split(" ")[-3])
                            recall = float(line.split(" ")[-1])
                        if line.startswith("F1-Score"):
                            f1_score = float(line.split(" ")[-1])
                    if precision and recall:
                        precision_points[ngram_threshold].append(precision)
                        recall_points[ngram_threshold].append(recall)
                        writer.writerow([ngram_threshold, levenshtein_threshold, precision, recall])
                        if precision > smartembed_precision and recall > smartembed_recall:
                            if DEBUG:
                                print((ngram_size, ngram_threshold, levenshtein_threshold), precision, recall, f1_score)
                            if f1_score > best_f1_score:
                                best_f1_score = f1_score
                                best_precision = precision
                                best_recall = recall
                                best_parameters = (ngram_size, ngram_threshold, levenshtein_threshold)
                        if precision > max_precision:
                            max_precision = precision
                            max_precision_parameters = (ngram_size, ngram_threshold, levenshtein_threshold)
                        if recall > max_recall:
                            max_recall = recall
                            max_recall_parameters = (ngram_size, ngram_threshold, levenshtein_threshold)
                print()
        palette = plt.rcParams["axes.prop_cycle"].by_key()["color"]
        fig, ax = plt.subplots()
        plt.xlabel("\u03B5")
        plt.xticks(LEVENSHTEIN_TRESHOLDS, [str(x) for x in LEVENSHTEIN_TRESHOLDS])
        ax.set_ylabel("Precision")
        ax.set_ylim(0.65, 1.0)
        ax.axhline(y=smartembed_precision, color="black")
        ax2 = ax.twinx()
        ax2.set_ylabel("Recall")
        ax2.set_ylim(0.1, 0.7)
        ax2.axhline(y=smartembed_recall, color="black")
        i = 0
        for ngram_threshold in precision_points:
            ax.plot(LEVENSHTEIN_TRESHOLDS, precision_points[ngram_threshold], marker="o", color=palette[i], label="\u03B7 = "+str(ngram_threshold))
            ax2.plot(LEVENSHTEIN_TRESHOLDS, recall_points[ngram_threshold], linestyle="dotted", marker="o", color=palette[i])
            i += 1
        fig.legend(frameon=False, bbox_to_anchor=(0.4, 0.28, 0.5, 0.5))
        plt.savefig("precision_recall_ngram_size_"+str(ngram_size)+".png", dpi=1000, format="png", bbox_inches="tight")

    print("Max precision:", max_precision)
    print("Max precision parameters:", max_precision_parameters)
    print()
    print("Max recall:", max_recall)
    print("Max recall parameters:", max_recall_parameters)
    print()
    print("Best F1-score:", best_f1_score)
    print("Best precision:", best_precision)
    print("Best recall:", best_recall)
    print("Best parameters:", best_parameters)
    print()

if __name__ == "__main__":
    main()
