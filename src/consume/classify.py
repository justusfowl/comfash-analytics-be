#!/usr/bin/env python
import pika
import json
import uuid
import os
import shutil
from urllib3.exceptions import HTTPError as BaseHTTPError

import analysis.googleVAPI as google
import analysis.comfashVAPI as CF
import indexing.searchable as SOLR

from resultdata import insert_session_object_to_mongo as resultHdl

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='classify')

global db

def callback(ch, method, properties, body):

    global db


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

        new_blank_child_documents = []

        for ch_doc in child_documents:
            if ch_doc["attr_type"] not in target_models:
                new_blank_child_documents.append(ch_doc)

    try:

        # retrieving labels and classifying

        if ("clothing" in target_models) or ("all" in target_models):
            cf_labels_clothing = CF.classify_image("clothing", session_thumbnail_path)
        else:
            cf_labels_clothing = []

        if ("gender" in target_models) or ("all" in target_models):
            cf_labels_gender = CF.classify_image("gender", session_thumbnail_path)
        else:
            cf_labels_gender = []


        if ("footwear" in target_models) or ("all" in target_models):
            cf_labels_footwear = CF.classify_image("footwear", session_thumbnail_path)
        else:
            cf_labels_footwear = []

        if ("g-label" in target_models) or ("all" in target_models):
            g_labels = google.classify_labels(session_thumbnail_path)
        else:
            g_labels = []

        print_string = ""

        # creating uniform labels for indexing

        for l in g_labels:

            uuid_item = uuid.uuid1()
            label_id = uuid_item.hex

            new_label = {
                "path": session_id + ".session.label",
                "id": label_id,
                "attr_type": "g-label",
                "attr_origin": "GVAPI",
                "labels": l["cat"],
                "prob": l["prob"]
            }

            print_string = print_string + "," + l["cat"]

            new_blank_child_documents.append(new_label)


        for l in cf_labels_clothing:

            uuid_item = uuid.uuid1()
            label_id = uuid_item.hex

            new_label = {
                "path": session_id + ".session.label",
                "id": label_id,
                "attr_type": "clothing",
                "attr_color" : "#000000",
                "attr_origin": "CFVAPI",
                "labels": l["cat"],
                "prob": l["prob"],
            }

            print_string = print_string + "," + l["cat"]

            new_blank_child_documents.append(new_label)

        for l in cf_labels_gender:

            # setting cut for gender at 30% certainty

            if l["prob"] > 0.3:

                uuid_item = uuid.uuid1()
                label_id = uuid_item.hex

                new_label = {
                    "path": session_id + ".session.label",
                    "id": label_id,
                    "attr_type": "gender",
                    "attr_origin": "CFVAPI",
                    "attr_color" : "#000000",
                    "labels": l["cat"],
                    "prob": l["prob"],
                }

                print_string = print_string + "," + l["cat"]

                new_blank_child_documents.append(new_label)

        for l in cf_labels_footwear:

            # setting cut for gender at 10% certainty

            if l["prob"] > 0.1:

                uuid_item = uuid.uuid1()
                label_id = uuid_item.hex

                new_label = {
                    "path": session_id + ".session.label",
                    "id": label_id,
                    "attr_type": "footwear",
                    "attr_origin": "CFVAPI",
                    "attr_color" : "#000000",
                    "labels": l["cat"],
                    "prob": l["prob"],
                }

                print_string = print_string + "," + l["cat"]

                new_blank_child_documents.append(new_label)



        # copy file into application environment if flag = true

        if flag_copy_thumbs:

            classify_path = os.environ.get('FILE_OUTPUT_PATH_FOR_CLASSIFY')

            application_path = os.environ.get('FILE_OUTPUT_FOR_COMFASH_APPLICATION')

            src = classify_path + file_name
            dst = application_path + file_name
            shutil.copy(src, dst)

            print("moving file complete")

        session_object = {
            "id" : session_id,
            "path": session_id + ".session",
            "owner": session_owner,
            "origPath": orig_Path,
            "origEntity": orig_entity,
            "sessionThumbnailPath": "/p/" + file_name,
            "content_type": "parentDocument",
            "sourcePage" : source_page,
            "_childDocuments_" : new_blank_child_documents
        }

        # store data in result pool

        resultHdl(db, session_object)

        session_object.pop("_id", None)

        # posting to index

        SOLR.add_session_to_index(session_object)

        print("done with file: " + session_thumbnail_path)
        print("following labels found: " + print_string)

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except BaseHTTPError as err:
        print("WARNING - SOMETHING WENT WRONG")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except:
        print("WARNING - OTHER THAN HTTP FAILURE - SOMETHING WENT WRONG, ACK=FALSE")

     #   pass



def init_consuming(data_base):

    global db
    db = data_base

    print("start consuming...")

    # receive message and complete simulation
    channel.basic_consume(callback, queue='classify')
    channel.start_consuming()
