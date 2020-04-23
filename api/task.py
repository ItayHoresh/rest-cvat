import models
from flask import jsonify
import requestsApi as rqApi
from sqlalchemy import func, String
from sqlalchemy.dialects.postgresql import ARRAY
import traceback
import json
import app
import requests
from collections import defaultdict
import os
import urllib3
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

def getOsId(path):
    """Get the id of the object storage according the two dir name in path
        params:
            path: path to file in s3    
    retrun: the id of the object storage    
    """
    splited_path = path.split('/')
    new_path = splited_path[0:2]
    new_path = '/'.join(new_path)
    object_storage_id = models.Objectstorages.query.filter_by(name=new_path).first().id

    return object_storage_id

def parseLabelsToDict(labels):
    """Parse labels from db to dictionary that work with the parser to string
        params:
            labels: all labels from db according to the project
    example result: {'animal': [], 'person': [{'age': []}], 'vehicle': [{'bus': []}, {'car': ['mazda', 'toyota']}, {'truck': ['long']}]}
    :return: labels dict
    """
    dictLabels = defaultdict(list)
    labels = list(map(lambda label : { label[0]: {
                                                    label[1]: label[2]
                                                 }
                                     }, labels))
    
    # For each label in list add the attribute to the label 
    for dictLabel in labels:
        for label, attr_vals in dictLabel.items():
            if None not in attr_vals:
                for attr in attr_vals.keys():
                    attr_vals[attr].remove(None)
                dictLabels[label].append(attr_vals)
            elif label not in dictLabels:
                dictLabels[label] = []
    return dictLabels

def parseDictToString(labels):
    """Parse labels from dict to string taht works with cvat
        params:
            labels: all labels in dictionary mode 
            example param value: {'animal': [], 'person': [{'age': []}], 'vehicle': [{'bus': []}, {'car': ['mazda', 'toyota']}, {'truck': ['long']}]}
    example result: animal person ~select=age: vehicle ~select=bus: ~select=car:mazda,toyota ~select=truck:long
    :return: labels string
    """
    labelString = ""
    for label, attr_vals in labels.items():
        labelString += label 
        for attr_val in attr_vals:
            for attr, values in attr_val.items():
                labelString += " ~select="
                labelString += attr + ":"
                for value in values:
                    labelString += value  
                    if values.index(value) != len(values) - 1:
                        labelString += ","
        labelString += " "

    return labelString

def getLabelString(pid):
    """Parse labels from db that works with cvat
        params:
            pid: the project id
    :return: labels string
    """
    project = models.Projects.query.filter_by(id=pid).first()
    labels = models.Labeltypes.query.filter_by(project=project)
    labels = labels.with_entities(models.Labeltypes.label, models.Labeltypes.attribute, func.array_agg(models.Labeltypes.value, type_=ARRAY(String))).group_by(models.Labeltypes.label, models.Labeltypes.attribute).all()
    labels = parseLabelsToDict(labels)
    labels = parseDictToString(labels)

    return labels

def getFrameProperties(pid):
    """Parse frame properties from db that works with cvat
        params:
            pid: the project id
    :return: frame properties json array (the parseer in cvat to json.loads(..))
    """
    project = models.Projects.query.filter_by(id=pid).first()
    frame_props = models.Frameproperties.query.filter_by(project=project).filter(models.Frameproperties.parent_id!=None).all()
    frame_props_list = []

    # For each frame_prop create dict with parent and original path (the parser need only this 2 things)
    for frame_prop in frame_props:
        if frame_prop.parent_id != None:
            currDict = {
                "parent" : str(frame_prop.parent_id),
                "original":
                {
                    "path" : str(frame_prop.prop) + "/" + str(frame_prop.value)
                }
            }
            frame_props_list.append(currDict)
    return json.dumps(frame_props_list)

def getMangersUserId(pid):
    """Get managers id's in the project
        params:
            pid: the project id
    :return: users id's of all mangers in the project
    """
    group_manager_id = models.Group.query.filter_by(name='manager').first().id
    project = models.Projects.query.filter_by(id=pid).first()
    project_users = models.Projects_users.query.filter_by(project=project)
    users = project_users.join(models.User, models.User.id == models.Projects_users.user_id)
    managers = users.join(models.User_groups, models.User.id == models.User_groups.user_id).filter_by(group_id=group_manager_id).all()
    managers = [manager.user_id for manager in managers]
    print(managers)
    
    return managers

