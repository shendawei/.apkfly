#!/usr/bin/env python3
# encoding: utf-8

__Author__ = 'maxinliang'
__Date__ = '2021-11-20'

import argparse
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

    def project_upload(self, project, filepath):
        if os.path.exists(filepath):
            result = project.upload(os.path.basename(filepath), filepath=filepath)
            return result
        else:
            print('upload err ~~~')

    def create_merge_request(self, project, source_branch, target_branch, assignee_id=None, description=None):
        '''创建 merge request
        :param project
        :param source_branch
        :param target_branch
        :param assignee_id 审批人id
        :param description: 描述
        '''
        mr = project.mergerequests.create({'source_branch': source_branch,
                                           'target_branch': target_branch,
                                           'title': "Merge branch '%s' into '%s'" % (source_branch, target_branch),
                                           'assignee_id':assignee_id,
                                           'description':description,
                                           })
        print(mr)
        return mr

    def get_merge_requests(self, project):
        return project.mergerequests.list()

    def search_project(self, project_name):
        return self.gl.projects.list(search=project_name,all=True,visibility='private')

def cmd_info(args):
    git = GitlabAPI()
    username='maxinliang1'
    user = git.get_user(username)
    print(username + '   ->   ' + str(user))


if __name__ == '__main__':

    # """执行入口
    # """
    # # 默认打印帮助信息
    # if len(sys.argv) == 1:
    #     sys.argv.append('--help')
    # # 创建命令行解析器
    # parser = argparse.ArgumentParser(prog="githelp", description=u"git帮助工具",
    #                                  epilog="make it easy!")
    # subparsers = parser.add_subparsers(title=u"可用命令")
    # subparsers.required = True

    # parser_setting = subparsers.add_parser("info", help=u"info")
    # parser_setting.set_defaults(func=cmd_info)
    # parser_setting.add_argument('-i', "--id", help=u'user id', action='store_true', default=False)

    # # 参数解析
    # args = parser.parse_args()
    # args.func(args)

    git = GitlabAPI()

    username='maxinliang1'

    # user = git.get_user(username)
    # print(username + '   ->   ' + str(user))

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

    # 上传文件，可用于上传lint报告，然后创建mergerequest时上传作为codereview的资料
    # up_result = git.project_upload(project, '/Users/gome007/Desktop/Git.png')
    # print(up_result)
    # {'alt': 'Git', 'url': '/uploads/0f42f60cb2d14077812411f675e0f86f/Git.png', 'markdown': '![Git](/uploads/0f42f60cb2d14077812411f675e0f86f/Git.png)'}

    # 删除分支
    # git.del_project_branch_by_branch_name(project, branch_name)

    # merge request
    # git.create_merge_request(project, 'dev-2', 'master')

    # merge_request_list = git.get_merge_requests(project)
    # for mr in merge_request_list:
    #     print(mr)

    # 搜索projects，可用于输入提示
    # rs = git.search_project('GHy')
    # for r in rs:
    #     print(r)
