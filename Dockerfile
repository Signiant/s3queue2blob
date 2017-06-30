FROM python:2-onbuild
ENV CONFIG_FILE /usr/src/app/config.json
ENTRYPOINT [ "python", "./queue2blob.py" ]
