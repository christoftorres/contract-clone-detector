#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import csv
import requests

class colors:
    INFO = "\033[94m"
    OK = "\033[92m"
    FAIL = "\033[91m"
    END = "\033[0m"

ETHERSCAN_API_KEY = "M8VPZT5CQ71TUQP9JNTTWMUMNS1J8KKC5B"

def main():
    if not os.path.exists("source_code"):
        os.makedirs("source_code")
    for path, _, files in os.walk("labels"):
        for name in files:
            if name.endswith(".csv"):
                if not os.path.exists(os.path.join("source_code", name.replace(".csv", ""))):
                    os.makedirs(os.path.join("source_code", name.replace(".csv", "")))
                with open(os.path.join(path, name)) as csvfile:
                    reader = csv.reader(csvfile, delimiter=',')
                    next(reader)
                    for row in reader:
                        address = row[0]
                        if not os.path.exists(os.path.join("source_code", name.replace(".csv", ""), address+".sol")):
                            print("Downloading", os.path.join("source_code", name.replace(".csv", ""), address+".sol"))
                            response = requests.get("https://api.etherscan.io/api?module=contract&action=getsourcecode&address="+address+"&apikey="+ETHERSCAN_API_KEY)
                            if response.status_code == 200 and response.json()["status"] == "1" and response.json()["message"] == "OK" and len(response.json()["result"]) == 1 and len(response.json()["result"][0]["SourceCode"]) > 0:
                                print(response.json()["result"][0]["ContractName"])
                                with open(os.path.join("source_code", name.replace(".csv", ""), address+".sol"), "w") as f:
                                    f.write(response.json()["result"][0]["SourceCode"])
                            else:
                                print(colors.FAIL+"Error: "+str(response.status_code)+" "+str(response.content)+colors.END)

if __name__ == "__main__":
    main()
