import models
from flask import jsonify, send_file, make_response
import requestsApi as rqApi
from functools import reduce
import traceback
import logging

logger = logging.getLogger('waitress')

def getTagsFromDB(data):
    """Get all tags of a tasks
    :param data: json contains the source of the tasks(video/image name) and project name
    :return: Json with all tags
    """

    missingParam = rqApi.checkIfParamsExist(data, ['project.name', 'source'])

    if missingParam != "":
        return jsonify({'message' :  missingParam + ' is missing!'}), 401
    
    try :
        projectName = data['project.name']
        sources = data['source'].split(',')
        annotations = []

        for source in sources:
            taskAnnotations = getTaskAnnotations(projectName, source)
            
            if taskAnnotations == -1:
                return jsonify({'message' :  source + ' is not exists!'}), 400

            annotations.append(taskAnnotations)

        return jsonify(annotations), 200
    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({'tags' : 'There is no tags'})

def getTaskAnnotations(projectName, source):
    """Get all tags of a task
    :param projectName: project name of the task
    :param source: source of the task
    :return: Json with all annotations of this task
    """
    task = rqApi.parseBytesToJson(rqApi.getRequest({'project.name' : projectName, 'source' : source}, models.Task).get_data())

    if len(task) == 0:
        # Checking if the source is task name for images task
        task = rqApi.parseBytesToJson(rqApi.getRequest({'project.name' : projectName, 'name' : source}, models.Task).get_data())
        if len(task) == 0:
            return -1

    jobId = rqApi.getJobId(task[0]['id'])

    labeledBox = getLabeledBox(jobId)
    trackedBox = getTrackedBox(jobId, int(task[0]['size']))
    labeledPolygon = getLabeledPolygon(jobId)
    frameProperties = getFrameProperties(task[0]['id'], int(task[0]['size']))

    taskAnnotations = {
        'project.name': projectName,
        'source' : task[0]['source'],
        'annotations' : trackedBox + labeledBox + labeledPolygon,
        'frameProperties' : frameProperties,
        'name': task[0]['name']
    }

    return taskAnnotations

def initializeProperties(model, key, value):
    """Get all properties of a tag
    :param model: model that represents the table with properties
    :param key: key to search by
    :param value: value to search by key
    :return: dictionary contains the properties
    """
    attrs = {}

    try:
        vals = rqApi.parseBytesToJson(rqApi.getRequest({key: value}, model).get_data())

        for val in vals:
            startIndex = val['spec']['text'].index('=') + 1

            try:
                endIndex = val['spec']['text'].index(':')
            except:
                endIndex = len(val['spec']['text'])
            attrs[val['spec']['text'][startIndex : endIndex]] = val['value']

    except Exception as e:
        logger.error(e, exc_info=True)

    return attrs

# Labeledbox

def getLabeledBox(jobId):
    """Get all labeledbox tags of a job
    :param jobId: the id of the job
    :return: array with all labeledbox tags
    """
    labels = rqApi.parseBytesToJson(rqApi.getRequest({'job.id': jobId}, models.Labeledbox).get_data())
    labels = list(map(lambda label : {"box": {
                                    "xbr": float(label['xbr']),
                                    "xtl": float(label['xtl']),
                                    "ybr": float(label['ybr']),
                                    "ytl": float(label['ytl'])
                                    },
                                    "properties" : initializeProperties(models.Labeledboxattributeval, 'box_id', str(label['id'])),
                        "frame" : int(label['frame']),
                        "class" : label['label']['name']}, labels))

    return labels

# Trackedbox

def getTrackedBox(jobId, size):
    """Get all interpolation tags of a job
    :param jobId: the id of the job
    :param size: the size of the job
    :return: array with all tags
    """
    # Get all track id's of this job
    objectsPath = rqApi.parseBytesToJson(rqApi.getRequest({'job.id': jobId}, models.Objectpath).get_data())

    if len(objectsPath) != 0:
        objectsPath = list(map(lambda x : str(x['id']), objectsPath))
        objectsPath = ','.join(objectsPath)

        # Get all tracks for this job
        tracks = rqApi.parseBytesToJson(rqApi.getRequest({'track.id': str(objectsPath)}, models.Trackedbox).get_data())
        tracks = list(map(lambda track : {"box":{
                                                "xbr": float(track['xbr']),
                                                "xtl": float(track['xtl']),
                                                "ybr": float(track['ybr']),
                                                "ytl": float(track['ytl'])
                                                },
                                                "properties" : initializeProperties(models.Trackedboxattributeval, 'box_id', str(track['id'])),
                                            "frame" : int(track['frame']),
                                            "class" : track['track']['label']['name'],
                                            "track_id": int(track['track']['id']),
                                            "outside": track['outside']}, tracks))

        tracks_dict = {}

        for track in tracks:
            trackId = track['track_id']
            if trackId not in tracks_dict:
                tracks_dict[trackId] = []
            
            tracks_dict[trackId].append(track)

        completeTracks = []

        for trackId in tracks_dict:
            currentTrack = tracks_dict[trackId]
            currentTrack.sort(key=lambda x : x['frame'])
            currentTrack = completeFrame(currentTrack, size)
            completeTracks.extend(currentTrack)

        return completeTracks
    else:
        return []

def initializeAttrsAndValsForTrackedBox(prevAttrs, currentAttrs):
    """Initialize attributes and their values for tracked box
    :param prevAttrs: attributes of the previous frame
    :param currentAttrs: attributes of the current frame
    :return: dictionary with all attributes
    """

    # Cloning attributes
    attrs = {}
    
    for attr in prevAttrs:
        attrs[attr] = prevAttrs[attr]

    for attr in currentAttrs:
        attrs[attr] = currentAttrs[attr]

    return attrs

