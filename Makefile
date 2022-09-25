#codeartifact-login:
#	utils/codeartifact-login.sh

python:
	python --version

install:
#	poetry run pip install --disable-pip-version-check --upgrade pip==21.0.1 setuptools==57.5.0;
	cd app; poetry install
	cd app; poetry env use 3.9.11

rmvenv:
#	rm -rf app/.venv/bin
#	rm -rf app/.venv/lib
#	rm -rf app/.venv/pyvenv.cfg
	rm -rf app/.venv
	rm -rf app/poetry.lock

package:
	cd app; poetry export --without-hashes --format requirements.txt --output requirements.txt
	cd app; poetry run chalice package --pkg-format terraform ../infra
	python utils/hack_terraform.py

plan:
	cd infra; terraform plan

apply:
	cd infra; terraform apply -auto-approve

destroy:
	cd infra; terraform apply -destroy -auto-approve


clean:
	rm -rf ./app/.chalice/deployments
	rm -rf ./app/requirements.txt
	rm -rf ./infra/chalice.tf.json
	rm -rf ./infra/deployment.zip

deploy: package plan apply

build-clean: destroy clean package plan apply

purge: destroy clean