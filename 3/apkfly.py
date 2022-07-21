#!/usr/bin/env python3
# encoding: utf-8
"""This script is used to manage android project"""
import argparse
import os
import re
import subprocess
import sys
import time
import xml
from collections import Counter
from xml.dom import minidom
import deploy
import tempfile
import json
from xml_etree import modify_project_xml

__author__ = "qiudongchao<1162584980@qq.com>"
__version__ = "6.0.0"

##########################################

file_build_gradle = "build.gradle"
dir_current = os.path.abspath(".")
file_settings = os.path.join(dir_current, "settings.gradle")
file_build = os.path.join(dir_current, file_build_gradle)

###################################################################
### 全局公共方法
###################################################################

def slog(message, loading=False, line=False):
    """
    打印日志
    :param message: 日志信息
    :param loading: 是否 显示进行中 状态
    :param line: 是否 换行
    :return:
    """
    temp = ">>> " + message
    if loading:
        temp = temp + "..."
    if line:
        temp = temp + "\n"
    print(temp)


def sloge(message):
    """
    打印异常日志
    :param message:
    :return:
    """
    print("[Exception] %s" % message)


def slogr(success):
    """
    打印 任务执行结果
    :param success: 是否 成功
    :return:
    """
    slog("O(∩_∩)O哈哈~" if success else "╮(╯▽╰)╭哎")

def sloge4red(message):
    """
    打印异常日志，红色文字
    :param message:
    :return:
    """
    print("\033[1;31m[Exception] %s\033[0m" % message)

def check_root_project():
    """
    校验当前工作空间是否合法
    :return: True or False
    """
    # file_exist = os.path.exists(file_build) and os.path.exists(file_settings)
    # is_file = os.path.isfile(file_settings) and os.path.isfile(file_build)
    file_exist = os.path.exists(file_build)
    is_file = os.path.isfile(file_build)
    result = file_exist and is_file
    if not result:
        raise Exception("工作空间校验失败")


def check_sub_project(sub_project, is_formate):
    """
    校验子项目是否合法
    :param sub_project: 子项目
    :param is_formate: 是否 校验 排序规则
    :return: True or False
    """
    check_result = False
    if os.path.isdir(sub_project):
        if os.path.exists(os.path.join(dir_current, sub_project, file_build_gradle)):
            if is_formate:
                p = re.compile(r"[A-Za-z0-9-]+$")#剔除了数字前缀判读，只有国美在服务器打包时有数组前缀，其他app没有数组前缀
                if p.match(sub_project):
                    check_result = True
            else:
                check_result = True
    return check_result


def exec_sub_project(cmd, args):
    """
    批量执行子项目命令
    :param cmd: 命令
    :param args: 命令行参数
    :return:
    """
    check_root_project()

    print(">>>>>>start to running<<<<<<")
    start_project = args.start
    only = args.only
    start_flag = False
    sub_file_list = [x for x in os.listdir(dir_current) if
                     check_sub_project(x, True)]

    if len(sub_file_list) == 0:
        printRed('not found sub project')
        return

    # print "project sub_file_list >>> ",sub_file_list
    if is_order_sub_project(sub_file_list[0]):
        # 按文件名排序
        sub_file_list.sort()
    else:
        # 按project.xml文件中project的顺序排序
        sub_file_list = sorft_by_projectxml(sub_file_list)
    # print "project sub_file_list sort >>> ",sub_file_list

    for sub_file in sub_file_list:
        if start_project:
            if sub_file.startswith(start_project):
                start_flag = True
        else:
            start_flag = True
        # 中断
        if not start_flag:
            continue
        # 是否只执行一个子项目
        if only:
            start_flag = False
        cmd_result = exec_one_project(cmd, sub_file)
        if cmd_result.find("BUILD SUCCESSFUL") != -1:
            print(">>>Success project:%s" % sub_file)
        else:
            print(">>>Error project:%s" % sub_file)
            break
    print(">>>>>>running stop<<<<<<")

def is_order_sub_project(sub_project_name):
    p = re.compile(r"^\d{3}-[A-Za-z0-9-]+$") # 数字前缀，说明已经排序
    return p.match(sub_project_name)

# 按project.xml文件中project的顺序排序
def sorft_by_projectxml(sub_file_list):
    projects = XmlProject.parser_manifest("projects.xml",allow_private=True)
    patch_list = []
    for project in projects:
        if(project.app == False):
            patch_list.append(project.path)
    sub_file_list_sort = [item for item in patch_list if item in sub_file_list]
    return sub_file_list_sort

def exec_one_project(cmd, sub_file):
    print(">>>Running project:%s" % sub_file)
    # 在settings.gradle 配置子项目
    with open(file_settings, "w") as setting:
        setting.write("include \":%s\"" % sub_file)
    # exec gradle clean uploadArchives
    clean_output = os.popen("gradle :%s:%s" % (sub_file, "clean"))
    print(clean_output.read())
    cmd_output = os.popen("gradle :%s:%s" % (sub_file, cmd))
    cmd_result = cmd_output.read()
    print(cmd_result)
    return cmd_result

def cmd_upload(args):
    """
    upload
    :param args:
    :return:
    """
    exec_sub_project("uploadArchives", args)

# 压缩图片
def cmd_imageCompress(args):
    """
    imageCompress
    :param args:
    :return:
    """
    exec_sub_project("imageCompressRelease", args)


def cmd_close_awb(args):
    """
    关闭awb版本
    :param args:
    :return:
    """
    modifyXMLNode("projects.xml", "false")
    updateVersion("awb", "plus", args.all)


def cmd_open_awb(args):
    """
    开启awb
    :param args:
    :return:
    """
    modifyXMLNode("projects.xml", "true")
    updateVersion("plus", "awb", args.all)


def cmd_upload_awb(args):
    exec_awb_sub_project("uploadArchives")


def modifyXMLNode(manifest, isbundleopen):
    try:
        root = minidom.parse(manifest)
    except (OSError, xml.parsers.expat.ExpatError) as e:
        raise Exception("error parsing manifest %s: %s" % (manifest, e))

    if not root or not root.childNodes:
        raise Exception("no root node in %s" % (manifest,))

    for manifestnode in root.childNodes:
        if manifestnode.nodeName == 'manifest':
            manifestnode.attributes["bundleOpen"].value = isbundleopen
            break
        else:
            raise Exception("no <manifest> in %s" % (manifestnode,))

    # 文件写入
    with open(manifest, "w") as manifestxml:
        manifestxml.write(root.toxml())


def updateVersion(fromv, tov, all):
    first_prop = 'AAR_GFRAME_UTILS_VERSION' if all else 'AAR_GFINANCE_VERSION'
    last_prop = 'AAR_MAPP_VERSION' if all else 'AAR_GTQ_DETAIL_VERSION'
    prop_file_path = os.path.join(dir_current, "gradle.properties")
    if os.path.exists(prop_file_path) and os.path.isfile(prop_file_path):
        print(">>>>>>start to version auto increment<<<<<<")
        aar_list = []
        is_aar = False
        # 遍历所有内容，获取 需要版本号变更的条目
        with open(prop_file_path, "r") as prop_file:
            prop_file_list = prop_file.readlines()
            for prop in prop_file_list:
                if prop.startswith(first_prop):
                    is_aar = True
                    aar_list.append(prop.strip())
                elif prop.startswith(last_prop):
                    aar_list.append(prop.strip())
                    is_aar = False
                else:
                    if is_aar and prop.strip() != '' and not prop.startswith('#'):
                        aar_list.append(prop.strip())
        # 遍历所有内容,并版本号自增
        with open(prop_file_path, "r") as prop_file_r:
            # 获取文件内容
            prop_file_content = prop_file_r.read()
            # 遍历需要版本变更的条目，动态升级版本号
            for aar in aar_list:
                # 此处可对版本号格式进行修改，当前仅适配GomePlus
                new_aar = re.sub(fromv, tov, aar)
                prop_file_content = prop_file_content.replace(aar, new_aar)
                print(">>>replace ", aar, " to ", new_aar)
        # 文件写入
        with open(prop_file_path, "w") as prop_file_w:
            prop_file_w.write(prop_file_content)
        print(">>>>>>running stop<<<<<<")
    else:
        print(">>>>>>error: gradle.properties not exit <<<<<<")


