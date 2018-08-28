#!/usr/bin/env python
import pika
import json
import uuid
import os
import hashlib
from PIL import Image
import glob
from sqlalchemy import exc
from models.data_model import  Inspiration_Image

import requests

from sqlalchemy.orm import sessionmaker
from util import get_entity_name, get_file_name

from libs import googleimages


connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='gather')

global db


def process_crawled_image(db, session, object, search_phrase, userId):

    local_session = session()

    url = str(object["image_link"])
    source_page = str(object["image_source"])

    print("in function consuming inbound...with file {}".format(url))

    image_date = ""

    original_file_name = get_file_name(url)

    filename, file_extension = os.path.splitext(original_file_name)

    hash_object = hashlib.md5(url.encode('utf-8'))
    hash_str = hash_object.hexdigest()

    target_file_name = hash_str + file_extension

    target_path_download = os.environ.get('FILE_OUTPUT_FOR_COMFASH_APPLICATION')

    target_file_full_path_download = os.path.join(target_path_download, target_file_name)

    os.makedirs(os.path.dirname(target_file_full_path_download), exist_ok=True)

    # save image file to dedicated location

    r = requests.get(url, allow_redirects=True)
    open(target_file_full_path_download, 'wb').write(r.content)

    # saving the information to the SQL index
    new_inspiration = Inspiration_Image(urlHash=hash_str, url=url, sourcePage=source_page, classifyPath=target_file_full_path_download)

    local_session.add(new_inspiration)

    result_object = {
        "id" : hash_str,
        "session_owner" : "google-crawl",
        "keywords" : search_phrase,
        "target_file_name" : target_file_name,
        "orig_path" : url,
        "source_page": "source_page",
        "userId" : userId
    }

    try:
        local_session.commit()

        print("URL added to mysqlDB index")

        push_image_to_mongo(db, result_object)

        return result_object

    except exc.SQLAlchemyError as e:

        err_msg = e.args[0]
        local_session.rollback()

        if "1062," in err_msg:
            print("error, image already exists in inspirations-table")
        else:
            print("unknown error adding user")

        pass

def push_image_to_mongo(db, result_object ):

    session_object = {
        "id": result_object["id"],
        "issuerUserId" : result_object["userId"],
        "path": result_object["id"] + ".session",
        "owner": result_object["session_owner"],
        "isValidated": False,
        "isCrawled" : True,
        "isSetTrainOnly" : True,
        "origPath": result_object["orig_path"],
        "keywords" : result_object["keywords"],
        "origEntity": None,
        "sessionThumbnailPath": "/p/" + result_object["target_file_name"],
        "content_type": "parentDocument",
        "sourcePage": result_object["source_page"],
        "_childDocuments_": []
    }

    db.mongo_db.inspiration.insert_one(session_object)

def callback(ch, method, properties, body):

    # try:

    global db

    session = sessionmaker()
    session.configure(bind=db.engine)

    requestParams = json.loads(body.decode('utf-8'))

    search_phrase = str(requestParams["searchPhrase"])
    userId = str(requestParams["userId"])

    print("in function consuming gather...with search phrase {}".format(search_phrase))

    response = googleimages.googleimagesdownload()  # class instantiation

    arguments = {
        "keywords": search_phrase,
        "limit": 100,
        "print_urls": False
    }

    paths,url_paths,all_objects = response.download(arguments, channel, userId)  # passing the arguments to the function

    for img in all_objects:
        process_crawled_image(db, session, img, search_phrase, userId)
        # try:
        #     process_crawled_image(db, session, img, search_phrase, userId)
        #
        # except:
        #     print("Something went wrong for the image {}".format(img["image_source"]))


    # mark messages acknoledged for inbound channel
    ch.basic_ack(delivery_tag=method.delivery_tag)

    # except ValueError:
    #     print("Value error of the image, unknown type {}".format(ValueError))
    # except:
    #     print("Unknown error in processing the file")


def init_consuming_gather(data_base):

    global db
    db = data_base

    print("start consuming for gather...")

    # receive message and complete simulation
    channel.basic_consume(callback, queue='gather')
    channel.start_consuming()