def completeFrame(track, size):
    """Complete all frames between key frames
    :param track: all the key frame of a track
    :param size: the size of the job
    :return: array with all completed frames
    """
    tracks = []

    for i in range(len(track) - 1):
        # Updating attributes for each tracked box
        if i > 0:
            track[i]['properties'] = initializeAttrsAndValsForTrackedBox(track[i - 1]['properties'], track[i]['properties'])
        if not track[i]['outside']:
            del track[i]['outside']
            tracks.append(track[i])
            margin = track[i+1]['frame'] - track[i]['frame']
            if margin > 1:
                averageTracks = averagePosition(track[i], track[i + 1], margin)
                tracks.extend(averageTracks)
    
    lastTrackIndex = len(track) - 1

    if not track[lastTrackIndex]['outside']:
        del track[lastTrackIndex]['outside']
        tracks.append(track[lastTrackIndex])

        # Adding all interpolated boxes until the end of the video
        if track[lastTrackIndex]['frame'] < size:
            for frame in range(track[lastTrackIndex]['frame'] + 1, size):
                newTrack = {
                    "frame" : frame,
                    "class" : track[lastTrackIndex]['class'],
                    "track_id" : track[lastTrackIndex]['track_id'],
                    "properties" : track[lastTrackIndex]['properties'],
                    "box": {
                        "xbr" : track[lastTrackIndex]['box']['xbr'],
                        "xtl" : track[lastTrackIndex]['box']['xtl'],
                        "ybr" : track[lastTrackIndex]['box']['ybr'],
                        "ytl" : track[lastTrackIndex]['box']['ytl']
                    }
                }
                tracks.append(newTrack)

    return tracks

def averagePosition(startFrame, stopFrame, margin):
    """Complete all frames between key frames by calculating their average position
    :param startFrame: start key frame
    :param stopFrame: end key frame
    :param margin: frames to complete
    :return: array with all completed frames
    """
    tracks = []
    xbrDis = (stopFrame['box']['xbr'] - startFrame['box']['xbr']) / margin
    xtlDis = (stopFrame['box']['xtl'] - startFrame['box']['xtl']) / margin
    ybrDis = (stopFrame['box']['ybr'] - startFrame['box']['ybr']) / margin
    ytlDis = (stopFrame['box']['ytl'] - startFrame['box']['ytl']) / margin

    for i in range(margin - 1):
        track = {
            "frame" : startFrame["frame"] + i + 1,
            "class" : startFrame["class"],
            "track_id" : startFrame['track_id'],
            "box": {
                "xbr" : xbrDis * (i+1) + startFrame['box']['xbr'],
                "xtl" : xtlDis * (i+1) + startFrame['box']['xtl'],
                "ybr" : ybrDis * (i+1) + startFrame['box']['ybr'],
                "ytl" : ytlDis * (i+1) + startFrame['box']['ytl']
            }
        }
        tracks.append(track)

    return tracks

# Labeledpolygon

def getLabeledPolygon(jobId):
    """Get all labeled polygon tags of a job
    :param jobId: the id of the job
    :return: array with all labeled polygon tags
    """
    labels = rqApi.parseBytesToJson(rqApi.getRequest({'job.id': jobId}, models.Labeledpolygon).get_data())
    labels = list(map(lambda label : {"geometry": {
                                        "type": "Polygon",
                                        "coordinates" : parsePointToGeoJsonPolygon(label['points'])
                                    },
                                    "properties" : initializeProperties(models.Labeledpolygonattributeval, 'polygon_id', str(label['id'])),
                        "frame" : int(label['frame']),
                        "class" : label['label']['name']}, labels))

    return labels

def parsePointToGeoJsonPolygon(points):
    points = points.split(' ')

    coordinates = []

    for point in points:
        coordinates.append(list(map(lambda p: float(p), point.split(','))))
    
    return [coordinates]

def getFrameProperties(taskId, taskSize):
    def getFrame(e):
        return e['frame']
    
    keyFrames = keyFramesProperties(taskId)
    frameProperties = []

    for key in keyFrames:
        keyFrames[key].sort(key=getFrame)

        for i in range(0, len(keyFrames[key])):
            if i == len(keyFrames[key])) - 1:
                frameProperties.extend(completeProps(keyFrames[key][i], taskSize)
            else:
                frameProperties.extend(completeProps(keyFrames[key][i], keyFrames[key][i + 1]['frame']))

    return frameProperties
    

def keyFramesProperties(taskId):
    frameProperties = rqApi.parseBytesToJson(rqApi.getRequest({'task.id': str(taskId)}, models.Taskframespec).get_data())
    keyFrames = {}
    for prop in frameProperties:
        props = rqApi.parseBytesToJson(rqApi.getRequest({'frameSpec_id': str(prop['id'])}, models.Keyframespec).get_data())

        for i in range(0, len(props)):
            keyFrameSpec = {
                "frame": props[i]['frame'],
                props[i]['frameSpec']['propVal']['prop']: props[i]['frameSpec']['propVal']['value'],
                "prop" : props[i]['frameSpec']['propVal']['prop']
            }

            if props[i]['frameSpec']['propVal']['prop'] not in keyFrames.keys():
                keyFrames[props[i]['frameSpec']['propVal']['prop']] = []

            keyFrames[props[i]['frameSpec']['propVal']['prop']].append(keyFrameSpec)

    return keyFrames

def completeProps(keyFrame, stopFrame):
    props = []

    for i in range(keyFrame['frame'], stopFrame):
        copy = keyFrame.copy()
        del copy['prop']
        copy['frame'] = i
        props.append(copy)

    return props