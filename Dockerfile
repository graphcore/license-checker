FROM ubuntu:20.04 AS base

WORKDIR /usr/src/app
ARG DEBIAN_FRONTEND=noninteractive
ENV TZ=Europe/London
RUN apt-get update && apt-get install -y python3-pip python3-apt python3.8-venv git libopenmpi-dev
RUN mkdir /root/.ssh
RUN echo "StrictHostKeyChecking=no" >> /root/.ssh/config

RUN pip install --upgrade pip

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .


FROM base AS run
COPY --from=base /usr/src/app ./
ENTRYPOINT [ "./entrypoint.sh" ]

# Testing stage
FROM base AS test
COPY --from=base /usr/src/app ./

RUN pip install --no-cache-dir -r requirements-dev.txt
CMD [ "python3", "-m", "pytest", "./tests"]
