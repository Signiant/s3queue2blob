# s3queue2blob

Polls an SQS queue for S3 Put/Post/Copy events on a publicly available bucket and replicates files listed in those events to Azure blob storage with an azure pull.

### Requirements
- You must have an s3 bucket that allows read to everyone.
- You must setup your bucket to send PUT, Post, Copy and Complete Multipart Upload events to an SQS Queue
- Your credentials profile must have access to poll the queue.
- Your queue should have a policy to allow the bucket to send messages to it.

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


### Sample config file format
```
{
  "QUEUE":"QUEUE",
  "REGION":"AWS REGION IF DEPLOYED IN AWS",
  "S3REGION":"S3 REGION",
  "STORAGE_ACCOUNT":"AZURE STORAGE ACCOUNT",
  "CONTAINER":"AZURE CONTAINER",
  "PROFILE":"AWS CREDENTIAL PROFILE"
}
```

Sample docker run command showing how to mount the config file into the container using a data volume on the local docker host :
```
docker run -d --privileged=true \
              -v /my/local/folder/config.json:/usr/src/app/config.json \
              --name s3queue2blob \
              signiant/s3queue2blob
```
