import io

# Imports the Google Cloud client library
from google.cloud import vision
from google.cloud.vision import types

# Instantiates a client
client = vision.ImageAnnotatorClient()

def classify_labels(file_name):

    # Loads the image into memory
    with io.open(file_name, 'rb') as image_file:
        content = image_file.read()

    image = types.Image(content=content)

    # Performs label detection on the image file
    response = client.label_detection(image=image)
    labels = response.label_annotations

    result_g_labels = []

    for label in labels:
        g_label = {}

        g_label["cat"] = label.description
        g_label["prob"] = label.score
        g_label["mid"] = label.mid

        result_g_labels.append(g_label)


    return result_g_labels