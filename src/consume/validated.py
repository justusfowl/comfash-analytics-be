#!/usr/bin/env python
import pika
import json

import indexing.searchable as SOLR
import indexing.postprod as PROD

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='validated')


def callback(ch, method, properties, body):

    try:
        session_object = json.loads(body.decode('utf-8'))

        print("in function validated to initiate indexing...with file {}".format(session_object["id"]))

        # posting to index

        SOLR.add_session_to_index(session_object)

        # posting to PRODUCTION index
        PROD.post_item_to_prod(session_object)

        # mark messages acknoledged for inbound channel
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except FileNotFoundError:
        print("File could not be found " + str(session_object["id"]))
    except:
        print("Unknown error occured at " + str(session_object["id"]))



def init_consuming():


    print("start consuming for validated queue...")

    # receive message and complete simulation
    channel.basic_consume(callback, queue='validated')
    channel.start_consuming()
