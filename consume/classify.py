#!/usr/bin/env python
import pika
import json
import os
from urllib3.exceptions import HTTPError as BaseHTTPError

from analysis.comfashVAPI import  ComfashVAPI
from result.resultdata import insert_session_object_to_mongo as resultHdl

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='classify')

global db
global comfash_vapi

def callback(ch, method, properties, body):

    global db
    global comfash_vapi

    requestParams = json.loads(body.decode('utf-8'))

    print("in function consuming...")

    session_thumbnail_path = str(requestParams["sessionThumbnailPath"])
    session_owner = str(requestParams["sessionOwner"])

    file_name = str(requestParams["fileName"])

    source_page = str(requestParams["sourcePage"])

    orig_Path = str(requestParams["origPath"])
    orig_entity = str(requestParams["origEntity"])

    session_id = str(requestParams["sessionId"])

    print(session_thumbnail_path)

    target_models = requestParams["targetModels"]

    flag_copy_thumbs = requestParams["flagCopyThumbs"]

    existing_document = db.mongo_db.inspiration.find({"id" : session_id })

    if existing_document.count() == 0:

        new_blank_child_documents = []

    else:
        for item in existing_document:
            doc = item
            doc.pop("_id", None)

        child_documents = doc["_childDocuments_"]

        if 'all' in target_models:
            new_blank_child_documents = []
        else:
            new_blank_child_documents = []

            for ch_doc in child_documents:
                if ch_doc["attr_type"] not in target_models:
                    new_blank_child_documents.append(ch_doc)

    try:

        # retrieving labels and classifying for the image = session_thumbnail_path
        #
        # FOR NOW: disable classification and create plain items into MongoDB

        #cf_labels = comfash_vapi.detect_and_classify_items(session_thumbnail_path, session_id, target_models)
        cf_labels = []

        print_string = ""

        # creating uniform labels for indexing

        for l in cf_labels:

            # for now: add all labels

            new_blank_child_documents.append(dict(l))

            #if ch_doc["attr_type"] in target_models or target_models == 'all':
            #    new_blank_child_documents.append(l)


        # deprecated (moved towards copying over webenvironment if flag = true

        if flag_copy_thumbs:

            #classify_path = os.environ.get('FILE_OUTPUT_PATH_FOR_CLASSIFY')

            #application_path = os.environ.get('FILE_OUTPUT_FOR_COMFASH_APPLICATION')

            #src = classify_path + file_name
            #dst = application_path + file_name
            #shutil.copy(src, dst)

            print("copying via flag is no longer available, copying takes place over webservice")

        session_object = {
            "id" : session_id,
            "path": session_id + ".session",
            "owner": session_owner,
            "isValidated" : False,
            "origPath": orig_Path,
            "origEntity": orig_entity,
            "sessionThumbnailPath": "/p/" + file_name,
            "content_type": "parentDocument",
            "sourcePage" : source_page,
            "_childDocuments_" : new_blank_child_documents
        }

        # store data in result pool ready for validation

        classify_path = os.environ.get('FILE_OUTPUT_PATH_FOR_CLASSIFY')
        src_object = classify_path + file_name

        resultHdl(db, session_object, src_object)


        print("done with file and progressed into verify-queue: " + session_thumbnail_path)
        print("following labels found: " + print_string)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except BaseHTTPError as err:
        print("WARNING - SOMETHING WENT WRONG with a HTTP request in classifying")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except:
        print("WARNING - OTHER THAN HTTP FAILURE - SOMETHING WENT WRONG, ACK=FALSE")
        pass



def init_consuming(data_base):

    global db
    db = data_base

    global comfash_vapi
    comfash_vapi = ComfashVAPI()

    print("start consuming...")

    # receive message and complete simulation
    channel.basic_consume(callback, queue='classify')
    channel.start_consuming()
