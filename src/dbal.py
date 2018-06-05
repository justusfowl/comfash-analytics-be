import os
from sqlalchemy import create_engine
import pymongo

class DB:

    def __init__(self):
        password = os.environ.get('MYSQL_DB_PASS')
        if password is None:
            CONNECTION_STRING = "{drivername}://{user}@{host}:{port}/{db_name}?charset=utf8".format(
                drivername="mysql+pymysql",
                user=os.environ.get('MYSQL_DB_USER'),
                passwd=os.environ.get('MYSQL_DB_PASS'),
                host=os.environ.get('MYSQL_DB_HOST'),
                port=os.environ.get('MYSQL_DB_PORT'),
                db_name=os.environ.get('MYSQL_DB_DB')
            )
        else:
            CONNECTION_STRING = "{drivername}://{user}:{passwd}@{host}:{port}/{db_name}?charset=utf8".format(
                user=os.environ.get('MYSQL_DB_USER'),
                passwd=os.environ.get('MYSQL_DB_PASS'),
                host=os.environ.get('MYSQL_DB_HOST'),
                port=os.environ.get('MYSQL_DB_PORT'),
                db_name=os.environ.get('MYSQL_DB_DB')
            )

        self.engine = create_engine(CONNECTION_STRING, encoding='utf-8')
        self.conn = self.engine.connect()

        mongo_conn_string = "mongodb://{user}:{passwd}@{host}:{port}/{db_name}".format(
            user=os.environ.get('MONGO_DB_USER'),
            passwd=os.environ.get('MONGO_DB_PASS'),
            host=os.environ.get('MONGO_DB_HOST'),
            port=os.environ.get('MONGO_DB_PORT'),
            db_name=os.environ.get('MONGO_DB_DB')
        )

        self.mongo_client = pymongo.MongoClient(mongo_conn_string)
        self.mongo_db = self.mongo_client.cfdata
