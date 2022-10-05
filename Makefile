venv:
	cd app; poetry install
	cd app; poetry run pip install --index-url https://pypi.org/simple/ --disable-pip-version-check --upgrade pip==21.0.1 setuptools==57.5.0;

rmvenv:
	rm -rf app/.venv
	rm -rf app/poetry.lock

package:
	cd app; poetry export --without-hashes --format requirements.txt --output requirements.txt
	cd app; poetry run chalice package --pkg-format terraform ../infra
	python utils/terraforming.py

plan:
	cd infra; terraform plan

apply:
	cd infra; terraform apply -auto-approve

empty-s3:
	aws s3 rm s3://nfl-site-8acf57f2-f8f5-4a05-ab52-4674f2837beb/current.html
	aws s3 rm s3://nfl-site-8acf57f2-f8f5-4a05-ab52-4674f2837beb/previous.html

destroy: empty-s3
	cd infra; terraform apply -destroy -auto-approve

clean:
	rm -rf ./app/.chalice/deployments
	rm -rf ./app/requirements.txt
	rm -rf ./infra/chalice.tf.json
	rm -rf ./infra/deployment.zip
	rm -rf ./infra/layer-deployment.zip

deploy: package plan apply

build-clean: destroy clean package plan apply

purge: destroy clean