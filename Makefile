.PHONY: build deploy deploy-guided

build:
	uv export --no-hashes --no-dev --output-file src/requirements.txt
	sam build

deploy-guided: build
	sam deploy --guided

deploy: build
	sam deploy
