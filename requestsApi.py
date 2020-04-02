from models import *
from sqlalchemy import text
from flask import jsonify, send_file, make_response
from itertools import tee
from s3cvat import _get_frame_path

def pairwise(iterable):
    a, b = tee(iterable)
    next(b, None)
    return zip(a ,b)

def getRequest(filters, model):
    """Return any model and filters.\n
    Example : getRequest({"project.name" : "ProjectName"}, Model)"""

    result = model.query
    for key in filters:
        values = filters[key].split(',')
        if len(values) != 0 :
            if '.' not in key:
                result = result.filter(getattr(model, key).in_(values))
            else:
                key_splited = key.split('.')
                currModel = model
                for attr1, attr2 in pairwise(key_splited):  
                    relation = getattr(currModel, attr1)
                    relation_model = relation.mapper.class_
                    field = getattr(relation_model, attr2)
                    result = result.join(relation_model, relation)
                    currModel = relation_model
                result = result.filter(field.in_(values))
    results = [i.serialized for i in result.all()]
    return jsonify(results)

def get_frame_path(sname, pname):
    """Read corresponding frame for the task"""
    
    task_sources = Tasksource.query
    task_sources = task_sources.filter_by(source_name=sname)
    task_sources = task_sources.all()

    # for each task_sorce check if the task is in the project requested
    for task_source in task_sources:
        result = Task.query
        result = result.filter_by(id=task_source.task.id)
        relation = getattr(Task, 'project')
        relation_model = relation.mapper.class_
        field = getattr(relation_model, 'name')
        result = result.join(relation_model, relation)
        result = result.filter(field.in_([pname]))
        db_task = result.first()
        frame = task_source.frame

        # if db_task is exist in the project
        if db_task:
            break

    path = _get_frame_path(frame, db_task.get_data_dirname())

    return path

def checkifAuthorize(pname, uid):
    project_exist = getRequest({'name' : pname}, Projects)

    project_exist = parseBytesToJson(project_exist.get_data())

    result = getRequest({'project.name' : pname, 'user.id': str(uid)}, Projects_users)

    project_splited = pname.split(',')

    result = parseBytesToJson(result.get_data())
    
    return (len(result) == len(project_splited) or bool(User.query.filter_by(id=uid, is_superuser=True).first())) and len(project_exist) != 0

def parseBytesToJson(data):
    """Return the json object from bytes object"""
    jsonData=data.decode('utf8').replace("'", '"')
    return json.loads(jsonData)

def getJobId(taskId):
    """Get the job id of a task
    :param taskId: id of a task
    :return: string of the job id
    """
    segment = parseBytesToJson(getRequest({'task.id': str(taskId)}, Segment).get_data())[0]
    job = parseBytesToJson(getRequest({'segment.id': str(segment['id'])}, Job).get_data())[0]

    return str(job['id'])

def checkIfParamsExist(data, params):
    """Check if all params exist in json data
    :param data: json of data
    :return: string of the parameter"""
    for param in params:
        if param not in data:
            return param
    return ""

def checkIfDataExist(data, params):
    """Check if all params exist in json data
    :param data: json of data
    :return: string of the parameter"""
    for param in params:
        if param not in data:
            return param
    return ""
    
def getJsonByParams(data, params):
    """Get result of data and parameter to show
    :param data: json of data
    :return: new json data with the requested parametrs"""
    newData = {}
    for param in params:
        splited_param = param.split('.')
        value = data[splited_param[0]]
        for currParam in splited_param[1:]:
            value = value[currParam]
        newData[param] = value
    return newData