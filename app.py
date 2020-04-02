from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
import os
import ptvsd
from requestsApi import *
from api.tags import getTagsFromDB
from api.login import loginRequest
from api.status import getStatusRequest, getTasksByStatusRequest
from api.watershed_images import getWatershedImageRequest
from api.count_frames import getCountFinishFramesRequest
from api.tags import getTagsFromDB
from api.task import putUpdateVideosScore
from api.task import createTaskRequest
from models import *
from functools import wraps
import jwt

# Init app
app = Flask(__name__)
basedir = os.path.abspath(os.path.dirname(__file__))

app.config['SECRET_KEY'] = 'CVAT-API'

# Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://' + os.environ.get('DB_USER') + ':' + os.environ.get('DB_PASSWORD') + '@' + os.environ.get('DB_HOST_IP') + ':5432/' + os.environ.get('DB_NAME')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

def token_required(f):
    """
    In each request, the client must send api_key to the server in headers.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        current_user = None
        data = {}
        if request.method == 'POST':
            data = request.get_json()
        if 'secret' not in data or data['secret'] != os.environ.get('API_SECRET'):
            if 'api_key' in request.headers:
                token = request.headers['api_key']
            
            if not token:
                return jsonify({'message' : 'Token is missing ! Login Required'}), 401

            try:
                data = jwt.decode(token, app.config['SECRET_KEY'])
                current_user = User.query.filter_by(id=data['id']).first()
            except:
                return jsonify({'message' : 'Token is invalid!'}), 401

        return f(current_user, *args, **kwargs)
    
    return decorated

def auth_required(f):
    """
    In each request, the client must be authorize to get the response according to the user id and project name.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        data = {}
        if request.method == 'POST':
            data = request.get_json()
        if 'secret' not in data or data['secret'] != os.environ.get('API_SECRET'):
            pname = request.args.get('project.name')
            
            if pname is None:
                return jsonify({'message' : 'Project name is missing!'}), 401

            current_user = args[0]
            if not checkifAuthorize(pname, current_user.id) :
                return jsonify({'message' : 'You are not authorized !'})
            
        return f(*args, **kwargs)
    
    return decorated

@app.errorhandler(404)
def page_not_found(e):
    return make_response('Not Found', 404) 

@app.route("/")
def index():
    return render_template("api.html")

@app.route("/swagger")
def swagger():
    
    with open('swagger.json') as json_file:
        data = json.load(json_file)
    
    return jsonify(data)

@app.route('/model/<string:modelName>', methods=['GET'])
@token_required
@auth_required
def get(current_user, modelName):

    data = request.args

    model = eval(modelName.capitalize())

    response = getRequest(data, model)

    return response

@app.route('/watershed/images', methods=['GET', 'POST'])
@token_required
@auth_required
def getWatershedImage(current_user):
    data = request.args

    response = getWatershedImageRequest(data)

    return response

@app.route('/task/status', methods=['GET'])
@token_required
@auth_required
def getStatus(current_user):
    data = request.args

    response = getStatusRequest(data)

    return response

@app.route('/tasks', methods=['GET'])
@token_required
@auth_required
def getTasksByStatus(current_user):
    data = request.args

    response = getTasksByStatusRequest(data)

    return response
    
@app.route('/count/frames', methods=['GET'])
@token_required
@auth_required
def getCountFinishFrames(current_user):
    data = request.args

    response = getCountFinishFramesRequest(data)
    
    return response

@app.route('/task/annotations', methods=['GET'])
@token_required
@auth_required
def getTags(current_user):
    data = request.args
    
    response = getTagsFromDB(data)

    return response

@app.route('/update/score/tasks', methods=['PUT'])
@token_required
@auth_required
def updateVideosScore(current_user):
    data = request.get_json()
    args = request.args
    response = putUpdateVideosScore(data, args)

    return response

@app.route('/task/create', methods=['POST'])
@token_required
@auth_required
def createTask(current_user):
    response = createTaskRequest(request, current_user)

    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    response = loginRequest(request.authorization)

    return response
    
if __name__ == '__main__':
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)