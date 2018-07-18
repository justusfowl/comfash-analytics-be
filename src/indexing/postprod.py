import pysolr
import os
import uuid
import requests
import json

from searchable import prepare_fields_session_object

solr_host_prod = os.environ.get('SOLR_HOST_PROD')
solr_collection = os.environ.get('SOLR_COLLECTION')
solr_port = os.environ.get('SOLR_PORT')

solr = pysolr.Solr('http://' + solr_host_prod + ':' + str(solr_port) + '/solr/' + solr_collection, timeout=10)

def add_session_to_prod_index(sessionObjectInput):

    sessionObject = prepare_fields_session_object(sessionObjectInput)

    # delete old object and reindex entire document

    session_id = sessionObject["id"]

    solr.delete(q='id:' + session_id)

    # add object to index

    solr.add([
        sessionObject
    ])

def prepare_posting(session_object):

    my_item = session_object
    my_item.pop("_id", None)

    comfash_app_host = os.environ.get('COMFASH_APP_HOST_PROD')
    comfash_app_port = os.environ.get('COMFASH_APP_PORT_PROD')

    url = 'https://' + str(comfash_app_host) + ':' + str(comfash_app_port) + '/api/v01/admin/crawl'

    data = {'collectionId': 1}

    headers = {'api_secret': os.environ.get('SERVER_2_SERVER_SECRET_PROD')}

    file_base_path = os.environ.get('FILE_OUTPUT_PATH_FOR_CLASSIFY')

    file_name = my_item["id"] + ".jpg"

    file_object = os.path.join(file_base_path, file_name)

    files = {'file': open(file_object, 'rb')}
    r = requests.post(url, data=data, files=files, headers=headers, verify=False)
    res = json.loads(r.content)

    database_session_id = res["sessionId"]

    my_item["sessionId"] = database_session_id

    return my_item

def post_item_to_prod(session_object):

    post_object = prepare_posting(session_object)

    print("indexing: " + str(post_object["id"]))

    add_session_to_prod_index(post_object)

def init_post_to_prod_index(db):

    result_data = db.mongo_db.inspiration.find({"isValidated" : True})

    for item in result_data:
        try:
            post_item_to_prod(item)
        except:
            print("Something went wrong with {}".format(item["id"]))


    print("reindexing complete")