#!/usr/bin/env python
"""
Automate the creation of a new HySDS framework release. This scripts:

1. Checks if a new release needs to be created for each hysds-framework repository
   e.g. hysds, hysds_commons, sciflo, osaka, etc.
2. If so, prompts the user for a tag release and release description then creates 
   a new release for the repository.
3. If a new release was created for any of the repositories, prompts the user for 
   a tag release and release description then creates a new release for the 
   hysds-framework. It will collect the most recent public release of all tarballs
   for each hysds-framework repository and attaches them to the new hysds-framework
   release.
"""
from __future__ import print_function
import os, sys, re, requests, json, logging, argparse, tempfile
from subprocess import call
from urlparse import urlparse


log_format = "[%(asctime)s: %(levelname)s/%(funcName)s] %(message)s"
logging.basicConfig(format=log_format, level=logging.INFO)


TOKEN_RE = re.compile(r'^GIT_OAUTH_TOKEN\s*=\s*(\S+)\s*')
URL_TOKEN_RE = re.compile(r'^(.+://)(?:.+@)?(.+)$')
TAG_RE = re.compile(r'v\d+\.\d+\.\d+(-.+)?$')
CR_RE = re.compile('\r')
HOST_RE = re.compile(r'^(.+://.+?)/(.+?)/(.+?)/.*$')
UPLOAD_RE = re.compile(r'^(.+/assets){?.*$')


FRAMEWORK_CFG = {
    "hysds-framework": {
        "owner": "hysds"
    }
}


REPO_CFGS = {
    "container-builder": {
        "owner": "hysds"
    },
    "figaro": {
        "owner": "hysds"
    },
    "grq2": {
        "owner": "hysds"
    },
    "hysds": {
        "owner": "hysds"
    },
    "hysds-cloud-functions": {
        "owner": "hysds"
    },
    "hysds-dockerfiles": {
        "owner": "hysds"
    },
    "hysds_commons": {
        "owner": "hysds"
    },
    "lightweight-jobs": {
        "owner": "hysds"
    },
    "mozart": {
        "owner": "hysds"
    },
    "osaka": {
        "owner": "hysds"
    },
    "prov_es": {
        "owner": "hysds"
    },
    "s3-bucket-listing": {
        "owner": "hysds"
    },
    "sdscli": {
        "owner": "sdskit"
    },
    "sciflo": {
        "owner": "hysds"
    },
    "spyddder-man": {
        "owner": "hysds"
    },
    "tosca": {
        "owner": "hysds"
    }
}


COLOR_CODE = {
    "red": "{};31",
    "green": "{};32",
}


def mask_token(url): return TOKEN_RE.sub(r'\1xxxxxxxx@\2', url)


def highlight(s, color="green", bold=True):
    """Return colored string."""

    color_code = COLOR_CODE[color].format("1" if bold else "0")
    return "\033[{};40m{}\033[0m".format(color_code, s)
    

def parse_url(url):
    """Return oauth token and url."""

    u = urlparse(url)
    if '@' in u.netloc:
        token, host = u.netloc.split('@')
    else:
        token = None
        host = u.netloc
    return token, '{}://{}{}'.format(u.scheme, host, u.path)


def get_token(url):
    """Get GitHub OAuth token from url or user file."""

    token, api_url = parse_url(url)
    if token is not None: return token, api_url
    tkn_file = os.path.join(os.path.expanduser("~"), ".git_oauth_token")
    if not os.path.exists(tkn_file):
       raise(RuntimeError("Github token not specified in URL or in {}.".format(tkn_file)))
    with open(tkn_file) as f:
        match = TOKEN_RE.search(f.read())
    if not match:
       raise(RuntimeError("Failed to get GitHub token from {}".format(tkn_file)))
    return match.group(1), api_url
    

def call_github_api(url, token, method="get", **kargs):
    """General function to call github API."""

    headers = { 'Authorization': 'token %s' % token }
    r = getattr(requests, method)(url, headers=headers, **kargs)
    if r.status_code not in (200, 201):
        logging.error("Error response: {}".format(r.content))
    r.raise_for_status()
    return r.json()


def get_input(prompt, regex=None):
    """Get input from user."""

    while True:
        val = raw_input(prompt).strip()
        while True:
            if val == '': break
            if regex is not None and not regex.search(val):
                print(highlight("Invalid format. Try to match pattern: {}".format(regex.pattern), "red"))
                break
            confirm = raw_input("You typed: {}. Are you sure? [y/n]: ".format(highlight(val))).strip().lower()
            if confirm == 'y': return val
            elif confirm == 'n': break
            else: continue


