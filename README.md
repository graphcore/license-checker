# README

This tool will help generate the license requirements for the application OSS form.

It generates an HTML file containing dependency tables that can be copied in verbatim. Licenses which need attention
are highlighted in **bold**.

Usage:

```bash
$ python3 -m gc_licensing --repository <repo_base_path> --output-path <output_file_path>
Running main...
Looking in indexes: https://ianh%40graphcore.ai:****@artifactory.sourcevertex.net:443/api/pypi/pypi-virtual/simple, https://pypi.python.org/simple/
Collecting pip
Using cached https://artifactory.sourcevertex.net:443/api/pypi/pypi-virtual/packages/package
...
```

Currently, assumes that there is a single `requirements.txt` resides in the base path of your application.

## Setup

To use the `apt` library, you need to create your venv with the `--system-site-packages` flag:

```bash
$ python3 -m venv --system-site-packages venv-gc-licensing
...
$ source venv-gc-licensing
$ python3 -m pip install -r requirements.txt
```

In order to write to Confluence, it is necessary to store API login details into a config file (which is not synced to VCS by default, and should not be).

Your username is the email address you use to log into the Atlassian suite.

1. First, generate an API Token on the [Confluence Cloud user page](https://id.atlassian.com/manage-profile/security/api-tokens)
2. Run `$ python3 -m gc_licensing --setup` and follow the on-screen instructions.

This will create a user config file inside the `gc_licensing` module.


## How it works

To get python dependencies, `pip-licensing` is used to scan the installed packages. However, to do this, we first
need to create a clean venv in `/tmp`, install `pip-licensing`, extract existing dependencies, then install
the pacakages from the source application.

To do this, there is a helper script `gc_licensing/generate_license_csvs.sh`, which will do the above, and delete
the temporary venv afterwards. It writes two CSV files to the root of this repo, one containing the packages/licenses
from before installing the source app, and one for after.

###  Ignoring packages on an app-by-app basis

The application will check for a file in the root of the repository: `.gclicense-ignore.yml`, and if found, will read packages from there
to add to the allow list (for either `apt` or `pip` packages). This is currently done by name only - a sensible future extension would be
to incorporate version checking here.

The structure of the `.gclicense-ignore.yml` file is a dictionary, where the key is either/both of [`apt`, `pip`], and the values are package names.

For example, if I want to add `htop` to the allowlist, I might have the following:

```yaml
apt:
    - htop
```

If I also wanted to add the `pip` package `pandas` to the allowlist, I might have:

```yaml
apt:
    - htop
pip:
    - pandas
```

Packages added to the allowlist in this way appear no differently to packages added to the global allowlist in the `config.yml`.

If a package appears in the global denylist and the ignorefile, the ignorefile takes precedence, and the package will be moved from the denylist
to the allowlist.

## Running from Docker

Build the image from the root of this repo. The Dockerfile is configured as a multi-stage build with two targets; `run` and `test` to run the script and run the tests respectively. They share much of the same base; however the `tests` image includes some extra packages and a different entrypoint.

```bash
$ docker build --target run -t gc_licensing .
$ docker build --target test -t gc_licensing_tests .
...
```

Then run it, mounting the repository you'd like to search, and the folder into which you'd like to save the output (which should exist already):

```bash
$ docker run \
    -v /localdata/myusername/repos/yolov5:/usr/src/source_repo \
    -v $(pwd)/docker-output:/usr/src/output \
    -it gc_licensing
...
```

### Additional Arguments

The default entrypoint runs the application and searches for `requirements.txt` and `Dockerfiles`. You can provide additional arguments on the command line as you would if running natively:

```bash
$ docker run \
    -v /localdata/myusername/repos/yolov5:/usr/src/source_repo \
    -v $(pwd)/docker-output:/usr/src/output \
    -it gc_licensing \
    --extra-arguments
...
```

### Choosing sources of dependencies

The default entrypoint runs the application and searches for `requirements.txt` and `Dockerfiles`. You can select specific requirements files using the `--pip-requirements-files` argument:

```bash
$ docker run \
    -v /localdata/myusername/repos/yolov5:/usr/src/source_repo \
    -v $(pwd)/docker-output:/usr/src/output \
    -it gc_licensing \
    --pip-requirements-files requirements.txt requirements-dev.txt
...
```

alternatively, to use a recursive search for those file names do:

```bash
$ docker run \
    -v /localdata/myusername/repos/yolov5:/usr/src/source_repo \
    -v $(pwd)/docker-output:/usr/src/output \
    -it gc_licensing \
    --find-pip-files  --find-pip-files-names requirements.txt requirements-dev.txt
...
```

Equivalent arguments exist for customising the behaviour for apt, docker and notebook files.

### SSH Agent Forwarding

If you have any private repositories, the easiest way to do this is to use SSH Agent and forward it into your Docker container using the following params into `docker run`:

```bash
$ mkdir docker-license-cache
$ docker run \
    -v $SSH_AUTH_SOCK:/ssh-agent -e SSH_AUTH_SOCK=/ssh-agent \
    -v /localdata/myusername/repos/yolov5:/usr/src/source_repo \
    -v $(pwd)/docker-license-cache:/usr/src/app/.license-cache \
    -v $(pwd)/docker-output:/usr/src/output \
    -it gc_licensing
...
```

### Caching APT licenses

If you're running multiple times, it is probably worth also mounting the apt license cache, which will allow it to persist between runs and reduce the number of calls to the ubuntu package website:

```bash
$ mkdir docker-license-cache
$ docker run \
    -v /localdata/myusername/repos/yolov5:/usr/src/source_repo \
    -v $(pwd)/docker-license-cache:/usr/src/app/.license-cache \
    -v $(pwd)/docker-output:/usr/src/output \
    -it gc_licensing
...
```

### Changing the Entrypoint

You can also enter the container directly and run whatever command you wish like so:

```bash
$ docker run \
    -v /localdata/myusername/repos/yolov5:/usr/src/source_repo \
    -v $(pwd)/docker-output:/usr/src/output \
    -it --entrypoint /bin/bash gc_licensing
...
```

To run the tests:

```bash
$ docker run -t gc_licensing_test
=================== test session starts ===================
platform linux -- Python 3.8.10, pytest-6.2.5, py-1.11.0, pluggy-1.0.0
rootdir: /usr/src/app
plugins: pythonpath-0.7.3, anyio-3.6.2
collected 95 items
...
```

## Re-Running from Existing Files

When you run the application, it stores its intermediate CSVs of packages and their licenses in the application root directory.
These can then be passed back into the application using the `--reqs-before-install` and `--reqs-after-install` options.

## Automatic Upload to Confluence

You must first provide your Confluence API key to the application by following the [Setup](#setup) instructions further up this page.

If running from a Docker image, run the setup locally, then mount `user.config.yml` directly into the container:

```docker run -v $(pwd)/gc_licensing/user.config.yml:/usr/src/app/gc_licensing/user.config.yml```

Once you're logged in:

* Start by creating a new OSS Application Review form.
* Publish it, but keep the status flag as "in progress".
* From the page URL, extract the page ID - the numerical ID after `/pages/`:

```text
https://<confluence>/wiki/spaces/~1234567/pages/87654321/OSS+Page+Demo
==>
87654321
```

* Run the application with the additional flag: `--upload-page-id 87654321`

## Limitations

* If your requirements file includes conditional installs, the tool will only check packages that match the host system.
* `requirements-parser` can't handle local wheels in the requirements file, and crashes out ungracefully. These won't work.
* There is currently no automatic way to check the license of the Docker base image.
* Probably lots of others...

## Troubleshooting

```text
pkg_resources.DistributionNotFound: The 'fqdn; extra == "format-nongpl"' distribution was not found and is required by jsonschema
```

Your virtual environment might not be able to see the system site packages, which is required for some of the apt licensing checks.
Recreate your virtual env with the `--system-site-packages` flag.

## TODO

* Any deps come pre-installed get ignored. I think this is ok for now, but might not be...
* A better way of handling the intermediate files.
* Handling git repos as pip dependencies
* Handling git repos cloned in docker containers

## LICENSE

This application is MIT licensed. Please see [LICENSE](LICENSE) for the full license text.
