# hysds-releaser

## Usage

```
usage: create_release.py [-h] [-f] repo_api_url

Automate the creation of a new HySDS framework release. This scripts: 1.
Checks if a new release needs to be created for each hysds-framework
repository e.g. hysds, hysds_commons, sciflo, osaka, etc. 2. If so, prompts
the user for a tag release and release description then creates a new release
for the repository. 3. If a new release was created for any of the
repositories, prompts the user for a tag release and release description then
creates a new release for the hysds-framework. It will collect the most recent
public release of all tarballs for each hysds-framework repository and
attaches them to the new hysds-framework release.

positional arguments:
  repo_api_url  Github API url for repo, e.g.
                https://github.jpl.nasa.gov/api/v3 or https://api.github.com

optional arguments:
  -h, --help    show this help message and exit
  -f, --force   force creation of new hysds-framework release
```

## Creating a new hysds-framework release
1. Update the `latest_release.txt` file in the `hysds-framework` git repo with the release tag you will use.
2. Commit and push updates to hysds-framework git repo.
3. Run releaser:
   ```
   ./create_release.py https://github.jpl.nasa.gov/api/v3
   ```

   or

   ```
   ./create_release.py https://api.github.com
   ```
