#! /usr/bin/env python2.7
# Import built in modules
import json
import logging
import mimetypes
import ntpath
import os
import os.path
import ssl
import StringIO
import time

# Import third-part modules
import numpy
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket

from PIL import Image
from tornado.options import define, options

# Import custom modules
from admin import admin
from opencv import opencv

'''
Tornado server to handles user's requests, websocket and opencv process.

SYNOPSIS
========

::

    server.py [--port] [--listen-address]

DESCRIPTION
===========

This script start webserver that is capable of processing http requests and
websocket functionalities including opencv as an authentication module.

OPTIONS
=======

``--port``  specify the listen port for the server default is port 8888.

``--listen-address`` specify the listen address for the server default is
    127.0.0.1.

ENVIRONMENT
===========

::
    os.path loads the paths for data/images

EXAMPLES
========

::
    1. python2.7 server.py
    2. python2.7 server.py --port 8080 --listen-address 192.168.56.25


SEE ALSO
========

For more information on this script see the README_.

.. _README: http://github.com/hemedy99/file-server

'''

define("port", default=8888, help="run on the given poort", type=int)
define("listen_address", group="webserver", default="127.0.0.1", help="Listen\
        address")
# # enable ssl connection to secure the user bio data
# ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
# ssl_ctx.load_cert_chain(os.path.join('/home/hemedy99/Code/Python2.7',
#     "mycert.pem"))


class Application(tornado.web.Application):

    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/facedetector", FaceDetectHandler),
            (r"/enrol", SetupHarvestHandler),
            (r"/harvesting", HarvestHandler),
            (r"/predict", PredictHandler),
            (r"/train", TrainHandler),
            (r"/admin/login/", AdminLoginHandler),
            (r"/admin/logout/", AdminLogoutHandler),
            (r"/admin-panel", AdminPanelHandler),
            (r"/admin-panel/train", AdminTrainHandler),
            (r"/admin-panel/enrol", AdminEnrolHandler),
            (r"/(.*)", ServerFilesHandler)
            ]

        settings = dict(
            cookie_secret="asdsafl.rleknknfkjqweonrkbknoijsdfckjnk 234jn",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            login_url="/admin/login/",
            xsrf_cookies=False,
            autoescape=None,
            debug=True
            )
        tornado.web.Application.__init__(self, handlers, **settings)


class MainHandler(tornado.web.RequestHandler):
    """
    Class that contains the main handler start page for face detection.
    """

    def get(self):
        """
        This module render facedetect.html  that is used to authenticate the
        user by face recognition.
        """
        self.render("facedetect.html")


class SocketHandler(tornado.websocket.WebSocketHandler):
    """
    This class define several methods for open,status,close and reply to the
    users requests.
    """

    def open(self):

        logging.info('new connection') # Display logging info in the terminal

    def on_message(self, message):
        """
        This module process the user's request.

        Args:
            message: process the image received.
        """
        image = Image.open(StringIO.StringIO(message))
        cv_image = numpy.array(image)
        self.process(cv_image)

    def on_close(self):

        logging.info('connection closed')

    def process(self, cv_image):
        pass


class FaceDetectHandler(SocketHandler):
    """
    A class that contains  methods that process the  detection of the face
    when client connect tho the server.
    """
    def process(self, cv_image):
        """
        This method calls detect_faces from opencv module.

        Args:
            cv_image: detect_faces function use this image to detect presence
                      of a face.
        """
        faces = opencv.detect_faces(cv_image)
        if len(faces) > 0:
            # If a face has been detected display the results
            # in json format
            result = json.dumps(faces.tolist())
            self.write_message(result)


class SetupHarvestHandler(tornado.web.RequestHandler):
    """
    This class contain useful methods that are used to harvest data for a new
    user for the registration purposes.
    """

    def get(self):

        self.render("harvest.html")

    def post(self):

        name = self.get_argument("label", None)

        if not name:
            logging.error("No label, bailing out")
            return
        logging.info("Got label %s" %  name)
        opencv.Label(name=name).persist() # Save the label.
        logging.info("Setting secure cookie %s" % name)
        self.set_secure_cookie('label', name)
        self.redirect("/") # Redirect the user to the startpage


class HarvestHandler(SocketHandler):
    """
    This class define a method that is used to process new user data based on
    the image and label.
    """

    def process(self, cv_image):
        """
        A function to get the user lable, cookie and prepaire a json  string.

        Args:
            cv_image: face image captured from video frames captured.
        """
        label = opencv.Label.get(opencv.Label.name ==
                                self.get_secure_cookie('label'))
        logging.info("Got label: %s" % label.name)
        if not label:
            logging.info("No cookie, bailing out")
            return
        logging.info("About to save image")
        result = opencv.Image(label=label).persist(cv_image)
        if result == 'Done':
            self.write_message(json.dumps(result))


