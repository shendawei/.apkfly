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

    def get_project_by_name(self, namespace, name):
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
        self.prn_obj(b)

    def del_project_branch(self, project, branch_ame):
        '''
        删除分支
        :param project: 项目对象
        :param branch_ame: 要删除的分支名称
        :return:
        '''
        project.branches.delete(branch_ame)
        print("del suc ^^^")

    def del_project_branch(self, branch):
        '''删除分支
        :param branch: 要删除的分支对象
        :return:
        '''
        branch.delete()
        print("del suc ^^^")

if __name__ == '__main__':
    git = GitlabAPI()

    # username='maxinliang1'
    
    # user = git.get_user(username)
    # print(username + '   ->   ' + str(user))

    owned_project = git.get_owned_projects()
    for p in owned_project:
        print(p.name + ': ' + p.http_url_to_repo)

    project = git.get_project_by_name('mobile-android-common', 'GHybrid')
    print(project.name)