FROM public.ecr.aws/amazonlinux/amazonlinux:2
EXPOSE 8080

RUN yum clean all \
    && yum update -y

RUN yum install vim ip-utils bind-utils net-tools traceroute awscli iperf3 -y

RUN yum install python3-pip python3-gevent git -y

RUN pip3 install pip --upgrade

RUN pip3 install Flask gunicorn gevent supervisor -U

RUN pip3 install iperf3 boto3

COPY exec_cmd.py /app/
COPY gunicorn_conf.py /app/
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY serve /

RUN chmod 777 /serve

ENTRYPOINT ["/serve"]