def exec_awb_sub_project(cmd):
    """批量执行子项目命令【gradle】
    """
    check_root_project()

    print(">>>>>>start to running<<<<<<")
    projects = XmlProject.parser_manifest("projects.xml")
    sub_file_list = [x for x in os.listdir(dir_current) if
                     check_sub_project(x, True)]
    # 按文件名排序
    sub_file_list.sort()
    for sub_file in sub_file_list:
        isbundle = is_bundle_project(sub_file, projects)
        if (isbundle):
            print(">>>Running project:%s" % sub_file)
            # 在settings.gradle 配置子项目
            with open(file_settings, "w") as setting:
                setting.write("include \":%s\"" % sub_file)
            # exec gradle clean uploadArchives
            clean_output = os.popen("gradle :%s:%s" % (sub_file, "clean"))
            print(clean_output.read())
            cmd_output = os.popen("gradle :%s:%s" % (sub_file, cmd))
            cmd_result = cmd_output.read()
            print(cmd_result)
            if cmd_result.find("BUILD SUCCESSFUL") != -1:
                print(">>>Success project:%s" % sub_file)
            else:
                print(">>>Error project:%s" % sub_file)
    print(">>>>>>running stop<<<<<<")


def is_bundle_project(sub_file, projects):
    checkbundle = False
    for project in projects:
        if sub_file.endswith(project.path) and project.bundleopen:
            checkbundle = True
            break

    return checkbundle

flutter_setting_content = '''setBinding(new Binding([gradle: this]))
evaluate(new File(settingsDir, '/%s/.android/include_flutter.groovy'))
include \":app\"
project(\":app\").projectDir = new File(settingsDir, '%s')'''

def cmd_setting(args):
    """
    将当前工作空间的项目部署到setting配置文件
    :param args:
    :return:
    """
    check_root_project()

    print(">>>>>>start to running<<<<<<")
    sub_file_list = [x for x in os.listdir(dir_current) if
                     check_sub_project(x, False)]
    setting_content = ""

    if args.flutter:
        mainModule = deploy.getMainModule(sub_file_list)
        if mainModule == None:
            printRed('没有找到主工程')
            return
        flutterModule = ""
        for sub_file in sub_file_list:
            if os.path.exists(os.path.join(dir_current, sub_file, '.android/include_flutter.groovy')):
                flutterModule = sub_file
        if flutterModule == "":
            printRed('没有找到flutter工程')
            return
        setting_content = flutter_setting_content % (flutterModule, mainModule)
        sub_file_list.remove(mainModule)

    for sub_file in sub_file_list:
        if setting_content == "":
            setting_content = "include \":%s\"" % sub_file
        else:
            setting_content += "\ninclude \":%s\"" % sub_file
    # 写入settings.gradle文件
    with open(file_settings, "w") as setting:
        setting.write(setting_content)
    print(">>>>>>running stop<<<<<<")


def cmd_version_add(args):
    """
    版本号 批量增加
    :param args:
    :return:
    """
    first_prop = args.start
    last_prop = args.end
    index = args.index
    value = args.value
    exec_version_add(first_prop, last_prop, index, value)

def exec_version_add(first_prop, last_prop, index, value):
    prop_file_path = os.path.join(dir_current, "gradle.properties")
    if os.path.exists(prop_file_path) and os.path.isfile(prop_file_path):
        print(">>>>>>start to version auto increment<<<<<<")
        aar_list = []
        is_aar = False
        # 遍历所有内容，获取 需要版本号变更的条目
        with open(prop_file_path, "r") as prop_file:
            prop_file_list = prop_file.readlines()
            for prop in prop_file_list:
                if prop.startswith(first_prop):
                    is_aar = True
                    aar_list.append(prop.strip())
                    if prop.startswith(last_prop):#此时开始和结束为同一个module
                        is_aar = False
                elif prop.startswith(last_prop):
                    aar_list.append(prop.strip())
                    is_aar = False
                else:
                    if is_aar and prop.strip() != '' and not prop.startswith('#'):
                        aar_list.append(prop.strip())
        # 遍历所有内容,并版本号自增
        with open(prop_file_path, "r") as prop_file_r:
            # 获取文件内容
            prop_file_content = prop_file_r.read()
            # 遍历需要版本变更的条目，动态升级版本号
            for aar in aar_list:
                if index == 1:
                    num_list = re.findall(r"^[A-Za-z0-9_]+\s*=\s*(\d+)\.\d+\.\d+", aar)
                elif index == 2:
                    num_list = re.findall(r"^[A-Za-z0-9_]+\s*=\s*\d+\.(\d+)\.\d+", aar)
                else:
                    num_list = re.findall(r"^[A-Za-z0-9_]+\s*=\s*\d+\.\d+\.(\d+)", aar)
                if len(num_list) == 1:
                    index_num = num_list[0]
                else:
                    raise ValueError("third num error for [" + aar + "]")
                index_num = int(index_num) + 1
                if value:
                    index_num = value
                # 此处可对版本号格式进行修改，当前仅适配GomePlus
                if index == 1:
                    new_aar = re.sub(r"=\s*\d+", "=" + str(index_num), aar)
                elif index == 2:
                    new_aar = re.sub(r"\.\d+\.", "." + str(index_num) + ".", aar)
                else:
                    new_aar = re.sub(r"\.\d+-", "." + str(index_num) + "-", aar)
                    if new_aar == aar:#部分版本后缀删除了 -plus，所以上面的匹配失败
                        new_aar = re.sub(r"\.\d+$", "." + str(index_num), aar)
                prop_file_content = prop_file_content.replace(aar, new_aar)
                print(">>>replace ", aar, " to ", new_aar)
        # 文件写入
        with open(prop_file_path, "w") as prop_file_w:
            prop_file_w.write(prop_file_content)
        print(">>>>>>running stop<<<<<<")
    else:
        print(">>>>>>error: gradle.properties not exit <<<<<<")


def cmd_prop(args):
    """
    提交gradle.properties到git服务器
    :param args:
    :return:
    """
    prop_file_path = os.path.join(dir_current, "gradle.properties")
    if os.path.exists(prop_file_path) and os.path.isfile(prop_file_path):
        message = "AAR批量打包:"
        branch = args.b
        if args.m:
            message = message + args.m
        else:
            time_info = time.strftime(" %Y-%m-%d %H:%M:%S", time.localtime(time.time()))
            message = message + time_info
        add_cmd = os.popen("git add gradle.properties")
        print(add_cmd.read())
        commit_cmd = os.popen("git commit -m '%s'" % message)
        print(commit_cmd.read())
        push_cmd = os.popen("git push origin %s" % branch)
        print(push_cmd.read())
    else:
        print(">>>>>>error: gradle.properties not exit <<<<<<")


