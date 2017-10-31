import argparse
import os
import sys
import boto3
import json
import time
import logging
import gc
from azure.storage.blob import BlockBlobService

WAIT_TIME = 60
blob_service = ""
debug = False

# setup logging
FORMAT = '%(asctime)-15s [%(levelname)s] %(message)s'
logging.basicConfig(format=FORMAT, stream=sys.stdout, level=logging.INFO)
logging.getLogger("botocore").setLevel(logging.CRITICAL)
logging.getLogger("boto3").setLevel(logging.CRITICAL)
logger = logging.getLogger(__name__)


def parse_config_file(config_file):
    global logger
    if not os.path.exists(config_file):
        s3_client = boto3.client('s3')
        local_path = "/tmp/config.json"
        s3bucket, s3config = config_file.split('/')
        s3_client.download_file(s3bucket, s3config, local_path)
        logger.info('Loaded configuration from S3')
        profile = "None"
    else:
        local_path = config_file
        print ("LOCAL PATH: " + local_path)
        profile = "dev2"
        logger.info('Loaded configuration from local file system')
    with open(local_path) as stream:
        config = {}
        try:
            config = json.load(stream)
        except ValueError, e:
            print(e)
            sys.exit(1)

        if os.environ.get('STORAGE_KEY'):
            key = os.environ.get('STORAGE_KEY')
        else:
            key = config['STORAGE_KEY']
        queue = config['QUEUE']
        region = config['REGION']
        s3_region = config['S3REGION']
        storage_account = config['STORAGE_ACCOUNT']
        container = config['CONTAINER']
        logger.debug('Values : %s,%s,%s,%s,%s', queue, region, storage_account, container, key)
        return queue, region, s3_region, profile, storage_account, container, key


def init_blob_service(storage_account, region, profile, key):
    global blob_service
    global logger
    try:
        blob_service = BlockBlobService(account_name=storage_account, account_key=key)
    except Exception as e:
        logger.error("ERROR: Could connect to Azure Storage: %s", str(e))
        return False
    return True


def upload_to_azure(source_files, container_name):
    global blob_service
    global logger
    for fileobject in source_files:
        logger.info('Uploading Fileobject: %s Sourceurl: %s', fileobject, source_files[fileobject])
        try:
            copy = blob_service.copy_blob(container_name, fileobject, source_files[fileobject])
        except Exception as e:
            # does not exist
            logger.error('Could not upload to container: %s', str(e))
            return False
        count = 0
        copy = blob_service.get_blob_properties(container_name, fileobject).properties.copy
        while copy.status != 'success':
            count = count + 1
            if count > 50:
                print('ERROR: Timed out waiting for async copy to complete.')
                return False
            logger.info('Copying to blob storage: %s', fileobject)
            time.sleep(5)
            copy = blob_service.get_blob_properties(container_name, fileobject).properties.copy
        logger.info('Upload complete: %s', fileobject)
        return True


def poll_queue(queue_name, region, s3_region, profile, container):
    global debug
    global logger
    try:
        if profile != "None":
            session = boto3.session.Session(profile_name=profile, region_name=region)
        else:
            session = boto3.session.Session(region_name=region)
        sqs = session.resource('sqs')
    except Exception as e:
        logger.error("Could not connect to AWS: %s", str(e))
        return False

    try:
        queue = sqs.get_queue_by_name(QueueName=queue_name)
    except Exception as e:
        logger.error("Could not load queue %s: %s", queue_name, str(e))
        return False
    # Process messages
    max_queue_messages = 10
    success = True
    while True:
        messages_to_delete = []
        for message in queue.receive_messages(MaxNumberOfMessages=max_queue_messages):
            # process message body
            try:
                body = json.loads(message.body)
            except Exception as e:
                logger.error("Could not load messaged body: %s", str(e))
                return False
            to_upload = {}
            if len(body) > 0:
                logger.debug('Message found')
                try:
                    logger.debug('Region: %s Bucket: %s File: %s ', body['Records'][0]['awsRegion'], body['Records'][0]['s3']['bucket']['name'], body['Records'][0]['s3']['object']['key'])
                    file_object = body['Records'][0]['s3']['object']['key']
                except KeyError, e:
                    logger.info('Found non s3 upload message, removing')
                    messages_to_delete.append({
                        'Id': message.message_id,
                        'ReceiptHandle': message.receipt_handle
                    })
                except IndexError, e:
                    logger.error('ERROR: IndexError received: %s', str(e))
                    return False
                else:
                    message_url = "https://" + s3_region + "/" + body['Records'][0]['s3']['bucket']['name'] + "/" + file_object
                    to_upload.update({file_object: message_url})
                    upload_result = upload_to_azure(to_upload, container)
                    # add message to delete
                    if upload_result:
                        messages_to_delete.append({
                            'Id': message.message_id,
                            'ReceiptHandle': message.receipt_handle
                        })
                    else:
                        # exception occured on upload
                        success = False
        if len(messages_to_delete) == 0:
            break
        # delete messages to remove them from SQS queue
        # handle any errors
        else:
            try:
                queue.delete_messages(Entries=messages_to_delete)
            except Exception as e:
                logger.error("Could not delete messages from queue: %s", str(e))
                return False
    return success


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='queue2blob.py')

    parser.add_argument("--config-file", help="config file containing required config", dest="config_file")
    parser.add_argument("--queue", help="Queue name", dest="queue_name")
    parser.add_argument("--region", help="AWS Region that the Queue is in", dest="region")
    parser.add_argument("--s3region", help="The region prefix for s3 downloads", dest="s3_region")
    parser.add_argument("--profile", help="The name of an aws cli profile to use.", dest='profile', required=False)
    parser.add_argument("--storage", help="The name of storage account to use.", dest='storage_account', required=False)
    parser.add_argument("--key", help="The key for the storage account", dest='storage_key', required=False)
    parser.add_argument("--container", help="The container for the blob.", dest='container', required=False)
    parser.add_argument("--debug", help="Set debug flag", action='store_true', dest='debug', required=False)
    args = parser.parse_args()

    if args.debug:
        logger.setLevel(logging.DEBUG)
    if args.config_file:
        queue_name, region, s3_region, profile, storage_account, container, key  = parse_config_file(args.config_file)
    elif os.environ.get('CONFIG_FILE') != None:
        queue_name, region, s3_region, profile, storage_account, container, key  = parse_config_file(os.environ.get('CONFIG_FILE'))
    else:
        queue_name = args.queue_name
        region = args.region
        profile = args.profile
        storage_account = args.storage_account
        s3_region = args.s3_region
        container = args.container
    if args.storage_key:
        key = args.storage_key

    if not init_blob_service(storage_account, region, profile, key):
        sys.exit(1)
    while True:
        logger.info('Starting run')
        result = poll_queue(queue_name, region, s3_region, profile, container)
        if result:
            logger.info('Completed run')
        else:
            logger.info('No messages processed , completed run')
        del result
        gc.collect()
        time.sleep(WAIT_TIME)
