#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import re

from difflib import SequenceMatcher

class colors:
    INFO = '\033[94m'
    OK = '\033[92m'
    FAIL = '\033[91m'
    END = '\033[0m'

def generate_ngrams(text, n):
    ngrams = list()
    for i in range(len(text) - n + 1):
        ngrams.append(text[i:i+n])
    return ngrams

def remove_comments(string):
    pattern = r"(\".*?\"|\'.*?\')|(/\*.*?\*/|//[^\r\n]*$)"
    # first group captures quoted strings (double or single)
    # second group captures comments (//single-line or /* multi-line */)
    regex = re.compile(pattern, re.MULTILINE|re.DOTALL)

    def _replacer(match):
        # if the 2nd group (capturing comments) is not None,
        # it means we have captured a non-quoted (real) comment string.
        if match.group(2) is not None:
            return ""  # so we will return empty to remove the comment
        else:  # otherwise, we will return the 1st group
            return match.group(1) # captured quoted-string
    return regex.sub(_replacer, string)

def remove_assembly(string):
    string = re.sub(r' case [0-9]+ {[^}]*}', '', string)
    string = re.sub(r' default {[^}]*}', '', string)
    string = re.sub(r' assembly {[^}]*}', '', string)
    return string