def cmd_dep(args):
    """
    分析依赖关系
    :param args: 命令行参数
    :return:
    """
    project = args.project
    configuration = args.configuration
    dependency = args.dependency

    if not configuration:
        # 默认查询配置
        configuration = "releaseCompileClasspath"

    if dependency:
        # 查看特定依赖
        deps_cmd = "gradle -q %s:dependencyInsight --configuration %s --dependency " + dependency
    else:
        # 查看依赖列表
        deps_cmd = "gradle -q %s:dependencies --configuration %s"

    if os.path.exists(os.path.join(dir_current, project)) and os.path.isdir(project):
        deps_cmd = deps_cmd % (project, configuration)
        printGreen(deps_cmd)
        deps_result = os.popen(deps_cmd)
        content_list = deps_result.readlines()
        dep_list = []
        p = re.compile(r".*?(\S*:\S*:\S*)\s*$")
        for content in content_list:
            print(content.rstrip())
            mvn_list = p.findall(content)
            if len(mvn_list) == 1:
                dep_list.append(mvn_list[0])
        # 去重-所有依赖内容
        dep_list = list(set(dep_list))
        dep_list.sort()
        # dep截取list
        dep_sub_list = [x[0: x.rfind(":")] for x in dep_list]
        sub_counter = Counter(dep_sub_list)
        dep_rep_list = [str(k) for k, v in list(dict(sub_counter).items()) if v > 1]
        index = 1
        for rep in dep_rep_list:
            print("------------------------------------------")
            print(index, "-", [x for x in dep_list if x.find(rep) != -1])
            index += 1
        if len(dep_rep_list) != 0:
            print("------------------------------------------")
    else:
        print(">>>>>>error: project %s not exit <<<<<<" % project)


###################################################################
### Jenkins 自动更新代码
###################################################################

def _git_clone_ser(project_name, git_url, git_branch):
    os.chdir(dir_current)
    clone_cmd = os.popen("git clone %s -b %s %s" % (git_url, git_branch, project_name))
    print(clone_cmd.read())


def _git_pull_ser(project_name, git_branch):
    os.chdir(os.path.join(dir_current, project_name))
    pull_cmd = os.popen("git pull origin %s" % git_branch)
    print(pull_cmd.read())


def cmd_update_project(args):
    """
    更新源码for jenkins
    :param args:
    :return:
    """
    check_root_project()
    is_order = args.order
    allow_private = args.allow_private
    groups = args.by_group
    projects = args.by_project
    ignore_app = args.ignore_app

    try:
        groups_size = len(groups)
        projects_size = len(projects)
        if groups_size > 0 and projects_size > 0:
            raise Exception("by_group 和 by_project 不能同时使用")
        os.chdir(dir_current)
        projects = XmlProject.parser_manifest("projects.xml", by_group=groups, by_project=projects,
                                              allow_private=allow_private, order=is_order,
                                              ignore_app=ignore_app)
        setting_content = ""
        for project in projects:
            os.chdir(dir_current)
            key = project.path
            git_branch = project.branch
            git_url = project.url
            # 获取最新项目源码
            if os.path.exists(os.path.join(dir_current, key)) and os.path.isdir(key):
                print(">>>项目%s存在，更新代码..." % key)
                _git_pull_ser(key, git_branch)
            else:
                print(">>>项目%s不存在，克隆代码..." % key)
                _git_clone_ser(key, git_url, git_branch)
            # 构建setting content
            if setting_content == "":
                setting_content = "include \":%s\"" % key
            else:
                setting_content += "\ninclude \":%s\"" % key
        print(">>>子项目写入setting")
        with open(file_settings, "w") as setting_file:
            setting_file.write(setting_content)
    except Exception as e:
        sloge(e.message)


###################################################################
### git 操作
###################################################################

class XmlProject(object):
    """
    manifest and parser
    """

    def __init__(self, url, branch, path, app, groups, bundleopen):
        if not url.endswith('.git'):
            raise Exception("%s error" % url)
        self.url = url
        self.branch = branch
        self.path = path
        self.app = app
        self.groups = groups
        self.bundleopen = bundleopen

    @staticmethod
    def parser_manifest(manifest, by_group=[], by_project=[], allow_private=False, order=False,
                        ignore_app=False):
        """
        projects.xml 解析
        :param manifest:
        :param by_group:
        :param by_project:
        :param allow_private:
        :param order:
        :param ignore_app:
        :return:
        """
        try:
            root = minidom.parse(manifest)
        except (OSError, xml.parsers.expat.ExpatError) as e:
            raise Exception("error parsing manifest %s: %s" % (manifest, e))

        if not root or not root.childNodes:
            raise Exception("no root node in %s" % (manifest,))

        for manifest in root.childNodes:
            if manifest.nodeName == 'manifest':
                break
            else:
                raise Exception("no <manifest> in %s" % (manifest,))

        host = manifest.getAttribute("host")
        if not host:
            raise Exception("no host attr in %s" % (manifest,))

        base_branch = manifest.getAttribute("branch")
        if not base_branch:
            raise Exception("no branch attr in %s" % (manifest,))

        index = 1
        projects = []
        for node in manifest.childNodes:
            if node.nodeName == 'project':
                url = node.getAttribute("url")
                if not url:
                    raise Exception("no %s in <%s> within %s" %
                                    ("url", "project", manifest))
                if not url.startswith("http") and not url.startswith("git@"):
                    url = host + url
                branch = node.getAttribute("branch")
                if not branch:
                    branch = base_branch
                path = node.getAttribute("path")
                if not path:
                    path = url.split('/')[-1].split('.')[0]
                app = True if "true" == node.getAttribute("app") else False
                groups = node.getAttribute("groups")
                bundleopen = node.getAttribute("bundleOpen")
                allow = False
                if len(by_group) > 0:
                    for group in by_group:
                        if groups and group in groups:
                            allow = True
                            break
                elif len(by_project) > 0:
                    for pro in by_project:
                        if path == pro:
                            allow = True
                            break
                else:
                    allow = True

                # 过滤私有
                if groups and "private" in groups and not allow_private:
                    allow = False
                # 过滤App
                if ignore_app and app:
                    allow = False

                if allow:
                    if order:
                        path = "%s-%s" % (str(index).zfill(3), path)
                    project = XmlProject(url, branch, path, app, groups, bundleopen)
                    projects.append(project)
                    index = index + 1
        return projects


def cmd_clone(args):
    """
    克隆子项目
    :param args:
    :return:
    """
    is_order = args.order
    allow_private = args.allow_private
    groups = args.by_group
    projects = args.by_project
    ignore_app = args.ignore_app

    try:
        groups_size = len(groups)
        projects_size = len(projects)
        if groups_size > 0 and projects_size > 0:
            raise Exception("by_group 和 by_project 不能同时使用")
        os.chdir(dir_current)
        projects = XmlProject.parser_manifest("projects.xml", by_group=groups, by_project=projects,
                                              allow_private=allow_private, order=is_order,
                                              ignore_app=ignore_app)
        for project in projects:
            if not os.path.exists(os.path.join(dir_current, project.path)):
                slog("Module:%s  Branch：%s" % (project.path, project.branch))
                slog("Url:%s" % project.url)
                _git_clone(project.url, project.branch, project.path)
            else:
                slog("%s has already existed" % project.path)
    except Exception as e:
        sloge(e.message)

def _git_clone(url, branch, path):
    """
    clone
    :param url:
    :param branch:
    :param path:
    :return:
    """
    cmd = "git clone %s -b %s %s" % (url, branch, path)
    clone_cmd = os.popen(cmd)
    print(clone_cmd.read())
    print("")  # 换行

