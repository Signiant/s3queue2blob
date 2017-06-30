# s3queue2blob

Polls an SQS queue for S3 Put/Post/Copy events on a publicly available bucket and replicates files listed in those events to Azure blob storage with an azure pull.

### Requirements
- You must have an s3 bucket that allows read to everyone.
- You must setup your bucket to send PUT, Post, Copy and Complete Multipart Upload events to an SQS Queue
- Your credentials profile must have access to poll the queue.
- Your queue should have a policy to allow the bucket to send messages to it.
- Optional - upload configuration file to bucket either accessible by credentials or public

### Example SQS Permission:
```
{
  "Version": "2012-10-17",
  "Id": "addmessage",
  "Statement": [
    {
      "Sid": "sqsAllow",
      "Effect": "Allow",
      "Principal": {
        "AWS": "*"
      },
      "Action": "SQS:SendMessage",
      "Resource": "arn:aws:sqs:us-east-1:ACCOUNT_NUMBER:QUEUE_NAME",
      "Condition": {
        "ArnLike": {
          "aws:SourceArn": "arn:aws:s3:*:*:NAME_OF_BUCKET"
        }
      }
    }
  ]
}
```
Where ACCOUNT_NUMBER is you account ID, QUEUE_NAME is the name of your Queue, and NAME_OF_BUCKET is the bucket that is sending the s3 events.


### Run from python script
```
python queue2blob.py --config-file location/of/config.json
```

### Sample config file format
```
{
  "QUEUE":"QUEUE",
  "REGION":"AWS REGION IF DEPLOYED IN AWS",
  "S3REGION":"S3 REGION",
  "STORAGE_ACCOUNT":"AZURE STORAGE ACCOUNT",
  "STORAGE_KEY":"AZURE STORAGE KEY (OPTIONAL IF READ FROM ENVIRONMENT)",
  "CONTAINER":"AZURE CONTAINER",
  "PROFILE":"AWS CREDENTIAL PROFILE"
}
```

You can also specify parameters on the command line without a config file
```
--queue QUEUE_NAME    Queue name
--region REGION       AWS Region that the Queue is in
--s3region S3_REGION  The region prefix for s3 downloads
--profile PROFILE     The name of an aws cli profile to use.
--storage STORAGE_ACCOUNT
                      The name of storage account to use.
--key STORAGE_KEY     The key for the storage account
--container CONTAINER
                      The container for the blob.
--debug               Set debug flag
```

### Run from Docker

```
docker run -d --privileged=true \
              -v /my/local/folder/config.json:/usr/src/app/config.json \
              -e STORAGE_KEY=AZURE_STORAGE_KEY
              --name s3queue2blob \
              signiant/s3queue2blob
```
