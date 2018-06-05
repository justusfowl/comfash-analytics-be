from dd_client import DD
import os

# setting up DD client
host = os.environ.get('DD_HOST')
dd = DD(host)
dd.set_return_format(dd.RETURN_PYTHON)

def classify_image(target_model, file_name):

    sname = target_model

    parameters_input = {}
    parameters_mllib = {}
    parameters_output = {'best': 5}
    data = [file_name]

    classif = dd.post_predict(sname, data, parameters_input, parameters_mllib, parameters_output)

    cf_labels = classif["body"]["predictions"][0]["classes"]

    result_cf_labels = []

    for label in cf_labels:
        cf_label = {}

        cf_label["cat"] = label["cat"]
        cf_label["prob"] = label["prob"]

        result_cf_labels.append(cf_label)

    return result_cf_labels


