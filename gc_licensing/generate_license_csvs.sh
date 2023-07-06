#!/usr/bin/env bash
# Copyright (c) 2023 Graphcore Ltd. All rights reserved.

SCRIPT_PATH=$(realpath $0)
SCRIPT_ROOT=$(dirname $SCRIPT_PATH)

APP_NAME=$1
APP_ROOT_DIRECTORY=$2
REQUIREMENTS_RELATIVE_PATH=$3

function usage() {
    echo ""
    echo "  Usage: bash <APP_NAME> <APP_ROOT_DIRECTORY> <REQUIREMENTS_RELATIVE_PATH>";
    echo "      <APP_NAME>:                   The name of the application, used to name the output CSVs"
    echo "      <APP_ROOT_DIRECTORY>:         Absolute path to the application root, which should"
    echo "                                    contain requirements and optionally, a Dockerfile."
    echo "      <REQUIREMENTS_RELATIVE_PATH>: Path of requirements file to process, relative to the"
    echo "                                    app root directory specified above"
    echo ""
    echo "  This script must be run in a fresh shell, do not source it."
    echo ""
}

function error_msg() {
    echo ""
    echo "ERROR: $1"
    echo ""
}

# Prevent sourcing
if [ "$0" != "$BASH_SOURCE" ] ; then
    error_msg "Do not source this script."
    usage
    return 0  2>/dev/null || :
fi

if [[ "${APP_ROOT_DIRECTORY:0:1}" != "/" ]]; then
    error_msg "<APP_ROOT_DIRECTORY> must be an absolute path."
    usage
    exit 1
fi;

APP_REQUIREMENTS=${APP_ROOT_DIRECTORY}/${REQUIREMENTS_RELATIVE_PATH}
if [ ! -f $APP_REQUIREMENTS ]; then
    error_msg "Could not find requirements.txt at path '${APP_REQUIREMENTS}'"
    exit 2
fi;

WORK_DIR=`mktemp -d -p "/tmp"`
VENV_PATH=$WORK_DIR/temp_venv
echo "VENV PATH: "$VENV_PATH

python3 -m venv $VENV_PATH
source $VENV_PATH/bin/activate

pip install --upgrade pip
pip install --upgrade pip-licenses wheel

pip-licenses -f csv --output-file ${APP_ROOT_DIRECTORY}/${APP_NAME}-before.csv

pip install -r $APP_REQUIREMENTS

pip-licenses -f csv --output-file ${APP_ROOT_DIRECTORY}/${APP_NAME}-after.csv

# pip install pipdeptree
# pipdeptree > ${SCRIPT_ROOT}/../${APP_NAME}-tree.txt

rm -rf $WORK_DIR
