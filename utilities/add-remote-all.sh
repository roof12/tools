#!/usr/bin/env sh

repos='gitea codeberg github'

found=0

for repo in $repos; do

	url=""
	url=$(git remote get-url $repo)

	if [ $url ]; then

		if [ $found = 0 ]; then
			found=1
			git remote add all "$url"
		fi

		git remote set-url --add --push all $url >/dev/null 2>&1
		echo Adding $repo to remote all
	fi

done
