import pysolr
import os
import uuid

solr_host = os.environ.get('SOLR_HOST')
solr_collection = os.environ.get('SOLR_COLLECTION')
solr_port = os.environ.get('SOLR_PORT')

solr = pysolr.Solr('http://' + str(solr_host) + ':' + str(solr_port) + '/solr/' + str(solr_collection), timeout=10)

def prepare_fields_session_object(sessionObject):
    # remove fields that are not to be indexed (e.g. mongoDB-ID)

    if '_id' in sessionObject:
        sessionObject.pop("_id", None)

    if 'isValidated' in sessionObject:
        sessionObject.pop("isValidated", None)

    tags = [];

    # hier muss noch die übersetzung der tags rein

    for child in sessionObject["_childDocuments_"]:
        if 'bbox' in child:
            child.pop("bbox", None)

        if 'id' not in child or child["id"] == "":
            child["id"] = uuid.uuid1().hex
            child["path"] = sessionObject["path"] + ".label"

        if "attr_category" in child:

            if "attr_color" in child:
                color = child["attr_color"]

            else:
                color = ""

            tag = child["attr_category"] + " " + color
            tags.append(tag)

        if "sex" in child["attr_type"]:
            tag = child["sex"]
            tags.append(tag)

    sessionObject["tags_en"] = tags

    return sessionObject

def add_session_to_index(sessionObjectInput):

    sessionObject = prepare_fields_session_object(sessionObjectInput)

    # delete old object and reindex entire document

    session_id = sessionObject["id"]

    solr.delete(q='id:' + session_id)

    # add object to index

    solr.add([
        sessionObject
    ])

def remove_index():
    solr.delete(q='*:*')
