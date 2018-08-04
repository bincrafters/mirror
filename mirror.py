#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

from __future__ import print_function
import os
import requests
import json


def github_token():
    if 'GITHUB_TOKEN' in os.environ:
        return os.environ['GITHUB_TOKEN']
    if os.path.isfile('github.token'):
        return open('github.token', 'r').read().strip()
    raise Exception('no GitHub token provided! '
                    'please specify GITHUB_TOKEN environment variable or create github.token file')


def gitlab_token():
    if 'GITLAB_TOKEN' in os.environ:
        return os.environ['GITLAB_TOKEN']
    if os.path.isfile('gitlab.token'):
        return open('gitlab.token', 'r').read().strip()
    raise Exception('no GitHub token provided! '
                    'please specify GITLAB_TOKEN environment variable or create gitlab.token file')


github_headers = {'Authorization': 'token %s' % github_token()}
gitlab_headers = {'PRIVATE-TOKEN': '%s' % gitlab_token(),
                  'Content-Type': 'application/json'}

github_endpoint = 'https://api.github.com'
gitlab_endpoint = 'https://gitlab.com/api/v4'


def get_github_projects():
    index = 1
    projects = dict()
    while True:
        r = requests.get('%s/orgs/bincrafters/repos?page=%s&per_page=100' % (github_endpoint, index),
                         headers=github_headers)
        if r.status_code != 200:
            raise Exception('GitHub GET request failed %s %s' % (r.status_code, r.content))
        page = json.loads(r.content.decode())
        if not page:
            break
        projects.update({project['name']: project['clone_url'] for project in page})
        index += 1
    return projects


def get_gitlab_projects():
    index = 1
    projects = dict()
    while True:
        r = requests.get('%s/groups/bincrafters/projects?page=%s&per_page=100' % (gitlab_endpoint, index),
                         headers=gitlab_headers)
        if r.status_code != 200:
            raise Exception('GitLab GET request failed %s %s' % (r.status_code, r.content))
        page = json.loads(r.content.decode())
        if not page:
            break
        projects.update({project['name']: project['id'] for project in page})
        index += 1
    return projects


def get_bincrafters_namespace():
    request = dict()
    request['with_projects'] = False
    r = requests.get('%s/groups/bincrafters' % gitlab_endpoint, headers=gitlab_headers, data=json.dumps(request))
    if r.status_code != 200:
        raise Exception('GitLab GET request failed %s %s' % (r.status_code, r.content))
    info = json.loads(r.content.decode())
    return int(info['id'])


def get_user_id():
    r = requests.get('%s/users?username=SSE4' % gitlab_endpoint, headers=gitlab_headers)
    if r.status_code != 200:
        raise Exception('GitLab GET request failed %s %s' % (r.status_code, r.content))
    info = json.loads(r.content.decode())
    return int(info[0]['id'])


if __name__ == '__main__':
    user_id = get_user_id()
    namespace_id = get_bincrafters_namespace()
    gh_projects = get_github_projects()
    gl_projects = get_gitlab_projects()
    for gh_project in gh_projects:
        gh_project_url = gh_projects[gh_project]
        if gh_project not in gl_projects:
            print('adding project %s (%s)...' % (gh_project, gh_project_url))

            request = dict()
            request['name'] = gh_project
            request['namespace_id'] = namespace_id
            request['import_url'] = gh_project_url
            request['mirror'] = True
            r = requests.post('%s/projects' % gitlab_endpoint, headers=gitlab_headers, data=json.dumps(request))
            if r.status_code != 201:
                raise Exception('GitLab POST request failed %s %s' % (r.status_code, r.content))

            info = json.loads(r.content.decode())
            gl_id = info['id']

            print('adding project %s (%s)...done!' % (gh_project, gh_project_url))
        else:
            print('project %s (%s) already exists on GitLab' % (gh_project, gh_project_url))
            gl_id = gl_projects[gh_project]

        print('enable mirroring for project %s (%s)...' % (gh_project, gh_project_url))

        request = dict()
        request['import_url'] = gh_project_url
        request['mirror'] = True
        request['mirror_user_id'] = user_id
        r = requests.put('%s/projects/%s' % (gitlab_endpoint, gl_id), headers=gitlab_headers, data=json.dumps(request))
        if r.status_code != 200:
            raise Exception('GitLab PUT request failed %s %s' % (r.status_code, r.content))

        print('enable mirroring for project %s (%s)...done!' % (gh_project, gh_project_url))

        print('start mirroring for project %s (%s)...' % (gh_project, gh_project_url))
        r = requests.post('%s/projects/%s/mirror/pull' % (gitlab_endpoint, gl_id), headers=gitlab_headers)
        if r.status_code != 200:
            raise Exception('GitLab POST request failed %s %s' % (r.status_code, r.content))
        print('start mirroring for project %s (%s)...done!' % (gh_project, gh_project_url))
