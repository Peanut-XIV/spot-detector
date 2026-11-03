source ./venv/bin/activate

pyside6-project clean && pyside6-project build && pyside6-deploy -c ./macOS26_deploy.spec
