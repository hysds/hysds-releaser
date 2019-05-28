#!/usr/bin/env python
"""
Checks if a new release needs to be created for each hysds-framework repository
e.g. hysds, hysds_commons, sciflo, osaka, etc.
"""

import os, sys, re, requests, json, logging, argparse, tempfile
from subprocess import call
from urllib.parse import urlparse

from create_release import *


def main(url):
    """Route request."""

    token, api_url = get_token(url)
    #logging.info("Github token: {}".format(token))
    logging.info("Github repo URL: {}".format(mask_token(token, url)))

    # loop over repos and check if release needs to be made
    release_info = {}
    for repo in REPO_CFGS:

        # get latest release
        owner = REPO_CFGS[repo]['owner']
        logging.info("repo: {}/{}".format(owner, repo))
        rel_api_url = "{}/repos/{}/{}/releases/latest".format(url, owner, repo)
        latest_rel_info = call_github_api(rel_api_url, token)
        #logging.info("latest release for {}: {}".format(repo, json.dumps(latest_rel_info, indent=2)))

        # compare latest release with target_commitish (master)
        tag_name = latest_rel_info['tag_name']
        target_commitish = latest_rel_info['target_commitish']
        logging.info("tag_name: {}".format(tag_name))
        logging.info("target_commitish: {}".format(target_commitish))
        coms_api_url = "{}/repos/{}/{}/compare/{}...{}".format(url, owner, repo, tag_name, target_commitish)
        com_info = call_github_api(coms_api_url, token)

        # if there are commits since the latest release, create new release
        commits_since_release = com_info['total_commits']
        if commits_since_release > 0:
            logging.info("commits since {}: {}".format(tag_name, highlight(commits_since_release, "red")))
            logging.info("Latest release of {}, {}, is outdated.".format(repo, highlight(tag_name, "red")))
        else:
            logging.info("commits since {}: {}".format(tag_name, highlight(commits_since_release)))
            logging.info("Latest release of {}, {}, is up-to-date.".format(repo, highlight(tag_name)))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo_api_url", help="Github API url for repo, e.g. https://github.jpl.nasa.gov/api/v3 or" + \
                        " https://api.github.com")
    args = parser.parse_args()
    main(args.repo_api_url)

