import pysolr
import os
import uuid

from util import get_label_translation

solr_host = os.environ.get('SOLR_HOST')
solr_collection = os.environ.get('SOLR_COLLECTION')
solr_port = os.environ.get('SOLR_PORT')

solr = pysolr.Solr('http://' + str(solr_host) + ':' + str(solr_port) + '/solr/' + str(solr_collection), timeout=10)

relevant_fields_for_tags = ["attr_type", "attr_category", "sex" , "attr_color", "attr_fabric", "attr_texture"]

def prepare_fields_session_object(label_dict, sessionObject):
    # remove fields that are not to be indexed (e.g. mongoDB-ID)

    if '_id' in sessionObject:
        sessionObject.pop("_id", None)

    if 'isValidated' in sessionObject:
        sessionObject.pop("isValidated", None)

    if 'isSetTrainOnly' in sessionObject:
        sessionObject.pop("isSetTrainOnly", None)

    tags_en = []
    tags_de = []

    # hier muss noch die übersetzung der tags rein

    for child in sessionObject["_childDocuments_"]:
        if 'bbox' in child:
            child.pop("bbox", None)

        if 'id' not in child or child["id"] == "":
            child["id"] = uuid.uuid1().hex
            child["path"] = sessionObject["path"] + ".label"

        tag_en = ""
        tag_de = ""

        for field in relevant_fields_for_tags:

            if field in child:

                label_desc_en = get_label_translation(label_dict, child[field], "en")
                label_desc_de = get_label_translation(label_dict, child[field], "de")

                tag_en = tag_en + label_desc_en + " "
                tag_de = tag_de + label_desc_de + " "

        tags_en.append(tag_en)
        tags_de.append(tag_de)


    sessionObject["tags_en"] = tags_en
    sessionObject["tags_de"] = tags_de

    return sessionObject

def add_session_to_index(label_dict, sessionObjectInput):

    sessionObject = prepare_fields_session_object(label_dict, sessionObjectInput)

    # delete old object and reindex entire document

    session_id = sessionObject["id"]

    solr.delete(q='id:' + session_id)

    # add object to index

    solr.add([
        sessionObject
    ])

def remove_index():
    solr.delete(q='*:*')
