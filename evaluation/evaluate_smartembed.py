#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import csv
import json
import time
import docker
import multiprocessing

class colors:
    INFO = '\033[94m'
    OK = '\033[92m'
    FAIL = '\033[91m'
    END = '\033[0m'

DEBUG = False

CPUs = 5

SIMILARITY_SCORE = 0.9

def worker(contract, contracts, queue):
    print("Analyzing '"+colors.INFO+contract+colors.END+"'")
    client = docker.from_env()
    volumes = {os.path.join(os.path.dirname(os.path.abspath(__file__)).replace("/evaluation", ""), "dataset"): {"bind": "/dataset", "mode": "ro"}}
    result = dict()
    start = time.time()
    logs = client.containers.run("christoftorres/smartembed", "/bin/bash -c \"echo '"+"\n".join([c for c in contracts])+"' > contracts.txt; python main.py "+contract+" contracts.txt\"", detach=False, remove=True, volumes=volumes)
    for line in logs.decode("utf-8").split("\n"):
        if DEBUG:
            print(line)
        if line.startswith("('Similarity"):
            similarity = re.compile("\('Similarity (.+?):', (.+?)\)").findall(line)[0]
            result[similarity[0]] = similarity[1]
    print("Analyzing '"+colors.INFO+contract+colors.END+"' took:", colors.INFO+str(time.time() - start)+colors.END, "second(s.)")
    assert(len(contracts) == len(result))
    queue.put((contract, result))
    return (contract, result)

def listener(queue):
    previous_progress = 0
    while 1:
        contract, result = queue.get()
        if result == "kill":
            break
        similarities = dict()
        if os.path.exists("results/smartembed_similarities.json"):
            with open("results/smartembed_similarities.json", "r") as f:
                similarities = json.load(f)
        similarities[contract] = result
        latest_progress = int(len(similarities)/len(result)*100.0)
        if latest_progress > previous_progress:
            previous_progress = latest_progress
            print("Overall progress:", colors.INFO+str(latest_progress)+"%"+colors.END)
        with open("results/smartembed_similarities.json", "w") as f:
            json.dump(similarities, f, indent=4)

def main():
    if not os.path.exists("results"):
        os.makedirs("results")

    all_contracts = list()
    for path, _, files in os.walk("dataset/honeypots/source_code"):
        for name in files:
            if name.endswith(".sol"):
                all_contracts.append(os.path.join(path, name).replace("..", ""))

    similarities = dict()
    if os.path.exists("results/smartembed_similarities.json"):
        with open("results/smartembed_similarities.json", "r") as f:
            similarities = json.load(f)

    manager = multiprocessing.Manager()
    queue = manager.Queue()
    pool = multiprocessing.Pool(CPUs)

    watcher = pool.apply_async(listener, (queue,))

    jobs = []
    for contract in all_contracts:
        if contract in similarities:
            if DEBUG:
                print("Skipping '"+colors.INFO+contract+colors.END+"'")
            continue
        job = pool.apply_async(worker, (contract, all_contracts, queue))
        jobs.append(job)
    for job in jobs:
        job.get()

    queue.put("kill")
    pool.close()
    pool.join()

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
    results["tool"] = "smartembed"
    results["similarity_score"] = SIMILARITY_SCORE
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
            if float(similarities[contract][contract2]) >= SIMILARITY_SCORE:
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

    with open("results/smartembed_results.json", "w") as f:
        json.dump(results, f, indent=4)

    print("Done.")

if __name__ == "__main__":
    main()
