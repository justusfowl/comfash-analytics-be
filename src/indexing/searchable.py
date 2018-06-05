import pysolr
import os

solr_host = os.environ.get('SOLR_HOST')
solr_collection = os.environ.get('SOLR_COLLECTION')
solr_port = os.environ.get('SOLR_PORT')

solr = pysolr.Solr('http://' + solr_host + ':' + str(solr_port) + '/solr/' + solr_collection, timeout=10)

def add_session_to_index(sessionObject):

    # delete old object and reindex entire document

    session_id = sessionObject["id"]

    solr.delete(q='id:' + session_id)

    # add object to index

    solr.add([
        sessionObject
    ])

def remove_index():
    solr.delete(q='*:*')