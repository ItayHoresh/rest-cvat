import models
from flask import jsonify, send_file, make_response
import requestsApi as rqApi
import traceback
import collections

def getStatusRequest(data):
    """Get the status of task\n
        params:
            data: json contains task and project name
        return: Status type (string)
    """
    missingParam = rqApi.checkIfParamsExist(data, ['project.name', 'source'])

    if missingParam != "":
        return jsonify({'message' :  missingParam + ' is missing!'}), 401

    tasks = rqApi.getRequest(data, models.Task)
    
    try :
        tasks = rqApi.parseBytesToJson(tasks.get_data())
        tasks = list(map(lambda task : {"project.name": task['project']['name'],
                                        "source": task['source'],
                                        "status": task['status']}, tasks))
        return jsonify(tasks)
    except:
        traceback.print_exc()
        return jsonify({'message' : 'There is no status to show !'})

def getTasksByStatusRequest(data):
    """Get the tasks according the status type\n
        params:
            data: json contains status types and project name
        return: all tasks
    """
    missingParam = rqApi.checkIfParamsExist(data, ['project.name'])

    if missingParam != "":
        return jsonify({'message' :  missingParam + ' is missing!'}), 401

    if 'status' in data:
        tasks = rqApi.getRequest({'project.name' : data['project.name'], 'status' : data['status']}, models.Task)
    else:
        tasks = rqApi.getRequest({'project.name' : data['project.name']}, models.Task)
    
    try :
        tasks = rqApi.parseBytesToJson(tasks.get_data())

        # Group all tasks by status parameter
        grouped_tasks = groupBy(tasks, 'status')

        # Display only requested parameters in task and change to dict instead of list
        tasks_by_status = { status  :   {   "tasks"         : list(map(lambda task : {  "project.name"  : task['project']['name'],
                                                                                        "source"        : task['source'],
                                                                                        "created_date"  : task['created_date'], 
                                                                                        "updated_date"  : task['updated_date']}, tasks)),
                                            "total_frames" : countFrames(tasks)
                                        } 
                                            
                                            for status, tasks in grouped_tasks.items()
                          }
                                        
        return jsonify(tasks_by_status)
    except:
        traceback.print_exc()
        return jsonify({'message' : 'There is no status to show !'})

def groupBy(array, param):
    grouped = collections.defaultdict(list)
    for element in array: 
        grouped[element[param]].append(element)

    return grouped

def countFrames(tasks):
    total=0
    for task in tasks:
        total+=task["size"]
    return total