def get_editor_input(prompt):
    """Get input from user using editor defined by os.environ['EDITOR'].
       Defaults to vim."""

    prompt = CR_RE.sub("", prompt)
    while True:
        with tempfile.NamedTemporaryFile(suffix=".tmp") as f:
            f.write(prompt)
            f.flush()
            call([os.environ.get('EDITOR', 'vim'), f.name])
            f.seek(0)
            val = f.read()
        while True:
            if val == '': break
            confirm = raw_input("You typed:\n\n{}\n\nAre you sure? [y/n]: ".format(highlight(val))).strip().lower()
            if confirm == 'y': return val
            elif confirm == 'n': break
            else: continue


def create_new_release(url, token, owner, repo, latest_rel_info, com_info):
    """Create new release. Prompt user for tag_name, name, and body."""

    rel_api_url = "{}/repos/{}/{}/releases".format(url, owner, repo)
    prompt = "Enter the tag_name for the new release: "
    tag_name = get_input(prompt, TAG_RE)
    logging.info("tag_name: {}".format(tag_name))
    prompt = "Name of previous release was \"{}\".\n".format(highlight(latest_rel_info['name'], "red"))
    prompt += "Enter the name for the new release: "
    name = get_input(prompt)
    logging.info("name: {}".format(name))
    prompt = "Specify body of new release. Previous release's body below:\n\n{}".format(latest_rel_info['body'])
    #logging.info("{}".format(json.dumps(com_info, indent=2)))
    prompt += "\n\n\nTo help you formulate the release body, the list of behind commit messages are provided below:\n\n"
    for cmt in com_info['commits']:
        prompt += "sha: {}\n".format(cmt['sha'])
        prompt += "html_url: {}\n".format(cmt['html_url'])
        prompt += "message:\n\n  {}\n\n".format(cmt['commit']['message'])
    body = get_editor_input(prompt)
    #logging.info("body: {}".format(body))
    rel_body = {
        "tag_name": tag_name,
        "target_commitish": latest_rel_info['target_commitish'],
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False, 
    }
    new_rel_info = call_github_api(rel_api_url, token, method="post", data=json.dumps(rel_body))
    #logging.info("new_rel_info: {}".format(json.dumps(new_rel_info, indent=2)))
    return new_rel_info