def _git_projects():
    """
    获取git子项目
    :return:
    """
    check_root_project()

    sub_projects = []
    sub_file_list = [x for x in os.listdir(dir_current) if
                     check_sub_project(x, False)]
    for sub_file in sub_file_list:
        dir_git = os.path.join(dir_current, sub_file, ".git")
        if os.path.exists(dir_git) and os.path.isdir(dir_git):
            sub_projects.append(sub_file)
        else:
            print(">>>>>>%s is not git repo" % sub_file)
    return sub_projects


def _git_check(branch_name, sub_projects, cmd_list):
    """
    校验git项目合法性
    :param branch_name: 分支名称
    :param sub_projects: 子项目列表list
    :param cmd_list: 命令列表list
    :return: 校验结果
    """
    slog("子项目合法性校验", loading=True)
    result = []
    for sub_file in sub_projects:
        process_status = subprocess.Popen(["git", "status"], stderr=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          cwd=os.path.join(dir_current, sub_file))
        code_status = process_status.wait()
        if code_status == 0:
            result_status = process_status.stdout.read().decode()
            if ("working directory clean" not in result_status) and ("working tree clean" not in result_status):
                result.append("子项目[%s] not clean" % sub_file)
                continue
        else:
            result.append("子项目[%s]运行[git status]异常" % sub_file)
            continue

        out_temp = tempfile.SpooledTemporaryFile('wt')
        fileno = out_temp.fileno()
        # subprocess.PIPE 本身可容纳的量比较小，所以程序会卡死
        process_check = subprocess.Popen(cmd_list, stderr=fileno, stdout=fileno,
                                         cwd=os.path.join(dir_current, sub_file))
        code_check = process_check.wait()
        if code_check == 0:
            out_temp.seek(0)
            result_check = [x.rstrip().decode() for x in out_temp.readlines()]
            for branch in result_check:
                if branch.endswith(branch_name):
                    result.append("子项目[%s] - [%s]存在" % (sub_file, branch_name))
                    break
        else:
            result.append("子项目[%s]运行[git branch -a / git tag]异常" % sub_file)

        if out_temp:
            out_temp.close()
    return result


def _git_create_push(branch_name, sub_projects, cmd_list, is_push):
    """
    创建分支 or Tag
    :param branch_name:
    :param sub_projects:
    :return:
    """
    result_list = []
    for sub_file in sub_projects:
        process_branch = subprocess.Popen(cmd_list, stderr=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          cwd=os.path.join(dir_current, sub_file))
        code_check = process_branch.wait()
        if code_check == 0:
            slog("%s 创建 %s 成功" % (sub_file, branch_name))
        else:
            result_list.append("%s 创建 %s 失败" % (sub_file, branch_name))
            continue

        if is_push:
            process_push = subprocess.Popen(["git", "push", "-u", "origin", branch_name],
                                            stderr=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            cwd=os.path.join(dir_current, sub_file))
            code_push = process_push.wait()
            if code_push == 0:
                slog("%s push %s 成功" % (sub_file, branch_name))
            else:
                result_list.append("%s push %s 失败" % (sub_file, branch_name))

    if len(result_list) > 0:
        slog("-----------------")
        for result in result_list:
            slog(result)
        slogr(False)
    else:
        slogr(True)


def _git_delete_push(branch_name, sub_projects, local_list, push_list, is_push):
    """
    创建分支 or Tag
    :param branch_name:
    :param sub_projects:
    :return:
    """
    result_list = []
    for sub_file in sub_projects:
        process_branch = subprocess.Popen(local_list, stderr=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          cwd=os.path.join(dir_current, sub_file))
        code_check = process_branch.wait()
        if code_check == 0:
            slog("%s 删除 %s 成功" % (sub_file, branch_name))
        else:
            result_list.append(
                "%s 删除 %s 失败\n%s" % (sub_file, branch_name, process_branch.stderr.read()))

        if is_push:
            process_push = subprocess.Popen(push_list, stderr=subprocess.PIPE,
                                            stdout=subprocess.PIPE,
                                            cwd=os.path.join(dir_current, sub_file))
            code_push = process_push.wait()
            if code_push == 0:
                slog("%s 删除远程 %s 成功" % (sub_file, branch_name))
            else:
                result_list.append(
                    "%s 删除远程 %s 失败\n%s" % (sub_file, branch_name, process_push.stderr.read()))

    if len(result_list) > 0:
        slog("-----------------")
        for result in result_list:
            slog(result)
        slogr(False)
    else:
        slogr(True)


def cmd_branch(args):
    """
    创建分支
    :param args:
    :return:
    """
    branch_name = args.name
    is_delete = args.delete
    is_push = args.push
    is_continue_branch = args.continue_branch
    is_include_work_space = args.include_work_space

    sub_projects = _git_projects()
    if is_include_work_space:
        sub_projects.append('./')

    if is_delete:
        _git_delete_push(branch_name, sub_projects, ["git", "branch", "-d", branch_name],
                         ["git", "push", "origin", ":" + branch_name], is_push)
    else:
        result_list = _git_check(branch_name, sub_projects, ["git", "branch", "-a"])
        if len(result_list) > 0:
            # 所有子项目，都是因为-已有分支-的错误
            all_project_is_branch_err = True
            for mess in result_list:
                if branch_name not in mess:
                    all_project_is_branch_err = False
                slog(mess)

            if is_continue_branch:
                # 手动，跳过已有分支的项目
                if all_project_is_branch_err:
                    # 判断_git_check的结果，所有错误都是因为-已有分支-才跳过
                    slog("下面过滤-已有分支-的子项目，然后再批量创建分支", loading=True)
                    # 过滤掉已有分支的子项目
                    filter_project(sub_projects, result_list)
                else:
                    slog("请检查以上错误中不是-已有分支-的错误", loading=False)
                    return
            else:
                slogr(False)
                return

        slog("开始批量创建分支[%s]" % branch_name, loading=True)
        _git_create_push(branch_name, sub_projects, ["git", "checkout", "-b", branch_name], is_push)


def filter_project(sub_projects, result_list):
    for num in range(len(sub_projects)-1, -1, -1):
        isFilter = False
        cur_sub_project = sub_projects[num]
        filter_sub_project_name = "[%s]" % cur_sub_project
        for filter_sub_project_err_msg in result_list:
            if filter_sub_project_name in filter_sub_project_err_msg:
                isFilter = True
                break
        if isFilter:
            del sub_projects[num]
            slog("过滤掉%s" % cur_sub_project)

def cmd_tag(args):
    """
    创建tag
    :param args:
    :return:
    """
    is_delete = args.delete
    tag_name = args.name
    tag_message = args.message
    if not tag_message:
        tag_message = "tag at" + time.strftime(" %Y-%m-%d %H:%M:%S", time.localtime(time.time()))

    sub_projects = _git_projects()
    if is_delete:
        _git_delete_push(tag_name, sub_projects, ["git", "tag", "-d", tag_name],
                         ["git", "push", "origin", ":refs/tags/" + tag_name], True)
    else:
        result_list = _git_check(tag_name, sub_projects, ["git", "tag"])
        if len(result_list) > 0:
            for mess in result_list:
                slog(mess)
            slogr(False)
            return

        slog("批量创建Tag[%s]" % tag_name, loading=True)

        _git_create_push(tag_name, sub_projects, ["git", "tag", "-a", tag_name, "-m", tag_message],
                         True)


def cmd_pull(args):
    """
    git pull
    :param args:
    :return:
    """
    cmd = "git pull"
    try:
        sub_projects = _git_projects()
        for sub_file in sub_projects:
            slog("git pull [%s]" % sub_file)
            os.chdir(os.path.join(dir_current, sub_file))
            result = os.popen(cmd).read().strip()
            print("--\n%s\n--" % result)
            # if "Updating" in result:
            #     raise Exception("[%s] maybe needs to merge" % sub_file)
        slog("All projects have been updated\n")
    except Exception as e:
        sloge(e.message)
    except KeyboardInterrupt:
        sloge("Cancel")


