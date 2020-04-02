import models
from flask import jsonify, send_file, make_response
import requestsApi as rqApi
import requests
from io import BytesIO
import zipfile
from s3cvat import getFileUrl, _get_frame_path
import traceback
import urllib3
import re
import logging

logger = logging.getLogger('waitress')

def getWatershedImageRequest(data):
    
    """Get the watershed image from s3\n
        params:\n
            data: json contains project and task names and (optionally) source names
        return: Watershed image
    """

    missingParam = rqApi.checkIfParamsExist(data, ['project.name', 'task.name'])

    if missingParam != "":
        return jsonify({'message' :  missingParam + ' is missing!'}), 401

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        project = models.Projects.query.filter_by(name = data['project.name']).first()
        task = models.Task.query.filter_by(project_id = project.id, name = data['task.name']).first()
        task_sources = models.Tasksource.query.filter_by(task_id = task.id)
        
        if data.get('source'):
            task_sources = task_sources.filter(models.Tasksource.source_name.in_(data['source'].split(',')))
        
        task_sources = task_sources.all()
        task_data_dir = task.get_data_dirname()

        images = BytesIO()
        with zipfile.ZipFile(images, mode='w') as imagesZipFile:
            for task_source in task_sources:
                frameUrl = getFileUrl(_get_frame_path(task_source.frame, task_data_dir))
                image_content = requests.get(frameUrl, verify=False)

                if image_content.status_code != 404:
                    image_content = image_content.content
                    insensitive_source = re.compile(re.escape('.jpg'), re.IGNORECASE)
                    source = insensitive_source.sub('_w.png', task_source.source_name)
                    imagesZipFile.writestr(source, image_content)
            
        images.seek(0)

        return send_file(images, mimetype="application/zip", attachment_filename=str(len(task_sources)) + "_images_" + project.name +".zip", as_attachment=True)
    except Exception as e:
        logger.error(e, exc_info=True)
        return jsonify({'message' : 'Cannot get images!'})