class TrainHandler(tornado.web.RequestHandler):
    """
    This class contain a method that process the user's request by calling
    function ``train`` from opencv module.
    """

    def post(self):
        """
        This method send request to the server for opencv to start trainning
        the  images.
        """
        opencv.train()


class PredictHandler(SocketHandler):
    """
    This class contains the method that handles the predition for the
    client connected to the server
    """

    def process(self, cv_image):
        """
        This method start the prediction of the client connected to the
        server.

        Args:
            cv_image: face image from video frames captured.
        """
        result = opencv.predict(cv_image)
        if result:
            self.write_message(json.dumps(result))


class AdminLoginHandler(tornado.web.RequestHandler):
    """
    This class handler login page for authenticating admin by username and a
    password.
    """

    def get(self):

        self.render("admin-login.html")
        logging.info("new connection established.")

    def post(self):

        # Initialize username and password
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")

        # Check if the username and password matches
        auth = admin.authUser(username, password)

        if auth:
            self.set_secure_cookie("user", username)
            self.redirect("/admin-panel")
        else:
            error_msg = u"?error=" + tornado.escape.url_escape("Login incorrect")
            self.redirect(u"/admin/login/" + error_msg)


class AdminLogoutHandler(tornado.web.RequestHandler):
    """
    Logout handler that clear the login user cookie and redirect the user to
    the main page.
    """

    def get(self):

        self.clear_cookie("user")
        self.redirect("/")


class AdminPanelHandler(tornado.web.RequestHandler):
    """
    Admin panel handler that checks whether the user is authenticated to access
    the admin control panel.
    """

    def get_current_user(self):

        return self.get_secure_cookie("user")

    @tornado.web.authenticated
    def get(self):
        username = tornado.escape.xhtml_escape(self.current_user)
        self.render("admin-panel.html", username=username)


class AdminTrainHandler(tornado.web.RequestHandler):
    """
    Admin train handler for training the images.
    """

    def get(self):
        logging.info("Training the model.")
        opencv.train()



class AdminEnrolHandler(tornado.web.RequestHandler):
    """
    Enroll new users handler .
    """

    def get(self):
        self.redirect("/enrol")

class ServerFilesHandler(tornado.web.RequestHandler):
    """
    This class  define methods that process the contents of the files that
    recides within the server e.g video, images, documents e.t.c.
    """

    SUPPORTED_METHODS = ['GET']

    def get(self, path):
        """
        GET method to list contents of directory or
        write index page if index.html exists.

        Args:
            path: define a path to the files(url).
        """

        for index in ['index.html', 'index.htm']:
            index = os.path.join(path, index)
            if os.path.exists(index):
                with open(index, 'rb') as f:
                    self.write(f.read())
                    self.finish()
                    return
        html = self.generate_index(path)
        self.write(html)
        self.finish()

    def generate_index(self, path):
        """
        This method generate the  index.html for files and their proper mime
        types.

        Args:
            path: url path for the files.
        """

        if os.path.isdir(path):
            files = os.listdir(path)
        else:
            files = [path]
            mime_type, encoding = mimetypes.guess_type(path)
            self.set_header("Content-Type", mime_type or 'text/plain')
        files = [ path + '/' + filename + '/'
                if os.path.isdir(os.path.join(path, filename))
                else filename
                for filename in files]
        html_template = """
        <!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN"><html>
        <title>Directory listing for /{{ path }}</title>
        <body>
        <h2>Directory listing for /{{ path }}</h2>
        <hr>
        <ul>
        {% for filename in files %}
        <li><a href="{{ filename }}">{{ filename }}</a>
        {% end %}
        </ul>
        <hr>
        </body>
        </html>
        """
        t = tornado.template.Template(html_template)
        return t.generate(files=files, path=path)


def main():
    """
    Our main function to start the server.
    """

    tornado.options.parse_command_line()
    opencv.Image().delete()
    logging.info("Images deleted")
    opencv.Label().delete()
    logging.info("Labels deleted")
    opencv.load_images_to_db("data/images")
    logging.info("Labels and images loaded")
    opencv.train()
    logging.info("Model trained")
    app = Application()
    app.listen(options.port)
    # http_server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_ctx)
    # http_server.listen(options.port, address=options.listen_address)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
  main()
