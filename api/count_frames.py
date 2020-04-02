import models
from flask import jsonify
import requestsApi as rqApi
import traceback

def getCountFinishFramesRequest(data):
    """Get the count of finish frames in specific project\n
        params:
            data: json contains task and project name
        return: number of frames (string)
    """
        
    missingParam = rqApi.checkIfParamsExist(data, ['project.name'])

    if missingParam != "":
        return jsonify({'message' :  missingParam + ' is missing!'}), 401

    tasks = rqApi.getRequest(data, models.Task)
    try :
        tasks = rqApi.parseBytesToJson(tasks.get_data())
        totalFrames = 0
        for task in tasks:
            totalFrames+=task['size']
        return str(totalFrames), 200
    except:
        traceback.print_exc()
        return jsonify({'message' : 'There is no count of frames to show !'})