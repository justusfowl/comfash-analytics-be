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