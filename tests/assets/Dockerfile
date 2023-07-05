FROM graphcore/pytorch:3.0.0

ENV DEBIAN_FRONTEND noninteractive

# Install linux packages
RUN apt-get update && apt-get install -y zip htop screen python3.6-tk wget
RUN apt-get -y install git

# Install python dependencies
COPY requirements.txt .
RUN python -m pip install --upgrade pip
RUN python -m pip install --upgrade setuptools wheel
RUN pip install --no-cache -r requirements.txt
# RUN pip install --no-cache -U torch torchvision
RUN pip install --no-cache -U numpy

# Create working directory
RUN mkdir -p /usr/src/app

COPY ./notebook/nbk-requirements.txt a_new_requirements_file.txt
RUN pip install -r a_new_requirements_file.txt

# Copy contents
COPY . /usr/src/app
WORKDIR /usr/src/app/custom_ops
RUN make clean && make

WORKDIR /usr/src/app/NMS/poptorch_ops/multiclass
RUN make clean && make
