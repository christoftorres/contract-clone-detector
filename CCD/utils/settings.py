import os

# Elasticsearch mapping
ELASTICSEARCH_MAPPING = os.path.dirname(__file__)+"/elasticsearch/mapping.json"
# Elasticsearch timeout
ELASTICSEARCH_TIMEOUT = 60
# Elasticsearch max results
ELASTICSEARCH_MAX_RESULTS = 1000
# Elasticsearch host
ELASTICSEARCH_HOST = "http://localhost"
# Elasticsearch port
ELASTICSEARCH_PORT = 9200
# Elasticsearch clear index
ELASTICSEARCH_CLEAR_INDEX = True
# Ngram size
NGRAM_SIZE = 3
# Ngram threshold
NGRAM_THRESHOLD = 0.5
# Levenshtein threshold
LEVENSHTEIN_TRESHOLD = 0.7
# Debugging mode
DEBUG_MODE = False
# Python recursion limit
PYTHON_RECURSION_LIMIT = 3000
