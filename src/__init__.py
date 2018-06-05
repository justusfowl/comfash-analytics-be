import argparse
import logging
import sys
import warnings

from dotenv import load_dotenv
from os.path import join, dirname

dotenv_path = join(dirname(__file__), '.env')
load_dotenv(dotenv_path=dotenv_path)

from consume import classify
from consume import inbound
from result import resultdata

from dbal import DB

list_of_choices = [
    'inbound',
    'classify',
    'reindex',
    'issue2classify'
]

parser = argparse.ArgumentParser(description='Comfash Analytics Processing')

parser.add_argument(
    '-r',
    '--routines',
    required=True,
    nargs='+',
    choices=list_of_choices,
    metavar='R',
    help='List of routines to run: {}'.format(', '.join(list_of_choices))
)

parser.add_argument(
    '--copythumbs',
    required=False,
    action='store_true',
    help='When routine = load_xml: empty xml staging data before load'
)

parser.add_argument("-m", "--models", nargs='+',
                    help="models to be rerun with routines=issue2classify", metavar="STRINGS")

parser.add_argument("-s", "--sessionid", help="sessionId to be rerun with routines=issue2classify", metavar="STRINGS")

def main(args=sys.argv[1:]):
    args = parser.parse_args(args)

    db = DB()

    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    logging.basicConfig(format='%(asctime)s %(relativeCreated)d %(levelname)s %(message)s',
                        filename='../comfash_logger.log', level=logging.DEBUG)
    logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    warnings.filterwarnings("ignore")


    if 'inbound' in args.routines:
        inbound.init_consuming(db)

    if 'classify' in args.routines:
        classify.init_consuming(db)

    if 'reindex' in args.routines:
        resultdata.reindex(db)

    if 'issue2classify' in args.routines:
        session_id = args.sessionid

        resultdata.issue_classify_queue(db, args.models, args.copythumbs, session_id)