def cmd_reset(args):
    """
    git reset
    :param args:
    :return:
    """
    cmd = "git reset --hard"
    sub_projects = _git_projects()
    print(">>>>>>start to running<<<<<<")
    for sub_file in sub_projects:
        print(">>>>>>Run [git %s] at dir [%s]" % (cmd, sub_file))
        os.chdir(os.path.join(dir_current, sub_file))
        git_cmd = os.popen(cmd)
        print(git_cmd.read())
    print(">>>>>>running stop<<<<<<")


###################################################################
### apk操作：安装、上传等
###################################################################

def cmd_deploy(args):

    # 命令
    upload = args.upload
    install = args.install
    app = args.app_deps_settings_module
    target_modules = args.target_modules
    deps_modules = args.deps_modules
    del_ex_setting_modules = args.del_ex_setting_modules
    project_xml = args.project_xml
    clone_project = args.clone_project

    if upload:
        deploy.uploadApk()
    elif install:
        deploy.installApk()
    elif app:
        # 对主工程进行部署依赖
        deploy.deployMainAppDeps()
    elif target_modules and deps_modules:
        # 检验module都是合法的
        if check_modules(target_modules, deps_modules):
            return
        # 开始部署依赖
        for m in target_modules:
            print('')
            deploy.exclude_aar_dep_source(m, deps_modules)
            print('-------------------------------------------------')
    elif del_ex_setting_modules:
        deploy.deleteExIncludeModule()
    elif project_xml:
        n = 3 # 三个一组：module branch group
        if len(project_xml) % 3 == 0:
            ps = [project_xml[i:i + n] for i in range(0, len(project_xml), n)]
            printRed('参数分组完毕：[module, branch, group]')
            printRed(ps)
            modify_project_xml(ps, 'projects.xml')
        else:
            printRed('参数不合格')
    elif clone_project:
        project_deploy_url = "http://10.2.47.6:8000/project/deploy"
        try:
            import requests
            response = requests.post(project_deploy_url, data = {'project_id':clone_project})
        except ImportError:
            printRed("Please install python requests lib，exec the command：")
            printRed("pip3 install requests")
            return

        if not response or response.status_code != 200:
            printRed(project_deploy_url + " 访问失败")
            return

        project_info = response.json()
        printRed(project_info)

        app_info = project_info.get('app')
        app_name = app_info.get('name')
        app_git = app_info.get('git')
        app_branch = app_info.get('branch')
        app_name_new = app_name + '_' + app_branch

        printGreen('1、clone workspace')
        _git_clone(app_git, app_branch, app_name_new)

        printGreen('2、配置project.xml')
        ms = project_info.get('ms')
        ms_config_list = []
        for m in ms:
            if m.get('git') == app_git:
                # workspace不修改project.xml不然第3步会重复下载workspace
                continue
            ms_config_list.append([m.get('name'), m.get('branch'), m.get('branch')])
        modify_project_xml(ms_config_list, './%s/projects.xml' % app_name_new)

        printGreen('3、clone modules')
        clone_cmd = 'cd %s && ./apkflyw clone -g %s' % (app_name_new, app_branch)
        printGreen(clone_cmd)
        os.popen(clone_cmd).read()

        printGreen('4、deploy app')
        clone_cmd = 'cd %s && ./apkflyw setting && ./apkflyw deploy -app' % app_name_new
        printGreen(clone_cmd)
        os.popen(clone_cmd).read()

        printGreen('执行完毕……^^……打个包试试吧，注意local.properties配置sdk')
    else:
        print('请输入正确命令')

def check_modules(target_modules, deps_modules):
    err = False
    for m in target_modules:
        if not check_sub_project(m, False):
            printRed('%s module不合法，请检查' % m)
            err = True
    for m in deps_modules:
        if not check_sub_project(m, False):
            printRed('%s module不合法，请检查' % m)
            err = True
    return err

def cmd_compile_aar(args):
    setting = args.setting
    modules_aar = args.modules
    version_index = args.version_index
    not_check = args.not_check

    if setting:
        includeModules = deploy.getIncludeModule()
        mainModuleName = deploy.getMainModule(includeModules)
        if mainModuleName:
            # 删除主工程
            includeModules.remove(mainModuleName)
        exec_compile_aars(includeModules, version_index, not_check)
    elif modules_aar:
        exec_compile_aars(modules_aar, version_index, not_check)

def exec_compile_aars(modules_aar, version_index, not_check):
    print('开始打包aar')

    # 注意点： clone代码时用apkfly，确保项目名和projects.xml中的path相同

    # 1、把build.gradle中deps的true全部改为false
    with open(file_build, "r") as file, open("%s.bak" % file_build, "w") as file_bak:
        for line in file:
            line = re.sub(r":\s*(true)\s*\?", ": false ?", line)
            file_bak.write(line)
        file.close()
        file_bak.close()
        # 把新文件覆盖现文件
        os.remove(file_build)
        os.rename("%s.bak" % file_build, file_build)
    print('1、把build.gradle中deps的true全部改为false')

    # 2、根据projects.xml对modules打包排序
    modules_aar_new = []
    if not_check: # 不检查，不排序，直接安装输入的顺序打包
        modules_aar_new = modules_aar
    else:
        projects = XmlProject.parser_manifest("projects.xml", allow_private=True)
        for project in projects:
            for m in modules_aar:
                if m == project.path:
                    modules_aar_new.append(m)
        print('2、根据projects.xml对modules打包排序完成: ')
        print(modules_aar_new)
        if len(modules_aar) != len(modules_aar_new):
            print('请检查输入的moduleNames与projects.xml中的path是否相同')
            return

    # 轮询批量aar
    exec_compile_aar(modules_aar_new, version_index)

    print('3、打包结束')

def exec_compile_aar(modules_aar, version_index):
    for module in modules_aar:
        versionTag = get_module_version_tag(module)
        if versionTag != '':
            # 版本AAR_XXX_YYY +1
            exec_version_add(versionTag, versionTag, version_index, None)
            # 打aar
            cmd_result = exec_one_project("uploadArchives", module)
            if cmd_result.find("BUILD SUCCESSFUL") != -1:
                print(">>>Success project:%s\n\n>>>-------------------------------------NEXT COMPILE AAR-------------------------------------\n" % module)
            else:
                print(">>>Error project:%s" % module)
                if cmd_result.find("uploadArchives FAILED") != -1:
                    print(">>>Error AAR 版本号应该有问题，请检查后再打包")
                elif cmd_result.find("compileReleaseJavaWithJavac FAILED") != -1:
                    print(">>>Error 项目编译应该有问题，请检查后再打包")
                else:
                    print("请检查是否配置全局Gradle命令")
                break
        else:
            print('>>>Error project:%s，版本字段名未找到' % module)
            break

def get_module_version_tag(moduleName):
    """获取module的版本字段名
    :param moduleName:
    :return:
    """
    moduleBuildFile = os.path.join(dir_current, moduleName, file_build_gradle)
    versionTag = ''
    if os.path.exists(moduleBuildFile):
        # 找到module找到对应的version版本AAR_XXX_YYY
        with open(moduleBuildFile, "r") as file:
            for line in file:
                if 'AAR_' in line:
                    versionTags = re.findall(r"\"(\w+)\"", line.strip())
                    if len(versionTags) > 0:
                        versionTag = versionTags[0]
                    break
    return versionTag

