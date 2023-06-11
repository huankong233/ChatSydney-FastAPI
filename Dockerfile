FROM python:3.11

WORKDIR ./ChatSydney

ADD . .

RUN pip install -r requirements.txt --upgrade

CMD ["python", "./main.py"]
