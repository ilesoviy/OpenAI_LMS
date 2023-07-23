"""
This script generates code owner mappings for monitoring LMS.

Sample usage::

    python lms/djangoapps/monitoring/scripts/generate_code_owner_mappings.py --repo-csv "Own Repos.csv" --app-csv "Own edx-platform Apps.csv" --dep-csv "Reference edx-platform Libs.csv"

Or for more details::

    python lms/djangoapps/monitoring/scripts/generate_code_owner_mappings.py --help


"""
import csv
import os
import re

import click

# Maps edx-platform installed Django apps to the edx repo that contains
# the app code. Please add in alphabetical order.
#
# The URLs here must match the URLs in the "Own: Repos" sheet:
# https://docs.google.com/spreadsheets/d/1qpWfbPYLSaE_deaumWSEZfz91CshWd3v3B7xhOk5M4U/view#gid=1990273504
EDX_REPO_APPS = {
    'bulk_grades': 'https://github.com/openedx/edx-bulk-grades',
    'coaching': 'https://github.com/edx/platform-plugin-coaching',
    'completion': 'https://github.com/openedx/completion',
    'config_models': 'https://github.com/openedx/django-config-models',
    'consent': 'https://github.com/openedx/edx-enterprise',
    'csrf': 'https://github.com/openedx/edx-drf-extensions',
    'edx_name_affirmation': 'https://github.com/edx/edx-name-affirmation',
    'edx_proctoring': 'https://github.com/openedx/edx-proctoring',
    'edxval': 'https://github.com/openedx/edx-val',
    'enterprise': 'https://github.com/openedx/edx-enterprise',
    'enterprise_learner_portal': 'https://github.com/openedx/edx-enterprise',
    'eventtracking': 'https://github.com/openedx/event-tracking',
    'help_tokens': 'https://github.com/openedx/help-tokens',
    'integrated_channels': 'https://github.com/openedx/edx-enterprise',
    'learner_pathway_progress': 'https://github.com/edx/learner-pathway-progress',
    'lti_consumer': 'https://github.com/openedx/xblock-lti-consumer',
    'notices': 'https://github.com/edx/platform-plugin-notices',
    'organizations': 'https://github.com/openedx/edx-organizations',
    'search': 'https://github.com/openedx/edx-search',
    'super_csv': 'https://github.com/openedx/super-csv',
    'wiki': 'https://github.com/openedx/django-wiki',
}

# Maps edx-platform installed Django apps to the third-party repo that contains
# the app code. Please add in alphabetical order.
#
# The URLs here must match the URLs in the "Reference: edx-platform Libs" sheet:
# https://docs.google.com/spreadsheets/d/1qpWfbPYLSaE_deaumWSEZfz91CshWd3v3B7xhOk5M4U/view#gid=506252353
THIRD_PARTY_APPS = {
    'corsheaders': 'https://github.com/adamchainz/django-cors-headers',
    'django': 'https://github.com/django/django',
    'django_object_actions': 'https://github.com/crccheck/django-object-actions',
    'drf_yasg': 'https://github.com/axnsan12/drf-yasg',
    'edx_sga': 'https://github.com/mitodl/edx-sga',
    'lx_pathway_plugin': 'https://github.com/open-craft/lx-pathway-plugin',
    'oauth2_provider': 'https://github.com/jazzband/django-oauth-toolkit',
    'rest_framework': 'https://github.com/encode/django-rest-framework',
    'simple_history': 'https://github.com/treyhunner/django-simple-history',
    'social_django': 'https://github.com/python-social-auth/social-app-django',
}


@click.command()
@click.option(
    '--repo-csv',
    help="File name of .csv file with repo ownership details.",
    required=True
)
@click.option(
    '--app-csv',
    help="File name of .csv file with edx-platform app ownership details.",
    required=True
)
@click.option(
    '--dep-csv',
    help="File name of .csv file with edx-platform 3rd-party dependency ownership details.",
    required=True
)
def main(repo_csv, app_csv, dep_csv):
    """
    Reads CSV of ownership data and outputs config.yml setting to system.out.

    Expected Repo CSV format:

        \b
        repo url,owner.squad
        https://github.com/openedx/edx-bulk-grades,team-red
        ...

    Expected App CSV format:

        \b
        Path,owner.squad
        ./openedx/core/djangoapps/user_authn,team-blue
        ...

    Expected 3rd-party Dependency CSV format:

        \b
        repo url,owner.squad
        https://github.com/django/django,team-red
        ...

    Final output only includes paths which might contain views.

    """
    # Maps theme name to a list of code owners in the theme, and squad to full code owner name.
    # Code owner is a string combining theme and squad information.
    owner_map = {'theme_to_owners_map': {}, 'squad_to_theme_map': {}}
    # Maps owner names to a list of dotted module paths.
    # For example: { 'team-red': [ 'openedx.core.djangoapps.api_admin', 'openedx.core.djangoapps.auth_exchange' ] }
    owner_to_paths_map = {}
    _map_repo_apps('edx-repo', repo_csv, EDX_REPO_APPS, owner_map, owner_to_paths_map)
    _map_repo_apps('3rd-party', dep_csv, THIRD_PARTY_APPS, owner_map, owner_to_paths_map)
    _map_edx_platform_apps(app_csv, owner_map, owner_to_paths_map)

    # NB: An automated script looks for this comment when updating config files,
    # so please update regenerate_code_owners_config.py in jenkins-job-dsl-internal
    # if you change the comment format here.
    print(f'# Do not hand edit CODE_OWNER_MAPPINGS. Generated by {os.path.basename(__file__)}')
    print('CODE_OWNER_MAPPINGS:')
    for owner, path_list in sorted(owner_to_paths_map.items()):
        print(f"  {owner}:")
        path_list.sort()
        for path in path_list:
            print(f"  - {path}")

    owner_with_mappings_set = set(owner_to_paths_map.keys())
    print(f'# Do not hand edit CODE_OWNER_THEMES. Generated by {os.path.basename(__file__)}')
    print('CODE_OWNER_THEMES:')
    for theme, owner_list in sorted(owner_map['theme_to_owners_map'].items()):
        theme_owner_set = set(owner_list)
        # only include the theme's list of owners that have mappings
        theme_owner_with_mappings_list = list(theme_owner_set & owner_with_mappings_set)
        if theme_owner_with_mappings_list:
            print(f"  {theme}:")
            theme_owner_with_mappings_list.sort()
            for owner in theme_owner_with_mappings_list:
                print(f"  - {owner}")


