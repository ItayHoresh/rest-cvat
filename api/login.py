import models
from flask import jsonify, send_file, make_response
import requestsApi as rqApi
import requests
from io import BytesIO
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
import app
from passlib.hash import django_pbkdf2_sha256

def loginRequest(auth):
    """Login cvat\n
        params:
            auth: json contains username and password
        return: json contains api_key token
    """
    if not auth or not auth.username or not auth.password:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'}) 

    user = models.User.query.filter_by(username=auth.username).first()

    if not user:
        return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'}) 

    algo, iterations, salt, hashTemp = user.password.split('$')

    if django_pbkdf2_sha256.using(rounds=int(iterations), salt=salt).verify(auth.password, user.password):
        token = jwt.encode({'id' : user.id, 'exp' : datetime.datetime.utcnow() + datetime.timedelta(days=365)}, app.app.config['SECRET_KEY'])
    
        return jsonify({'api_key' : token.decode('UTF-8')})

    return make_response('Could not verify', 401, {'WWW-Authenticate' : 'Basic realm="Login required!"'}) 