def _git_status(sub_projects, is_raise_origin_err = False):
    """校验status
    :param sub_projects project列表
    :param is_raise_origin_err 是否抛出原始错误
    """
    slog("子项目合法性校验", loading=True)
    for sub_file in sub_projects:
        process_status = subprocess.Popen(["git", "status"], stderr=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          cwd=os.path.join(dir_current, sub_file))
        code_status = process_status.wait()
        if code_status == 0:
            result_status = process_status.stdout.read().decode()
            if ("working directory clean" not in result_status) and ("working tree clean" not in result_status):
                if is_raise_origin_err:
                    raise Exception("子项目[%s] not clean\n%s" % (sub_file, result_status))
                else:
                    raise Exception("子项目[%s] not clean" % sub_file)
        else:
            raise Exception("子项目[%s]运行[git status]异常" % sub_file)
        print("子项目[%s] 正常" % sub_file)

def checkout_branch_pull(module, branch):
    printGreen('%s: git checkout %s' % (module, branch))
    # 切换目录到module
    os.chdir(os.path.join(dir_current, module))
    # 切换分支
    git_cmd = os.popen("git checkout %s" % branch)
    print(git_cmd.read())
    # 更新一下
    printGreen('%s: git pull')
    git_cmd = os.popen("git pull")
    print(git_cmd.read())
    # 切换目录到workspace
    os.chdir(dir_current)


def cmd_compile_merge(args):
    branch = args.branch
    workspace_and_setting = args.workspace_and_setting
    main_branch = args.main_branch

    if not branch:
        print('分支名不可为空，请补充 -b 参数')
        return

    # settings.gradle 中的module配置
    include_modules = deploy.getIncludeModule()
    if len(include_modules) < 1:
        printRed('结束合并操作，settings中没有配置module，如果只合并workspace请直接使用git原始操作合并吧')
        return

    # 检查git状态
    try:
        # workspace
        _git_status([dir_current], True)
    except Exception as err:
        printRed(err)
        printGreen('如果当前在主分支，由子分支 -> 主分支，而此时workspace中主动生成创建了project_merge.xml，此时检查合法性肯定报错')
        request_code = input("workspace没有clean，请确定是否忽略这个错误 y/n:")
        if request_code != 'y':
            printRed('结束合并操作')
            return
    # modules
    _git_status(include_modules)

    # 主分支名，从需求分支自动切换到主分支，然后再合并代码（适合工作空间还在需求分支上的场景）
    if main_branch:
        # ~~~~此时，工作空间在需求分支上合并~~~

        # 判断当前分支是否是业务分支
        cBranch = os.popen("git branch --show-current").read().strip()
        if branch != cBranch:
            printRed('当前不在业务分支，请再检查一下branch != cBranch ? %s:%s' % (branch, cBranch))
            return

        # 1、备份需求分支上的projects.xml
        with open("projects.xml", "r") as file:
            content = file.read()
            with open("projects_merge.xml", "w") as wFile:
                wFile.write(content)

        print('\n切换分支…………')

        # 2、把所有合并module都切换到主分支
        # 2.1、先切换workspace到主干，并更新代码，必须在切换module之前切换workspace，因为切换module需要用到主干的projects.xml
        checkout_branch_pull(dir_current, main_branch)

        # 主干project.xml
        projects_main = XmlProject.parser_manifest("projects.xml", by_project=include_modules, allow_private=True)
        # 2.2、setting中配置的module切换到主分支，并更新代码
        for p in projects_main:
            # 打印分割线
            printGreen("------------------------------------------")
            # 切换分支到主干
            checkout_branch_pull(p.path, p.branch)

    # 3、读取需求分支备份的 project_merge.xml配置，获取到所有module的需求分支名（此时module都在主分支）
    projects_merge = None
    if os.path.exists(os.path.join(dir_current, 'projects_merge.xml')):
        request_code = input("当前使用projects_merge.xml中的配置进行合并 y/n:")
        if 'y' == request_code:
            projects_merge = XmlProject.parser_manifest("projects_merge.xml", by_project=include_modules, allow_private=True)
            if len(include_modules) != len(projects_merge):
                print('settings.gradle获取的module数量 %s' % len(include_modules))
                print('projects_merge.xml获取的module数量 %s' % len(projects_merge))
                printRed('结束合并操作，settings.gradle与projects_merge.xml配置的module数量不一样')
                return
        else:
            printRed('结束合并操作')
            return
    else:
        request_code = input("当前没有找到projects_merge.xml，所有合并分支都用%s y/n:" % branch)
        if "y" != request_code:
            printRed('结束合并操作')
            return

    # 组装settings中配置的module合并对象
    merge_modules = []
    if projects_merge:
        for m in projects_merge:
            c_branch = os.popen("cd %s && git branch --show-current && cd .." % m.path).read().strip()
            merge_modules.append({
                'name': m.path,
                'branch': c_branch,
                'm_branch': m.branch,
            })
    else:
        for m in include_modules:
            c_branch = os.popen("cd %s && git branch --show-current && cd .." % m).read().strip()
            merge_modules.append({
                'name': m,
                'branch': c_branch,
                'm_branch': branch,
            })

    # workspace是否合并
    if workspace_and_setting:
        # 加上 WorkSpace
        c_branch = os.popen("git branch --show-current").read().strip()
        merge_modules.append({
            'name': dir_current,
            'branch': c_branch,
            'm_branch': branch,
        })

    if len(merge_modules) < 1:
        printRed("结束合并操作，merge modules is empty")
        return

    printRed('\n\n合并信息如下：')
    for mm in merge_modules:
        printRed('%s 合并: %s -> %s' % (mm.get('name'), mm.get('m_branch'), mm.get('branch')))

    # 马上合并集合中的所有module，用户再次确认合并信息
    request_code = input("请确定上方红色打印的合并信息是否正确 y/n:")
    if request_code != 'y':
        printRed('结束合并操作')
        return

    mergeLogName = 'merge-result.log'

    mergeType1 = 'Already up to date'
    mergeType1M = []

    mergeType2 = 'Fast-forward'
    mergeType2M = []

    mergeType3 = "Merge made by the 'recursiv"
    mergeType3M = []

    mergeType4 = 'CONFLICT'
    mergeType4M = []

    # 无法分析log
    mergeType5M = []

    mergeType6 = 'not something we can merge'
    mergeType6M = []

    # 项目不存在
    mergeType7M = []

    # 4、轮询合并module
    # 合并详细结果，缓存文件
    with open(os.path.join(mergeLogName), "w") as mergeReustLog:

        for mm in merge_modules:
            mm_name = mm.get('name')
            mm_m_branch = mm.get('m_branch')
            start_log = '%s 开始合并: %s -> %s\n' % (mm_name, mm_m_branch, mm.get('branch'))
            print(start_log)
            mergeReustLog.write(start_log)


            if os.path.exists(os.path.join(dir_current, mm_name)) and os.path.isdir(os.path.join(dir_current, mm_name)):
                # 执行合并命令
                out_temp = tempfile.SpooledTemporaryFile('wt')
                fileno = out_temp.fileno()
                # subprocess.PIPE 本身可容纳的量比较小，所以程序会卡死
                process_check = subprocess.Popen(['git', 'merge', mm_m_branch], stderr=fileno, stdout=fileno,
                                                 cwd=os.path.join(dir_current, mm_name))
                code_check = process_check.wait()
                # if code_check != 0:
                #   continue

                # 读取命令执行结果
                out_temp.seek(0)
                merge_result = '\n'.join([x.decode().rstrip() for x in out_temp.readlines()])
                out_temp.close()

                if mergeType1 in merge_result:
                    print('合并成功，分支<%s>没有任何修改' % mm_m_branch)
                    mergeType1M.append(m)
                elif mergeType2 in merge_result:
                    print('合并成功，记得去push [Fast-forward]')
                    mergeType2M.append(m)
                elif mergeType3 in merge_result:
                    print("合并成功，记得去push [Merge made by the 'recursive' strategy]")
                    mergeType3M.append(m)
                elif mergeType4 in merge_result:
                    sloge4red('合并出错，屮艸芔茻，有冲突 <Err>')
                    mergeType4M.append(m)
                elif mergeType6 in merge_result:
                    sloge4red('本项目应该没有该分支%s，请检查后再处理 <Err>' % mm_m_branch)
                    mergeType6M.append(m)
                else:
                    sloge4red('合并出错，无法分析合并log，请自行分析 <Warn>')
                    mergeType5M.append(m)
                mergeReustLog.write('\nmerge_result:\n%s\n' % merge_result)
            else:
                log = '项目不存在，请核实 <Err>'
                sloge4red(log)
                mergeReustLog.write('\n%s\n' % log)
                mergeType7M.append(m)

            end_log = "合并结束\n-----------------------------------------------------"
            print(end_log)
            mergeReustLog.write(end_log + '\n')

    print('\033[33m')
    print(('-' * 100))
    print('\033[0m')

    print('\033[1;35m合并详细日志：根目录的[%s]这个文件\033[0m' % mergeLogName)
    print('\n总结如下，共处理%s个项目：' % len(merge_modules))

    # 当前打印的序号，只打印有用的条目
    printNum = 0
    if len(mergeType1M) > 0:
        printNum = printNum + 1
        msg1 = '\n%s、合并成功，没有任何修改的项目，共%s个：' % (printNum, len(mergeType1M))
        printGreen(msg1)
        print(mergeType1M)

    if len(mergeType2M) > 0:
        printNum = printNum + 1
        msg2 = '\n%s、合并成功，记得去push的项目[Fast-forward]，共%s个：' % (printNum, len(mergeType2M))
        printGreen(msg2)
        print(mergeType2M)

    if len(mergeType3M) > 0:
        printNum = printNum + 1
        msg3 = "\n%s、合并成功，记得去push的项目[Merge made by the 'recursive' strategy]，共%s个：" % (printNum, len(mergeType3M))
        printGreen(msg3)
        print(mergeType3M)

    if len(mergeType4M) > 0:
        printNum = printNum + 1
        msg4 = '\n%s、合并出错，屮艸芔茻，有冲突的项目，共%s个：' % (printNum, len(mergeType4M))
        printRed(msg4)
        print(mergeType4M)

    if len(mergeType5M) > 0:
        printNum = printNum + 1
        msg5 = '\n%s、合并出错，无法分析log，请自行查看的项目，共%s个：' % (printNum, len(mergeType5M))
        printRed(msg5)
        print(mergeType5M)

    if len(mergeType6M) > 0:
        printNum = printNum + 1
        msg6 = '\n%s、没有对应分支的项目，共%s个：' % (printNum, len(mergeType6M))
        printYellow(msg6)
        print(mergeType6M)

    if len(mergeType7M) > 0:
        printNum = printNum + 1
        msg7 = '\n%s、项目不存在，共%s个：' % (printNum, len(mergeType7M))
        printYellow(msg7)
        print(mergeType7M)

