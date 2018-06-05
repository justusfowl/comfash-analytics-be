import json
import pika

import indexing.searchable as SOLR
from sqlalchemy.sql import select
from models import data_model

from util import get_file_name, get_entity_name

def insert_session_object_to_mongo(db, session_object):

    session_id = session_object["id"]
    db.mongo_db.inspiration.delete_one({"id": session_id})

    db.mongo_db.inspiration.insert_one(session_object)


def reindex(db):

    SOLR.remove_index()

    result_data = db.mongo_db.inspiration.find()

    for item in result_data:
        my_item = item
        my_item.pop("_id", None)

        print("indexing: " + str(my_item["id"]))

        SOLR.add_session_to_index(my_item)

    print("reindexing complete")


def issue_classify_queue(db, target_models=["all"], flag_copy_thumbs=False, session_id=None):

    if session_id is not None:
        s = select([data_model.Inspiration_Image]).where(data_model.Inspiration_Image.urlHash == session_id)
    else:
        s = select([data_model.Inspiration_Image])

    result = db.conn.execute(s)

    MQ_connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = MQ_connection.channel()
    channel.queue_declare(queue='classify')

    for row in result:
        print(row)

        url = row["url"]
        classify_path = row["classifyPath"]
        source_page = row["sourcePage"]
        file_name = classify_path.rsplit('/', 1)[1]

        message = {
            "sessionId": row["urlHash"],
            "fileName": file_name,
            "sessionOwner": get_entity_name(url),
            "origPath": url,
            "origEntity": get_entity_name(url),
            "sessionThumbnailPath": classify_path,
            "targetModels" : target_models,
            "flagCopyThumbs" : flag_copy_thumbs,
            "sourcePage" : source_page
        }

        message_obj = json.dumps(message)

        channel.basic_publish(exchange='',routing_key='classify',body=message_obj)

    result.close()

    print("issuing to queue: classify complete")