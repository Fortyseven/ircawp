DEST_SSH=wheeljack:~/opt/ircawp-beta/

run:
	uv run -m app

aimee:
	uv run -m app --config ./config.aimee.yml

push-to-wheeljack:
	rsync -azr -v  \
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
		./ \
		$(DEST_SSH)