def printGreen(message):
    print("\033[0;36m%s\033[0m" % message)

def printRed(message):
    print("\033[0;31m%s\033[0m" % message)

def printYellow(message):
    print("\033[0;33m%s\033[0m" % message)

def cmd_remote(args):
    set = args.set
    if set:
        newHostUrl = set[0]

        rootDir = os.listdir('.')
        for childDir in rootDir:
            swRemoteHost(newHostUrl, childDir)

        swRemoteHost(newHostUrl, os.path.abspath('.'))

        print(" ~~~全部执行完毕 ！！！")

def swRemoteHost(host, moduleDir):
    if os.path.isdir(moduleDir) and ".git" in os.listdir(moduleDir):
        print(moduleDir)

        # 查看远程地址
        remoteV = os.popen("cd %s && git remote -v" % (moduleDir)).read()

        # 分割，找到具体url
        gitOldUrl = remoteV.split("\n")[0].split()[1]
        print("原git地址: %s" % gitOldUrl)

        # 切换远程地址
        gitOldHost = gitOldUrl.split(":")
        # print u"原git host地址: %s" % gitOldHost[0]
        gitNewUrl = gitOldUrl.replace(gitOldHost[0], host)
        print("新git地址: %s" % gitNewUrl)
        cmdSet = "git remote set-url origin %s" % gitNewUrl
        cmdSet = "cd %s && %s" % (moduleDir, cmdSet)
        # print cmdSet
        os.popen(cmdSet).read()
        print("%s 切换远程地址执行完成 ！\n" % moduleDir)
