#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import json
import elasticsearch

from utils import settings
from utils.utils import colors, generate_ngrams

def load_database_mapping(index, mapping_file=settings.ELASTICSEARCH_MAPPING, clear_index=False):
    es = elasticsearch.Elasticsearch([settings.ELASTICSEARCH_HOST+":"+str(settings.ELASTICSEARCH_PORT)], timeout=settings.ELASTICSEARCH_TIMEOUT)
    if es.indices.exists(index=index) and clear_index:
        es.indices.delete(index=index)
    if not es.indices.exists(index=index):
        with open(mapping_file, "r") as json_file:
            mapping = json.load(json_file)
            mapping["settings"]["analysis"]["tokenizer"]["fingerprint_tokenizer"]["min_gram"] = settings.NGRAM_SIZE
            mapping["settings"]["analysis"]["tokenizer"]["fingerprint_tokenizer"]["max_gram"] = settings.NGRAM_SIZE
            es.indices.create(index=index, body=mapping)

def add_document_to_index(document, index, id=None):
    es = elasticsearch.Elasticsearch([settings.ELASTICSEARCH_HOST+":"+str(settings.ELASTICSEARCH_PORT)], timeout=settings.ELASTICSEARCH_TIMEOUT)
    try:
        if id:
            es.index(index=index, document=document, op_type="create", id=id)
        else:
            es.index(index=index, document=document, op_type="create")
    except elasticsearch.exceptions.ConflictError:
        print(colors.INFO+"[Elasticsearch] Error: document already exists! ", id, colors.END)
    es.indices.refresh(index)

def get_document_by_id(id, index):
    es = elasticsearch.Elasticsearch([settings.ELASTICSEARCH_HOST+":"+str(settings.ELASTICSEARCH_PORT)], timeout=settings.ELASTICSEARCH_TIMEOUT)
    query = {
        "query": {
            "match":{
               "_id":{
                  "query": id
                }
            }
        }
    }
    return es.search(body=query, index=index)

"""def get_document_by_errors(index):
    es = elasticsearch.Elasticsearch([settings.ELASTICSEARCH_HOST+":"+str(settings.ELASTICSEARCH_PORT)], timeout=settings.ELASTICSEARCH_TIMEOUT)
    query = {
        "query": {
            "regexp":{
                "errors": ".+"
            }
        }
    }
    results = es.search(body=query, index=index, size=settings.ELASTICSEARCH_MAX_RESULTS)
    c = 0
    erros = dict()
    for record in results["hits"]["hits"]:
        c += 1
        erros[record["_source"]["errors"]] = record["_source"]["file_path"]
        print(record["_source"]["errors"], record["_source"]["file_path"])
    print(c)
    print(len(erros))
    import pprint
    pprint.pprint(erros)
    return None"""

def get_matching_items_for_fingerprint(index, fingerprint, threshold):
    fingerprint_ngrams = generate_ngrams(fingerprint, settings.NGRAM_SIZE)
    es = elasticsearch.Elasticsearch([settings.ELASTICSEARCH_HOST+":"+str(settings.ELASTICSEARCH_PORT)], timeout=600, max_retries=1, retry_on_timeout=True)
    query = {
        "query": {
            "match":{
               "fingerprint":{
                  "query": fingerprint,
                  "minimum_should_match": str(int(threshold*100))+"%"
                }
            }
        }
    }
    timer_start = time.time()
    results = es.search(body=query, index=index, size=settings.ELASTICSEARCH_MAX_RESULTS)
    timer_end = time.time()
    matched_fingerprints = list()
    for record in results["hits"]["hits"]:
        record_ngrams = generate_ngrams(record["_source"]["fingerprint"], settings.NGRAM_SIZE)
        ngram_match = 0
        for ngram in fingerprint_ngrams:
            if ngram in record_ngrams:
                ngram_match += 1
        score = ngram_match / len(fingerprint_ngrams) * 100.0
        matched_fingerprints.append((score, record["_source"]["file_path"], record["_source"]["fingerprint"]))
    return matched_fingerprints, timer_end - timer_start
