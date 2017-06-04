# Built in modules
import logging
import os
import shutil
import sys

# Third-part modules
import cv2
import numpy as np

from peewee import *

'''
Opencv operations for detect, predict and crop the images.

DESCRIPTION
===========

This script is used for training the images for facerecognition purposed.
The functions are also used by other models such as tornado for the server
authentication purposes.

Files
=====

write a file , ``model.mdl``
create database file, ``data/images.db``


'''

MODEL_FILE = "model.mdl"
db = SqliteDatabase("data/images.db")


class BaseModel(Model):

    class Meta:
        database = db   # Images database


class Label(BaseModel):
    """
    Database table to store user label.
    """

    IMAGE_DIR = "data/images"
    name = CharField()

    def persist(self):
        """
        A method to save the label.
        """
        path = os.path.join(self.IMAGE_DIR, self.name)
        #if directory exists with 10 images
        #delete it and recreate
        if os.path.exists(path) and len(os.listdir(path)) >= 10:
            shutil.rmtree(path)

        if not os.path.exists(path):
            logging.info("Created directory: %s" % self.name)
            os.makedirs(path)

        Label.get_or_create(name=self.name)


class Image(BaseModel):
    """
    Database  table to store images.
    """

    IMAGE_DIR = "data/images"
    path = CharField()
    label = ForeignKeyField(Label)

    def persist(self, cv_image):
        """
        A method to save the images.
        """
        path = os.path.join(self.IMAGE_DIR, self.label.name)
        nr_of_images = len(os.listdir(path))
        if nr_of_images >= 10:
            return 'Done'
        faces = detect_faces(cv_image)
        if len(faces) > 0 and nr_of_images < 10:
            path += "/%s.jpg" % nr_of_images
            path = os.path.abspath(path)
            logging.info("Saving %s" % path)
            cropped = to_grayscale(crop_faces(cv_image, faces))
            cv2.imwrite(path, cropped)
            self.path = path
            self.save()

def detect(img, cascade):
    """
    A function to detect presence of a face.
    """

    gray = to_grayscale(img)
    scale_factor = 1.2
    min_neighbors = 5
    min_size = (30, 30)
    biggest_only = True
    flags = cv2.CASCADE_FIND_BIGGEST_OBJECT | \
            cv2.CASCADE_DO_ROUGH_SEARCH if biggest_only else \
            cv2.CASCADE_SCALE_IMAGE

    rects = cascade.detectMultiScale(gray, scaleFactor=scale_factor,
            minNeighbors=min_neighbors, minSize=min_size, flags=flags)

    # If nothing has been detected as a face
    if len(rects) == 0:
        return []
    return rects

def detect_faces(img):
    """
    A  function that uses haarcascade to detect faces.
    """

    cascade = cv2.CascadeClassifier("data/haarcascade_frontalface_alt.xml")
    return detect(img, cascade)

def to_grayscale(img):
    """
    A function to convert rbg image to gray scale.
    """

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    gray = cv2.equalizeHist(gray)
    return gray

def contains_face(img):
    """
    A function that return a region that contain face.
    """

    return len(detect_faces(img)) > 0

def save(path, img):
    """
    A function to save the images in ``data/images`` directory.

    Args:
        path: path for images directory.
        img: image
    """

    cv2.imwrite(path, img)

def crop_faces(img, faces):
    """
    A function to crop the images.
    """

    for face in faces:
        x, y, h, w = [result for result in face]
        center = (x + w / 2, y + h / 2)
        axis_major = h / 2
        axis_minor = w / 2
        mask = np.zeros_like(img)
        # create a white filled ellipse
        mask = cv2.ellipse(mask, center=center, axes=(axis_major, axis_minor),
                           angle=0, startAngle=0, endAngle=360,
                           color=(255, 255, 255), thickness=-1)
        # Bitwise AND operation to black out regions outside the mask
        images_ellipse = np.bitwise_and(img, mask)

    return images_ellipse[y:y+h,x:x+w]


def load_images(path):
    """
    A function to load the images from a given path.

    Args:
        path: image path.
    """

    images, labels = [], []
    c = 0
    print "test " + path
    for dirname, dirnames, filenames in os.walk(path):
        print "test"
        for subdirname in dirnames:
            subjectPath = os.path.join(dirname, subdirname)
            for filename in os.listdir(subjectPath):
                try:
                    img = cv2.imread(os.path.join(subjectPath, filename),
                    cv2.IMREAD_GRAYSCALE)
                    images.append(np.asarray(img, dtype=np.uint8))
                    labels.append(c)
                except IOError, (errno, strerror):
                    print "IOError({0}): {1}".format(errno, strerror)
                except:
                    print "Unexpected error:" , sys.exc_info()[0]
                    raise
            c += 1
    return images, labels

def load_images_to_db(path):
    """
    A function to load the images from the database.

    Args:
        path: image path.
    """

    for dirname, dirnames, filenames in os.walk(path):
        for subdirname in dirnames:
            subject_path = os.path.join(dirname, subdirname)
            label, created = Label.get_or_create(name=subdirname)
            label.save()
            for filename in os.listdir(subject_path):
                path = os.path.abspath(os.path.join(subject_path, filename))
                logging.info('saving path %s' % path)
                image, created = Image.get_or_create(path=path, label=label)
                image.save()

def load_images_from_db():
    """
    A function to load the images from database.
    """

    images, labels = [],[]
    for label in Label.select():
        for image in label.image_set:
            try:
                cv_image = cv2.imread(image.path, cv2.IMREAD_GRAYSCALE)
                cv_image = cv2.resize(cv_image, (100,100))
                images.append(np.asarray(cv_image, dtype=np.uint8))
                labels.append(label.id)
            except IOError, (errno, strerror):
                print "IOError({0}): {1}".format(errno, strerror)
    return images, np.asarray(labels)

def train():
    """
    A function to train the images loaded from database.
    """

    images, labels = load_images_from_db()
    model = cv2.face.createFisherFaceRecognizer()
    #model = cv2.createEigenFaceRecognizer()
    #model = cv2.face.createLBPHFaceRecognizer()
    model.train(images,labels)
    model.save(MODEL_FILE)

    return True

def predict(cv_image):
    """
    A function to predict the person infront of the camera.

    Args:
        cv_image: image captured from stream of video frames.

    Returns:
        result: Return results.
    """

    faces = detect_faces(cv_image)
    result = None
    if len(faces) > 0:
        cropped = to_grayscale(crop_faces(cv_image, faces))
        resized = cv2.resize(cropped, (100,100))

        model = cv2.face.createFisherFaceRecognizer()
        #model = cv2.createEigenFaceRecognizer()
        #nmodel = cv2.face.createLBPHFaceRecognizer()
        model.load(MODEL_FILE)
        prediction = model.predict(resized)
        result = {
                  'face': {
                          'name': Label.get(Label.id == prediction[0]).name,
                          'distance': prediction[1],
                          'coords': {
                                    'x': str(faces[0][0]),
                                    'y': str(faces[0][1]),
                                    'width': str(faces[0][2]),
                                    'height': str(faces[0][3])
                                    }
                          }
                 }
    return result

if __name__ == "__main__":
    print "Beginning training"
    train()
    print "Done training"
