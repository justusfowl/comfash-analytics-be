from urllib.parse import urlparse

def get_file_name(url):
    if url.find('/'):
      return url.rsplit('/', 1)[1]



def get_entity_name(url):
    o = urlparse(url)
    d = o.netloc

    if "www." in d:
        name = d[4:]
    else:
        name = d

    return name

def get_label_dict(meta_object):

    all_labels = {}

    # add colors first

    for color in meta_object["color"]:
        all_labels[color["name"]] = color


    def get_label(input_arr):

        for i in input_arr:

            if "children" in i:

                obj = {
                    "translation" : i["translation"]
                }
                if i["attr_type"] not in all_labels:
                    all_labels[i["attr_type"]] = obj
                get_label(i["children"])
            else:
                if "label" in i:
                    all_labels[i["label"]] = i


    get_label(meta_object["meta"])

    return all_labels

def get_label_translation(label_dict, input_str, lang_key):

    try:
        translation = label_dict[input_str]["translation"][lang_key]
        return translation
    except:
        print("Translation for {} could not be found for {}".format(input_str, lang_key))
        return ""