def download_file(url, outdir='.', fname=None, token=None, session=None):
    """Download file."""

   
    headers = {}
    if token is not None: headers['Authorization'] = 'token %s' % token
    if session is None: session = requests.session()
    if fname is None:
        path = os.path.join(outdir, os.path.basename(url))
    else:
        path = os.path.join(outdir, fname)
    logging.info('Downloading URL: {}'.format(url))
    r = session.get(url, stream=True, verify=False, headers=headers, allow_redirects=True)
    val = r.raise_for_status()
    with open(path,'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)
                f.flush()
    return path


def upload_file(url, token, fname, file):
    """Upload asset to release."""

    headers = {
        'Authorization': 'token %s' % token,
        'Content-Type': "application/octet-stream"
    }
    r = requests.post("{}?name={}".format(url, fname), data=open(file, 'r'), headers=headers)
    if r.status_code not in (200, 201):
        logging.error("Error response: {}".format(r.content))
    r.raise_for_status()
    return r.json()


def upload_repo_asset(url, token, owner, fw_repo, new_rel_info, repo, repo_rel_info):
    """Upload repo assets to framework release."""

    # get upload url
    match = UPLOAD_RE.search(new_rel_info['upload_url'])
    if not match: raise(RuntimeError("Failed to detect url from upload_url"))
    upload_url = match.group(1)
    #logging.info("upload_url: {}".format(upload_url))

    # using tarbal_url gives tarball directory named according to
    # https://stackoverflow.com/questions/6334040/when-i-download-a-zip-from-github-what-is-the-hex-string-at-the-end-of-the-file
    #archive_url = repo_rel_info['tarball_url']

    # use codeload url to get apprpriately named directory
    #logging.info("repo_rel_info: {}".format(json.dumps(repo_rel_info, indent=2, sort_keys=True)))
    match = HOST_RE.search(repo_rel_info['html_url'])
    if not match: raise(RuntimeError("Failed to detect host from html_url"))
    #logging.info("html_url: {}".format(repo_rel_info['html_url']))
    if match.group(1) == "https://github.com":
        archive_url = "https://codeload.github.com/{}/{}/tar.gz/{}".format(match.group(2), match.group(3), repo_rel_info['tag_name'])
    else:
        archive_url = "{}/_codeload/{}/{}/tar.gz/{}".format(match.group(1), match.group(2), match.group(3), repo_rel_info['tag_name'])
    #logging.info("archive_url: {}".format(archive_url))

    fname = "{}-{}.tar.gz".format(repo, repo_rel_info['tag_name'])
    file = download_file(archive_url, fname=fname, token=token)
    logging.info("downloaded {}".format(file))

    # upload to new framework release as an asset
    asset_info = upload_file(upload_url, token, fname, file)
    logging.info("uploaded {}".format(file))
    #logging.info("asset_info {}".format(json.dumps(asset_info, indent=2)))
    os.unlink(file)


def create_new_framework_release(url, token, owner, repo, latest_rel_info, repo_rel_info):
    """Create new framework release. Prompt user for tag_name, name, and body."""

    rel_api_url = "{}/repos/{}/{}/releases".format(url, owner, repo)
    prompt = "Enter the tag_name for the new hysds-framework release: "
    tag_name = get_input(prompt, TAG_RE)
    logging.info("tag_name: {}".format(tag_name))
    prompt = "Name of previous release was \"{}\".\n".format(highlight(latest_rel_info['name'], "red"))
    prompt += "Enter the name for the new release: "
    name = get_input(prompt)
    logging.info("name: {}".format(name))
    prompt = "To help you formulate the release body, links to updated repo releases are listed below:\n\n"
    prompt += "Bug fixes and enhancement:\n\n"
    for i in repo_rel_info:
        rinfo = repo_rel_info[i]
        if rinfo.get('update_for_hysds-framework', False):
            prompt += "# {}[{}] ({}):\n".format(i, rinfo['tag_name'], rinfo['html_url'])
            prompt += "{}\n".format(rinfo['body'])
    body = get_editor_input(prompt)
    #logging.info("body: {}".format(body))
    rel_body = {
        "tag_name": tag_name,
        "target_commitish": latest_rel_info['target_commitish'],
        "name": name,
        "body": body,
        "draft": False,
        "prerelease": False, 
    }
    new_rel_info = call_github_api(rel_api_url, token, method="post", data=json.dumps(rel_body))
    #logging.info("new_framework_rel_info: {}".format(json.dumps(new_rel_info, indent=2)))

    # add all repo assets to this new framework release
    for i in repo_rel_info:
        upload_repo_asset(url, token, owner, repo, new_rel_info, i, repo_rel_info[i])
    return new_rel_info


def main(url, force):
    """Route request."""

    token, api_url = get_token(url)
    #logging.info("Github token: {}".format(token))
    logging.info("Github repo URL: {}".format(mask_token(url)))

    # do a new hysds-framework release
    new_framework_release = True if force else False

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
            new_rel_info = create_new_release(url, token, owner, repo, latest_rel_info, com_info)
            new_rel_info['update_for_hysds-framework'] = True
            release_info[repo] = new_rel_info
            new_framework_release = True
        else:
            logging.info("commits since {}: {}".format(tag_name, highlight(commits_since_release)))
            logging.info("Latest release of {}, {}, is up-to-date.".format(repo, highlight(tag_name)))
            release_info[repo] = latest_rel_info

    #logging.info("release_info for repos: {}".format(json.dumps(release_info, indent=2)))

    # create new framework release
    repo = 'hysds-framework'
    owner = FRAMEWORK_CFG[repo]['owner']
    logging.info("repo: {}/{}".format(owner, repo))
    rel_api_url = "{}/repos/{}/{}/releases/latest".format(url, owner, repo)
    latest_rel_info = call_github_api(rel_api_url, token)
    tag_name = latest_rel_info['tag_name']
    #logging.info("latest release for {}: {}".format(repo, json.dumps(latest_rel_info, indent=2)))
    if new_framework_release:
        logging.info("Latest release of {}, {}, is outdated or --force option specified.".format(repo, highlight(tag_name, "red")))
        logging.info("Creating a new hysds-framework release.")
        new_rel_info = create_new_framework_release(url, token, owner, repo, latest_rel_info, release_info)
        latest_rel_info = call_github_api(rel_api_url, token)
        logging.info("new framework info: {}".format(json.dumps(latest_rel_info, indent=2)))
    else: logging.info("Not creating a new hysds-framework release. Specify --force option to force it.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-f", "--force", help="force creation of new hysds-framework release", action='store_true')
    parser.add_argument("repo_api_url", help="Github API url for repo, e.g. https://github.jpl.nasa.gov/api/v3 or" + \
                        " https://api.github.com")
    args = parser.parse_args()
    main(args.repo_api_url, args.force)

