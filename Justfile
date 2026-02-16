DEST_SSH_HOST:="wheeljack"
DEST_SSH_PATH:="~/opt/ircawp-beta/"

run:
	uv run -m app

aimee:
	uv run -m app --config ./config.aimee.yml

test:
	python -m pytest tests/ -v

test-cov:
	python -m pytest tests/ --cov=app --cov-report=html --cov-report=term

test-quick:
	python -m pytest tests/ -q

push-to-wheeljack:
    @echo "-----------------------------"
    @rsync -azr -v  \
        --exclude='__pycache__' \
        --exclude '/venv' \
        --exclude '/.venv' \
        --exclude '/.env' \
        --exclude='/.git' \
        --exclude='/.gitignore' \
        --exclude='/.vscode' \
        --exclude='/_archive' \
        --exclude='/models' \
        --exclude '/attic' \
        ./ {{DEST_SSH_HOST}}:{{DEST_SSH_PATH}}
    @echo "-----------------------------"
    @ssh {{DEST_SSH_HOST}}