def validateAllParams(data):
    video_types = ['mp4', 'avi', 'mov', 'png', 'jpeg', 'jpg']
    video_type = data['data'].split('.')[-1]


    if data['labels'] == '':
        return 'labels is empty, labels'

    if os.environ.get('WITH_OS') == 'True' and data['os_id'] == None:
        return 'no such object storage, path'

    if video_type not in video_types:
        return 'cvat don\'t support this format video, data'
    
    if data['overlap_size'] < 0:
        return 'overlap_size have to be positive, overlap_size'
    
    if data['compress_quality'] < 0 or data['compress_quality'] > 95:
        return 'compress_quality '

    if data['storage'] != 'share' and data['storage'] != 'sorted' and data['storage'] != 'local':
        return 'storage'
        
    return ''

def createTaskRequest(request, current_user):
    """Create Task
        params:
            request: contains the data json and args
            current_user: the user that create the task  
    :return: response from cvat
    """
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        data = request.form.to_dict()
        if not data:
            data = request.get_json()
        files = request.files.getlist('data')
        logger.info(files)
        all_files = set()
        if files:
            for curr_file in files:
                all_files.add(('data', (curr_file.filename, curr_file.read())))

        missingParam = rqApi.checkIfDataExist(data, ['data'])
        if missingParam != "":
            return jsonify({'message' :  missingParam + ' is missing!'}), 401

        missingParam = rqApi.checkIfParamsExist(request.args, ['project.name'])

        if missingParam != "":
            return jsonify({'message' :  missingParam + ' is missing!'}), 401

        projectName = request.args.get('project.name')
        data['owner'] = current_user.id
        data['project'] = models.Projects.query.filter_by(name=projectName).first().id

        if os.environ.get('WITH_OS') == 'True':
            data['os_id'] = getOsId(data['data'])

        managers = getMangersUserId(data['project'])

        if current_user.id not in managers and not current_user.is_superuser:
            return jsonify({'message' : 'Only managers can create task !'}), 403

        if not 'storage' in data:
            data['storage'] = 'share'

        if not 'task_name' in data:
            data['task_name'] = data['data'].split('/')[-1].split('.')[0]

        if not 'score' in data:
            data['score'] = 0

        if not 'flip_flag' in data:
            data['flip_flag'] = False

        if not 'z_order' in data:
            data['z_order'] = False

        if not 'bug_tracker_link' in data:
            data['bug_tracker_link'] = ""

        if not 'labels' in data:
            data['labels'] = getLabelString(data['project'])

        if not 'frame_properties' in data:
            data['frame_properties'] = getFrameProperties(data['project'])

        if not 'overlap_size' in data:
            data['overlap_size'] = 0

        if not 'compress_quality' in data:
            data['compress_quality'] = 95

        if not 'assignee' in data:
            data['assignee'] = managers[0]
        else:
            userName = data['assignee']
            assignee_user = models.User.query.filter_by(username=userName).first()

            if assignee_user != None:
                if not rqApi.checkifAuthorize(projectName, assignee_user.id):
                     return jsonify({'message' : 'assignee user not authorized !'})
                else:
                    data['assignee'] = assignee_user.id
            else:
                 return jsonify({'message' : 'assignee user not exists !'})

        param = validateAllParams(data)

        if param != '':
            return jsonify({'message' : param + ' don\'t pass validation !'}), 404

        url = os.environ.get('CVAT_SERVER') + "/create/task"
        
        logger.info('Task create with params : {}'.format(data))

        data['CVAT_API_TOKEN'] = os.environ.get('CVAT_API_TOKEN')

        if data['storage'] != 'local':
            response = requests.post(url, data=data, verify=False)
        else:
            response = requests.post(url, data=data, files=all_files, verify=False)
        return response.text, response.status_code

    except  Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({'message' : 'can\'t create task'}), 401

def putUpdateVideosScore(data, args):
    """Update all videos with the new score 
    :return: if the update is success
    """

    missingParam = rqApi.checkIfParamsExist(args, ['project.name'])

    if missingParam != "":
        return jsonify({'message' :  missingParam + ' is missing!'}), 500
    try :
        countUpdatedVideos = 0
        for video in data:
            if 'video_id' in video and 'score' in video:
                video_id = video['video_id']
                new_score = video['score']
                tasks = models.Task.query
                project = models.Projects.query.filter_by(name=args['project.name']).first()
                tasks = tasks.filter_by(video_id=video_id, project=project)
                if bool(tasks.first()):
                    tasks.update({models.Task.score: new_score})
                    countUpdatedVideos += 1
                    app.db.session.commit()

        return jsonify({'message' : 'updated successfully ' + str(countUpdatedVideos) + ' videos'}), 200
    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({'message' : 'can\'t update scores'}), 500

