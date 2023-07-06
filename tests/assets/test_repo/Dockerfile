FROM graphcore/pytorch:3.0.0

ENV DEBIAN_FRONTEND noninteractive

# Install linux packages
RUN apt-get update && apt-get install -y htop screen vim

COPY docker-requirements.txt inside_docker_requirements.txt

RUN pip install -qr inside_docker_requirements.txt

CMD python myfile.py
