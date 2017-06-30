FROM python:2-onbuild

ENTRYPOINT [ "python", "./queue2blob.py" ]
