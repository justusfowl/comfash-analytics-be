import pysolr
import os
import uuid

solr_host = os.environ.get('SOLR_HOST')
solr_collection = os.environ.get('SOLR_COLLECTION')
solr_port = os.environ.get('SOLR_PORT')

solr = pysolr.Solr('http://' + solr_host + ':' + str(solr_port) + '/solr/' + solr_collection, timeout=10)

def add_session_to_index(sessionObject):

    # remove fields that are not to be indexed (e.g. mongoDB-ID)

    if '_id' in sessionObject:
        sessionObject.pop("_id", None)

    if 'isValidated' in sessionObject:
        sessionObject.pop("isValidated", None)

    for child in sessionObject["_childDocuments_"]:
        if 'bbox' in child:
            child.pop("bbox", None)
        if 'id' not in child or child["id"] == "":
            child["id"] = uuid.uuid1().hex
            child["path"] = sessionObject["path"] + ".label"

    # delete old object and reindex entire document

    session_id = sessionObject["id"]

    solr.delete(q='id:' + session_id)

    # add object to index

    solr.add([
        sessionObject
    ])

def remove_index():
    solr.delete(q='*:*')
