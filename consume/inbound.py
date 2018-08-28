#!/usr/bin/env python
import pika
import json
import uuid
import os
import hashlib
from PIL import Image
import glob

from models.data_model import  Inspiration_Image
from util import get_file_name

import requests

from sqlalchemy.orm import sessionmaker
from util import get_entity_name, get_file_name


connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

channel.queue_declare(queue='inbound')
channel.queue_declare(queue='classify')

global db




def callback(ch, method, properties, body):

    try:

        global db

        session = sessionmaker()
        session.configure(bind=db.engine)

        local_session = session()

        requestParams = json.loads(body.decode('utf-8'))



        url = str(requestParams["url"])
        source_page = str(requestParams["sourcePage"])

        print("in function consuming inbound...with file {}".format(url))

        if "imageDate" in requestParams:
            image_date = str(requestParams["imageDate"])
        else:
            image_date = ""

        original_file_name = get_file_name(url)

        filename, file_extension = os.path.splitext(original_file_name)



        hash_object = hashlib.md5(url.encode('utf-8'))
        hash_str = hash_object.hexdigest()

        target_file_name = hash_str + file_extension

        target_path_download = os.environ.get('FILE_OUTPUT_PATH_FROM_DOWNLOAD')

        target_file_full_path_download = target_path_download + target_file_name

        os.makedirs(os.path.dirname(target_file_full_path_download), exist_ok=True)

        # save image file to dedicated location

        r = requests.get(url, allow_redirects=True)
        open(target_file_full_path_download, 'wb').write(r.content)

        # create smaller image for display / classification
        size = 680, 680

        target_path_thumbnails = os.environ.get('FILE_OUTPUT_PATH_FOR_CLASSIFY')

        target_file_full_path_thumbnail = target_path_thumbnails + target_file_name

        im = Image.open(target_file_full_path_download)
        im.thumbnail(size)

        if file_extension[1:].upper() == "JPG" or file_extension[1:].upper() == "JPEG":
            im.save(target_file_full_path_thumbnail, "JPEG")
        elif file_extension[1:].upper() == "PNG":
            im.save(target_file_full_path_thumbnail, "PNG")
        else:
            raise ValueError("Unsupported type of image {}".format(file_extension[1:].upper()))


        # temporary solution for owner

        message = {
            "sessionId" : hash_str,
            "fileName" : target_file_name,
            "sessionOwner": get_entity_name(url),
            "origPath": url,
            "origEntity": get_entity_name(url),
            "sessionThumbnailPath": target_file_full_path_thumbnail,
            "targetModels" : ["all"],
            "flagCopyThumbs" : True,
            "sourcePage" : source_page,
            "imageDate" : image_date
        }

        inspiration_image = local_session.query(Inspiration_Image).filter_by(urlHash=hash_str).first()
        inspiration_image.classifyPath = target_file_full_path_thumbnail
        local_session.commit()
        local_session.close()

        # create new message in queue for classification
        channel.basic_publish(exchange='', routing_key='classify', body=json.dumps(message, ensure_ascii=False))

        # mark messages acknoledged for inbound channel
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except ValueError:
        print("Value error of the image, unknown type {}".format(ValueError))
    except:
        print("Unknown error in processing the file")


def init_consuming(data_base):

    global db
    db = data_base

    print("start consuming for inbound...")

    # receive message and complete simulation
    channel.basic_consume(callback, queue='inbound')
    channel.start_consuming()
