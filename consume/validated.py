#!/usr/bin/env python
import pika
import json

from util import get_label_dict

import indexing.searchable as SOLR
import indexing.postprod as PROD

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='validated')

global label_dict

def callback(ch, method, properties, body):

    global label_dict

    try:
        session_object = json.loads(body.decode('utf-8'))

        print("in function validated to initiate indexing...with file {}".format(session_object["id"]))

        # posting to index

        SOLR.add_session_to_index(label_dict, session_object)

        # posting to PRODUCTION index
        PROD.post_item_to_prod(label_dict, session_object)

        # mark messages acknoledged for inbound channel
        # ch.basic_ack(delivery_tag=method.delivery_tag)
    except FileNotFoundError:
        print("File could not be found " + str(session_object["id"]))
    except:
        print("Unknown error occured at " + str(session_object["id"]))



def init_consuming(db):


    print("start consuming for validated queue...")

    labels_meta = db.mongo_db.meta.find_one({"version" : 1, "type" : "label"})

    global label_dict
    label_dict = get_label_dict(labels_meta)

    # receive message and complete simulation
    channel.basic_consume(callback, queue='validated')
    channel.start_consuming()
