#!/usr/bin/env python3
# encoding: utf-8
#

__Author__ = 'maxinliang'
__Date__ = '2021-11-20'

import gitlab

import os
import sys

class GitlabAPI(object):
    def __init__(self, *args, **kwargs):
        if os.path.exists('/etc/python-gitlab.cfg'):
            self.gl = gitlab.Gitlab.from_config('gitinfo', ['/etc/python-gitlab.cfg'])
        elif os.path.exists(os.getenv('HOME') + '/.python-gitlab.cfg'):
            self.gl = gitlab.Gitlab.from_config('gitinfo', [os.getenv('HOME') + '/.python-gitlab.cfg'])
        else:
            print('You need to make sure there is a file named "/etc/python-gitlab.cfg" or "~/.python-gitlab.cfg"')
            sys.exit(5)

    def get_user(self, username):
        return self.gl.users.list(username=username)[0]

    def get_user_id(self, username):
        user = self.get_user(username)
        return user.id

    def get_owned_projects(self):
        projects = self.gl.projects.list(owned=True)
        # projects = self.gl.projects.list(all=True)
        return projects

    def get_project_by_name(self, name_with_namespace):
        project = self.gl.projects.get(name_with_namespace)
        return project

    def get_project(self, namespace, name):
        """获取项目对象

        Args:
            namespace ([type]): 组
            name ([type]): 项目名称

        Returns:
            [type]: 项目对象
        """
        project_name_with_namespace = '%s/%s' % (namespace, name)
        project = self.gl.projects.get(project_name_with_namespace)
        return project

    def create_project_branch(self, project, branch_name, ref):
        '''
        创建分支
        :param project: 项目对象
        :param branch_name: 要创建的分支名称
        :param ref: 从哪一个分支创建
        :return:
        '''
        b = project.branches.create({'branch': branch_name, 'ref': ref})
        print("create suc ^^^")

    def del_project_branch_by_branch_name(self, project, branch_ame):
        '''
        删除分支
        :param project: 项目对象
        :param branch_ame: 要删除的分支名称
        :return:
        '''
        try:
            project.branches.delete(branch_ame)
            print("del suc ^^^")
        except gitlab.exceptions.GitlabDeleteError as e:
            print('del err ~~~')

    def del_project_branch_by_branch(self, branch):
        '''删除分支
        :param branch: 要删除的分支对象
        :return:
        '''
        branch.delete()
        print("del suc ^^^")

    def create_merge_request(self, project, source_branch, target_branch, assignee_id = None):
        mr = project.mergerequests.create({'source_branch': source_branch,
                                           'target_branch': target_branch,
                                           'title': "Merge branch '%s' into '%s'" % (source_branch, target_branch),
                                           'assignee_id':assignee_id,
                                           })
        print(mr)

    def get_merge_requests(self, project):
        return project.mergerequests.list()

if __name__ == '__main__':
    git = GitlabAPI()

    username='maxinliang1'

    user = git.get_user(username)
    print(username + '   ->   ' + str(user))

    # owned_project = git.get_owned_projects()
    # for p in owned_project:
    #     print(p.name + ': ' + p.http_url_to_repo)

    project_name_with_namespace = 'maxinliang1/My007Project'
    # 获取project
    project = git.get_project_by_name(project_name_with_namespace)
    print(project.name + ': ' + project.http_url_to_repo)

    # branch_name = '202202test'
    # 创建分支
    # branch = git.create_project_branch(project, branch_name, 'master')
    # print(branch.name)

    # 删除分支
    # git.del_project_branch_by_branch_name(project, branch_name)

    # merge request
    # git.create_merge_request(project, 'dev-2', 'master')

    # merge_request_list = git.get_merge_requests(project)
    # for mr in merge_request_list:
    #     print(mr)