def _map_repo_apps(csv_type, repo_csv, app_to_repo_map, owner_map, owner_to_paths_map):
    """
    Reads CSV of repo ownership and uses app_to_repo_map to update owner_map and owner_to_paths_map

    Arguments:
        csv_type (string): Either 'edx-repo' or '3rd-party' for error message
        repo_csv (string): File name for the edx-repo or 3rd-party repo csv
        app_to_repo_map (dict): Dict mapping Django apps to repo urls
        owner_map (dict): Dict of owner details
        owner_to_paths_map (dict): Holds results mapping owner to paths

    """
    with open(repo_csv) as file:
        csv_data = file.read()
    reader = csv.DictReader(csv_data.splitlines())

    csv_repo_to_owner_map = {}
    for row in reader:
        owner = _get_and_map_code_owner(row, owner_map)
        csv_repo_to_owner_map[row.get('repo url')] = owner

    for app, repo_url in app_to_repo_map.items():
        owner = csv_repo_to_owner_map.get(repo_url, None)
        if owner:
            if owner not in owner_to_paths_map:
                owner_to_paths_map[owner] = []
            owner_to_paths_map[owner].append(app)
        else:
            raise Exception(
                f'ERROR: Repo {repo_url} was not found in {csv_type} csv. Needed for app {app}. '
                'Please reconcile the hardcoded lookup tables in this script with the ownership '
                'sheet.'
            )


def _map_edx_platform_apps(app_csv, owner_map, owner_to_paths_map):
    """
    Reads CSV of edx-platform app ownership and updates mappings
    """
    with open(app_csv) as file:
        csv_data = file.read()
    reader = csv.DictReader(csv_data.splitlines())
    for row in reader:
        path = row.get('Path')
        owner = _get_and_map_code_owner(row, owner_map)

        # add paths that may have views
        may_have_views = re.match(r'.*djangoapps', path) or re.match(r'[./]*openedx\/features', path)
        # remove cms (studio) paths and tests
        may_have_views = may_have_views and not re.match(r'.*(\/tests\b|cms\/).*', path)

        if may_have_views:
            path = path.replace('./', '')  # remove ./ from beginning of path
            path = path.replace('/', '.')  # convert path to dotted module name

            # skip catch-alls to ensure everything is properly mapped
            if path in ('common.djangoapps', 'lms.djangoapps', 'openedx.core.djangoapps', 'openedx.features'):
                continue

            if owner not in owner_to_paths_map:
                owner_to_paths_map[owner] = []
            owner_to_paths_map[owner].append(path)


def _get_and_map_code_owner(row, owner_map):
    """
    From a csv row, takes the theme and squad, update ownership maps, and return the code_owner.

    Will also warn if the squad appears in multiple themes.

    Arguments:
        row: A csv row that should have 'owner.theme' and 'owner.squad'.
        owner_map: A dict with 'theme_to_owners_map' and 'squad_to_theme_map' keys.

    Returns:
        The code_owner for the row.  This is made from the theme+squad (or squad if there is no theme).

    """
    theme = row.get('owner.theme')
    squad = row.get('owner.squad')
    assert squad, 'Csv row is missing required owner.squad: %s' % row

    # use lower case names only
    squad = squad.lower()
    if theme:
        theme = theme.lower()

    owner = f'{theme}-{squad}' if theme else squad
    theme = theme or squad

    if squad not in owner_map['squad_to_theme_map']:
        # store the theme for each squad for a later data integrity check
        owner_map['squad_to_theme_map'][squad] = theme

        # add to the list of owners for each theme
        if theme not in owner_map['theme_to_owners_map']:
            owner_map['theme_to_owners_map'][theme] = []
        owner_map['theme_to_owners_map'][theme].append(owner)

    # assert that squads have a unique theme. otherwise we have a data integrity issues in the csv.
    assert owner_map['squad_to_theme_map'][squad] == theme, \
        'Squad %s is associated with theme %s in row %s, but theme %s elsewhere in the csv.' % \
        (squad, theme, row, owner_map['squad_to_theme_map'][squad])

    return owner


if __name__ == "__main__":
    main()  # pylint: disable=no-value-for-parameter
