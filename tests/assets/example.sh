#!/bin/bash

function do_thing() {
    echo $1
    touch "${1}.txt"
    echo "some text: ${2}" > "${1}.txt"
}

do_thing \
    "the first argument" \
    "another argument"

# A comment
# Another comment
# And one more comment, this time with /home/username/requirements.txt in it
# And this one says I'm using apt-get install to install some package

pip install numpy pandas==1.5.3
pip install -q -r requirements.txt
sudo apt-get update && apt-get install vim

echo "Done
multline
string"

echo "this is \" a line including an escaped quote"

cat << EOF >> /path/to/file
Your Name is ${yourname}

EOF

cat << EOF >> /path/to/file
Your "Name" is ${yourname}

EOF
apt install emacs