###################################################################
### 主程序入口
###################################################################
if __name__ == '__main__':
    """执行入口
    """
    # debug
    # sys.argv.append("serv-update")

    # 默认打印帮助信息
    if len(sys.argv) == 1:
        sys.argv.append('--help')
    # 创建命令行解析器
    parser = argparse.ArgumentParser(prog="apkfly", description="国美workspace帮助工具",
                                     epilog="make it easy!")
    subparsers = parser.add_subparsers(title="可用命令")
    subparsers.required = True

    # 添加子命令

    # 把workspace内所有的module配置到settings.gradle
    parser_setting = subparsers.add_parser("setting",
                                           help="把workspace内所有的module配置到settings.gradle")
    parser_setting.set_defaults(func=cmd_setting)
    parser_setting.add_argument('-f', "--flutter", help='配置flutter', action='store_true', default=False)

    # 提交gradle.properties到git服务器
    parser_setting = subparsers.add_parser("pushprop", help="提交gradle.properties到git服务器")
    parser_setting.set_defaults(func=cmd_prop)
    parser_setting.add_argument('-m', type=str, help='push评论信息')
    parser_setting.add_argument('-b', type=str, default='mergeDev', help='push 分支')

    # 关闭awb
    parser_close_awb = subparsers.add_parser("closeawb", help="关闭awb开关")
    parser_close_awb.set_defaults(func=cmd_close_awb)
    parser_close_awb.add_argument('-a', "--all", help='所有版本为awb', default=True)

    # 打开awb
    parser_open_awb = subparsers.add_parser("openawb", help="打开awb开关")
    parser_open_awb.set_defaults(func=cmd_open_awb)
    parser_open_awb.add_argument('-a', "--all", help='所有版本为awb', default=True)

    # 版本自增
    parser_version = subparsers.add_parser("version", help="自增gradle.properties内的 aar 配置版本")
    parser_version.set_defaults(func=cmd_version_add)
    parser_version.add_argument('-s', "--start", type=str, default='AAR_MODULE_VERSION_START_TAG',
                                help='起始AAR版本【例：AAR_MFRAME2_VERSION】')
    parser_version.add_argument('-e', "--end", type=str, default='AAR_MAPP_VERSION',
                                help='终止AAR版本')
    parser_version.add_argument('-i', "--index", type=int, default=2, choices=[1, 2, 3],
                                help='自增版本索引【1大版本，2中间版本，3小版本】')
    parser_version.add_argument('-v', '--value', type=int, help='版本，默认值')

    # 批量生成aar并提交至maven私服
    parser_upload = subparsers.add_parser("upload",
                                          help="按module名称 数字排列顺序 依次 执行gradle uploadArchives")
    parser_upload.set_defaults(func=cmd_upload)
    parser_upload.add_argument('-s', "--start", type=str, help='执行起始点【项目名前三位，例：027】')
    parser_upload.add_argument('-o', "--only", help='只执行一个', action='store_true',
                               default=False)

     # 批量对本地module进行图片压缩
    parser_imageCompress = subparsers.add_parser("imageCompress",
                                          help="按module名称 数字排列顺序 依次 执行gradle imageCompress 进行本地图片压缩")
    parser_imageCompress.set_defaults(func=cmd_imageCompress)
    parser_imageCompress.add_argument('-s', "--start", type=str, help='执行起始点【项目名前三位，例：027】')
    parser_imageCompress.add_argument('-o', "--only", help='只执行一个', action='store_true',
                                   default=False)


    # 批量生成awb并提交至maven私服
    parserawb_upload = subparsers.add_parser("uploadawb",
                                             help="按module名称 数字排列顺序 依次 执行gradle uploadArchives")
    parserawb_upload.set_defaults(func=cmd_upload_awb)

    # 分析项目依赖关系
    parser_deps = subparsers.add_parser("deps", help="项目依赖关系分析")
    parser_deps.set_defaults(func=cmd_dep)
    parser_deps.add_argument("project", type=str, help='待分析依赖关系的项目名称')
    parser_deps.add_argument("-c", "--configuration", type=str, help='依赖配置参数compile、api、implementation等')
    parser_deps.add_argument("-d", "--dependency", type=str, help='查看特定的依赖，maven信息，比如：widget')

    # 更新代码
    parser_pull = subparsers.add_parser("pull", help="更新 项目代码")
    parser_pull.set_defaults(func=cmd_pull)

    # reset
    parser_reset = subparsers.add_parser("reset", help="重置 项目代码")
    parser_reset.set_defaults(func=cmd_reset)

    # 克隆
    parser_clone = subparsers.add_parser("clone", help="克隆子工程")
    parser_clone.set_defaults(func=cmd_clone)
    parser_clone.add_argument("-o", "--order", help='对子项目进行排序', action='store_true', default=False)
    parser_clone.add_argument("-a", "--allow_private", help='包含私有项目', action='store_true',
                              default=False)
    parser_clone.add_argument("-g", "--by_group", help='根据组进行克隆', action='append', default=[])
    parser_clone.add_argument("-p", "--by_project", help='根据项目名进行克隆', action='append', default=[])
    parser_clone.add_argument("-i", "--ignore_app", help='忽略App', action='store_true',
                              default=False)

    # 创建branch
    parser_branch = subparsers.add_parser("branch", help="创建分支")
    parser_branch.set_defaults(func=cmd_branch)
    parser_branch.add_argument("name", help='分支名称', action='store')
    parser_branch.add_argument("-p", "--push", help='是否推送到服务器', action='store_true', default=False)
    parser_branch.add_argument("-d", "--delete", help='删除分支', action='store_true', default=False)
    parser_branch.add_argument("-c", "--continue_branch", help='创建分支时如某项目已有该分支直接跳过，如不加此命令会打印错误日志不继续创建分支', action='store_true', default=False)
    parser_branch.add_argument("-i", "--include_work_space", help='是否创建workspace的分支', action='store_true', default=False)

    # 创建tag
    parser_tag = subparsers.add_parser("tag", help="打tag")
    parser_tag.set_defaults(func=cmd_tag)
    parser_tag.add_argument("name", help='tag名称', action='store')
    parser_tag.add_argument("-m", "--message", help='评论信息', action='store')
    parser_tag.add_argument("-d", "--delete", help='删除分支', action='store_true', default=False)

    # 仅用于Jenkins更新构建源码
    parser_apk = subparsers.add_parser("serv-update", help="打包for jenkins")
    parser_apk.set_defaults(func=cmd_update_project)
    parser_apk.add_argument("-o", "--order", help='对子项目进行排序', action='store_true', default=False)
    parser_apk.add_argument("-a", "--allow_private", help='包含私有项目', action='store_true',
                            default=False)
    parser_apk.add_argument("-g", "--by_group", help='根据组进行克隆', action='append', default=[])
    parser_apk.add_argument("-p", "--by_project", help='根据项目名进行克隆', action='append', default=[])
    parser_apk.add_argument("-i", "--ignore_app", help='忽略App', action='store_true',
                            default=False)

    # 操作apk文件
    parser_apk_ = subparsers.add_parser("deploy", help="开发部署工具")
    parser_apk_.set_defaults(func=cmd_deploy)
    parser_apk_.add_argument("-u", "--upload", help='上传apk到finder', action='store_true', default=False)
    parser_apk_.add_argument("-i", "--install", help='自动寻找apk，并安装到手机', action='store_true', default=False)
    # parser_apk_.add_argument("-di", "--debugInstall", help=u'构建Debug包，并安装到手机', action='store_true', default=False)
    # parser_apk_.add_argument("-ri", "--releaseInstall", help=u'构建Release包，并安装到手机', action='store_true', default=False)
    parser_apk_.add_argument("-app", "--app_deps_settings_module", help='根据setting中的配置的项目，对App部署依赖', action='store_true', default=False)
    parser_apk_.add_argument("-t", "--target_modules", help='对某些module部署依赖', nargs='*')
    parser_apk_.add_argument("-d", "--deps_modules", type=str, help='依赖某些module的源码', nargs='*')
    parser_apk_.add_argument("-dm", "--del_ex_setting_modules", help='删除非setting配置的其他module', action='store_true', default=False)
    parser_apk_.add_argument("-p", "--project_xml", help='修改xml中的某个module的branch、groups，例如把moduleA的配置修改成branch1、group1：deploy -p moduleA branch1 group1', type=str, nargs='*')
    parser_apk_.add_argument("-c", "--clone_project", help='下载项目管理系统中的project', type=int)

    parser_aar = subparsers.add_parser("aar", help="批量aar")
    parser_aar.set_defaults(func=cmd_compile_aar)
    parser_aar.add_argument('-s', "--setting", help='根据setting文件中module打aar', action='store_true', default=False)
    parser_aar.add_argument("-m", "--modules", help='多个module打包aar', nargs='+')
    parser_aar.add_argument('-v', "--version_index", type=int, default=3, choices=[1, 2, 3], help='自增版本索引【1大版本，2中间版本，3小版本】')
    parser_aar.add_argument('-nc', "--not_check", help='不检查，不排序，直接按照输入的顺序打包', action='store_true', default=False)
    #parser_aar.add_argument("-s", "--start_projects_xml", type=str, default='GFrameHttp', help=u'从某个module开始打包（根据projects.xml中的顺序）')

    parser_merge = subparsers.add_parser("merge", help="合并代码，默认setting配置的所有module")
    parser_merge.set_defaults(func=cmd_compile_merge)
    parser_merge.add_argument('branch', help='合并分支，暂不支持远程分支，如果各module的分支名不统一可以自行创建projects_merge.xml并配置各自分支', action='store')
    parser_merge.add_argument('-w', '--workspace_and_setting', help='setting配置的所有module + WorkSpace都参与合并', action='store_true', default=False)
    parser_merge.add_argument('-m', '--main_branch', type=str, help='主分支名名，适合工作空间还在需求分支上的场景（从需求分支自动切换到主分支，然后再合并代码），例如 apkfly featureBranch -m mergeDev -w')

    # 切换远程地址
    parser_remote = subparsers.add_parser("remote", help="远程地址")
    parser_remote.set_defaults(func=cmd_remote)
    parser_remote.add_argument("-s", "--set", help='切换远程地址Host, apkfly.py remote -s git@code.gome.inc', action='append', default=[])

    # 参数解析
    args = parser.parse_args()
    args.func(args)

