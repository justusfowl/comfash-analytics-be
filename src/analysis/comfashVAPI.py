import os
import sys
import numpy as np
import tensorflow as tf
import pandas as pd
import uuid

from PIL import Image
from dd_client import DD
from colorthief import ColorThief
import webcolors


sys.path.append("/home/uli/GCP/models/research/")
from object_detection.utils import ops as utils_ops
from object_detection.utils import label_map_util



class ComfashVAPI:
    def __init__(self):
        self.dd_host = os.environ.get('DD_HOST')
        self.dd = DD(self.dd_host)
        self.dd.set_return_format(self.dd.RETURN_PYTHON)

        # What model to download.
        MODEL_NAME = '/home/uli/GCP/models/research/output_inference_graph_fashion.pb'
        # MODEL_FILE = MODEL_NAME + '.tar.gz'
        # DOWNLOAD_BASE = 'http://download.tensorflow.org/models/object_detection/'

        # Path to frozen detection graph. This is the actual model that is used for the object detection.
        PATH_TO_CKPT = MODEL_NAME + '/frozen_inference_graph.pb'

        # List of the strings that is used to add correct label for each box.
        PATH_TO_LABELS = os.path.join('/home/uli/GCP/models/research/object_detection/data', 'fashion.pbtxt')

        NUM_CLASSES = 31

        self.detection_graph = tf.Graph()
        with self.detection_graph.as_default():
            od_graph_def = tf.GraphDef()
            with tf.gfile.GFile(PATH_TO_CKPT, 'rb') as fid:
                serialized_graph = fid.read()
                od_graph_def.ParseFromString(serialized_graph)
                tf.import_graph_def(od_graph_def, name='')

        self.label_map = label_map_util.load_labelmap(PATH_TO_LABELS)
        self.categories = label_map_util.convert_label_map_to_categories(self.label_map, max_num_classes=NUM_CLASSES,
                                                                    use_display_name=True)
        self.category_index = label_map_util.create_category_index(self.categories)

        df_rel_classes = pd.read_csv('/media/datadrive/google/relevant_classes.csv', sep=';')
        df_rel_classes.set_index("Class")
        self.df_rel_classes = df_rel_classes

    @staticmethod
    def load_image_into_numpy_array(image):
      (im_width, im_height) = image.size
      return np.array(image.getdata()).reshape(
          (im_height, im_width, 3)).astype(np.uint8)

    @staticmethod
    def get_description(df_rel_classes, input_class):
        res = df_rel_classes["ClassDescription"][df_rel_classes["Class"] == input_class]

        return res.get_values()[0]

    @staticmethod
    def get_target_class_models(df_rel_classes, input_class):
        res = df_rel_classes["TargetClassModels"][df_rel_classes["ClassDescription"] == input_class]
        try:
            return res.get_values()[0].replace(" ", "").split(",")
        except:
            print("error with {}".format(input_class))

    @staticmethod
    def crop_image_to_tile(image, coords):
        image_width = image.size[0]
        image_height = image.size[1]

        y_min = coords[0] * image_height
        y_max = coords[2] * image_height

        x_min = coords[1] * image_width
        x_max = coords[3] * image_width

        region = image.crop((x_min, y_min, x_max, y_max))
        outfile = os.path.join("/home/uli/tmpClassifyTiles", uuid.uuid4().hex + ".jpg")
        region.save(outfile, "JPEG")

        return outfile

    @staticmethod
    def map_color_to_name(rgb_triplet):
        min_colours = {}
        for key, name in webcolors.css21_hex_to_names.items():
            r_c, g_c, b_c = webcolors.hex_to_rgb(key)
            rd = (r_c - rgb_triplet[0]) ** 2
            gd = (g_c - rgb_triplet[1]) ** 2
            bd = (b_c - rgb_triplet[2]) ** 2
            min_colours[(rd + gd + bd)] = name
        return min_colours[min(min_colours.keys())]

    def detect_and_classify_items(self, file_path, session_id, requested_models):

        labels = []
        label_help_arr = []

        image = Image.open(file_path)

        image_np = self.load_image_into_numpy_array(image)

        # Actual detection.
        output_dict = self.run_inference_for_single_image(image_np, self.detection_graph)

        print("detection complete")

        dd_server = self.dd.info()
        services = [d['name'] for d in dd_server["head"]["services"]]

        min_score_thresh = .3
        min_score_thresh_classify = .3

        for i, item in enumerate(output_dict["detection_boxes"]):
            if output_dict["detection_scores"][i] > min_score_thresh:
                box_coords = item
                outfile = self.crop_image_to_tile(image, box_coords)

                score_value = round(output_dict["detection_scores"][i] * 100, 2)

                class_detected = output_dict["detection_classes"][i]
                class_label = self.category_index[class_detected]

                data = [outfile]
                target_models = self.get_target_class_models(self.df_rel_classes, class_label["name"])

                color_thief = ColorThief(outfile)
                # get the dominant color
                dominant_color = color_thief.get_palette(color_count=2)

                dom_color_name = self.map_color_to_name(dominant_color[0])

                new_help_label = {
                    "attr_type" : "detection",
                    "labels" : class_label["name"]
                }

                new_label = {
                    "path": session_id + ".session.label",
                    "id": uuid.uuid1().hex,
                    "labels": class_label["name"].lower(),
                    "prob": str(output_dict["detection_scores"][i]), #required workaround for correct storage in mongoDB
                    "attr_color": dom_color_name,
                    "attr_origin" : "cfvapi",
                    "attr_type" : "detection",
                    "bbox" : str(output_dict["detection_boxes"][i])
                }


                # work around to avoid duplicate labels upon detection and classification

                if new_help_label not in label_help_arr:
                    label_help_arr.append(new_help_label)
                    labels.append(new_label)

                for model in target_models:
                    sname = model.lower()
                    if sname in services and (sname in requested_models or 'all' in requested_models):

                        print("predicting for model {} ".format(sname))
                        print("predicting on file {}".format(outfile))

                        classif = self.dd.post_predict(sname, data, parameters_input={}, parameters_mllib={}, parameters_output={"best" : 5})
                        print(classif)

                        for pred in classif["body"]["predictions"][0]["classes"]:

                            if pred["prob"] > min_score_thresh_classify:

                                new_help_label = {
                                    "attr_type": sname,
                                    "labels": pred["cat"]
                                }

                                new_label = {
                                    "path": session_id + ".session.label",
                                    "id": uuid.uuid1().hex,
                                    "labels" : pred["cat"].lower(),
                                    "prob" : str(pred["prob"]),  #required workaround for correct storage in mongoDB
                                    "attr_color" : dom_color_name,
                                    "attr_origin" : "cfvapi",
                                    "attr_type" : sname,
                                    "bbox": str(output_dict["detection_boxes"][i])
                                }

                                if new_help_label not in label_help_arr:
                                    label_help_arr.append(new_help_label)
                                    labels.append(new_label)

                    else:
                        print("model {} not found on dd-service".format(sname))

                os.unlink(outfile)

        print("resulting labels from analysis")
        print(labels)
        return labels

    @staticmethod
    def run_inference_for_single_image(image, graph):
      with graph.as_default():
        with tf.Session() as sess:
          # Get handles to input and output tensors
          ops = tf.get_default_graph().get_operations()
          all_tensor_names = {output.name for op in ops for output in op.outputs}
          tensor_dict = {}
          for key in [
              'num_detections', 'detection_boxes', 'detection_scores',
              'detection_classes', 'detection_masks'
          ]:
            tensor_name = key + ':0'
            if tensor_name in all_tensor_names:
              tensor_dict[key] = tf.get_default_graph().get_tensor_by_name(
                  tensor_name)
          if 'detection_masks' in tensor_dict:
            # The following processing is only for single image
            detection_boxes = tf.squeeze(tensor_dict['detection_boxes'], [0])
            detection_masks = tf.squeeze(tensor_dict['detection_masks'], [0])
            # Reframe is required to translate mask from box coordinates to image coordinates and fit the image size.
            real_num_detection = tf.cast(tensor_dict['num_detections'][0], tf.int32)
            detection_boxes = tf.slice(detection_boxes, [0, 0], [real_num_detection, -1])
            detection_masks = tf.slice(detection_masks, [0, 0, 0], [real_num_detection, -1, -1])
            detection_masks_reframed = utils_ops.reframe_box_masks_to_image_masks(
                detection_masks, detection_boxes, image.shape[0], image.shape[1])
            detection_masks_reframed = tf.cast(
                tf.greater(detection_masks_reframed, 0.5), tf.uint8)
            # Follow the convention by adding back the batch dimension
            tensor_dict['detection_masks'] = tf.expand_dims(
                detection_masks_reframed, 0)
          image_tensor = tf.get_default_graph().get_tensor_by_name('image_tensor:0')

          # Run inference
          output_dict = sess.run(tensor_dict,
                                 feed_dict={image_tensor: np.expand_dims(image, 0)})

          # all outputs are float32 numpy arrays, so convert types as appropriate
          output_dict['num_detections'] = int(output_dict['num_detections'][0])
          output_dict['detection_classes'] = output_dict[
              'detection_classes'][0].astype(np.uint8)
          output_dict['detection_boxes'] = output_dict['detection_boxes'][0]
          output_dict['detection_scores'] = output_dict['detection_scores'][0]
          if 'detection_masks' in output_dict:
            output_dict['detection_masks'] = output_dict['detection_masks'][0]
      return output_dict