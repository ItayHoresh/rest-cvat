import boto3
import os

s3_res = boto3.resource('s3', 
    endpoint_url= os.environ.get('AWS_S3_HOST'),
    config=boto3.session.Config(signature_version='s3v4'),
    aws_access_key_id= os.environ.get('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key= os.environ.get('AWS_SECRET_ACCESS_KEY'),
    verify=False)						 
s3_cli = s3_res.meta.client

def _get_frame_path(frame, base_dir):
    d1 = str(frame // 10000)
    d2 = str(frame // 100)
    path = os.path.join(d1, d2, str(frame) + '_w.png')
    if base_dir:
        path = os.path.join(base_dir, path)

    return path

def getFileUrl(path):
    # Check if bucket exists
    response = s3_cli.list_buckets()
    buckets = [bucket['Name'] for bucket in response['Buckets']]

    if buckets and os.environ.get('CVAT_BUCKET') in buckets:
        url = s3_cli.generate_presigned_url(ClientMethod='get_object',
            Params={'Bucket':os.environ.get('CVAT_BUCKET'), 'Key':path},
            ExpiresIn=15)
        return url
    return ''
