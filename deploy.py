#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import platform
import subprocess

# 解决win命令行乱码问题
reload(sys)
sys.setdefaultencoding('utf-8')
##########################################

file_build_gradle = "build.gradle"
dir_current = os.path.abspath(".")
file_settings = os.path.join(dir_current, "settings.gradle")
file_build = os.path.join(dir_current, file_build_gradle)
path_build_gome_core_deps = os.path.join('deps', 'coredeps.gradle')

def exclude_aar_dep_source(tModule, dModules):
    print u'开始部署依赖，排除%s中的%s AAR依赖，直接依赖其源码' % (tModule, ",".join(dModules))
    # 先检测一下，module是否在setting文件中

    # 1、settings.gradle中include的所有module
    includeModules = getIncludeModule()
    print u"1、include的所有module配置读取完毕"

    if len(includeModules) < 2:
        print u'出错警告： setting.gradle 配置超过2个module再来哦'
        return

    if tModule not in includeModules:
        print u'出错警告： 请确保%s 已配置在setting.gradle' % (tModule)
        return

    for dm in dModules:
        if dm not in includeModules:
            print u'出错警告： 请确保%s 已配置在setting.gradle' % ( ",".join(dModules))
            return

    # 2、module的maven信息，并include的module在ext.deps[ ]中打开依赖
    moduleInfos = getModuleMavenInfo(includeModules)
    print u"2、includeModule的maven信息读取完毕，并在ext.deps[ ]中打开依赖"

    # 3、排除aar,依赖源码
    print u"3、开始为子工程加入Dep Excludes"
    mainModuleInfo = None
    sourceModuleInfos = []
    for m in moduleInfos:
        if m.name == tModule:
            mainModuleInfo = m
        elif m.name in dModules:
            sourceModuleInfos.append(m)
    if mainModuleInfo and len(sourceModuleInfos) == len(dModules):
        writeConfigurationsExcludesAndCompileToBuildGradle(mainModuleInfo, sourceModuleInfos)
    else:
        print u'部署err'

    print u'部署完毕'

def deployMainAppDeps():
    print u'开始部署依赖'
    # 读取setting中的include 项目
    # 找到项目对应的maven id
    # 修改主项目中deps.gradle中的配置（根据gradle.properties中变量判断是哪个app, gome, bang, mini）
    # 添加configurations排除依赖
    # 添加项目compile依赖
    # 关闭debug下的混淆开关

    print u"1、读取settings.gradle中include的所有module"
    includeModules = getIncludeModule()
    if len(includeModules) < 2:
        print u'出错警告： setting.gradle 配置超过2个module再来哦'
        return

    print u"2、从build.gradle读取module的maven信息，并把include的module在其ext.deps[ ]中打开依赖"
    moduleInfos = getModuleMavenInfo(includeModules)

    mainModuleName = getMainModule(includeModules)
    print u"3、解析到主工程 %s" % mainModuleName

    # 主工程信息
    mainModuleInfo = ModuleInfo(mainModuleName, '', '', '')

    print u"4、把主工程上次部署的（依赖、排除）reset"
    os.popen("cd %s && git checkout %s" % (mainModuleName, mainModuleInfo.getBuildFile()))

    print u"5、开始为主工程 %s build.gradle加入部署依赖" % mainModuleName
    writeConfigurationsExcludesAndCompileToBuildGradle(mainModuleInfo, moduleInfos)

    print u"部署完毕"

def getMainModule(includeModules):
    for includeModule in includeModules:
        with open(os.path.join(dir_current, includeModule, file_build_gradle), "r") as file:
            for line in file:
                l = line.replace(' ', '')
                if l.startswith("applyplugin:'com.android.application'"):
                    return includeModule

def getIncludeModule():
    """获取include中的所有module
    :return:
    """
    includeModules = []
    for line in open(file_settings):
        line = line.strip()
        if not (line == '' or line.startswith('//') or line.startswith('/') or line.startswith('*')):
            ls = line.split('\"')
            moduleName = ls[1].replace(':', '')
            includeModules.append(moduleName)
    return includeModules

def printRed(message):
    print "\033[1;31m%s\033[0m" % message

def getModuleMavenInfo(includeModules):
    """获取module的maven信息
    :param includeModules:
    :return:
    """
    moduleInfos = []
    start = False
    with open(file_build, "r") as file, open("%s.bak" % file_build, "w") as file_bak:
        for line in file:

            # 只解析ext.deps = [ ] 之中的配置，也排除注释的代码
            line_ = line.replace(' ', '')
            if not (line == "" or line_.startswith('//') or line_.startswith('/') or line_.startswith('*')):
                if line_.startswith('ext.deps'):
                    start = True
                    file_bak.write(line)
                    continue
                elif line_.startswith(']') and start:
                    start = False

                if  start:
                    # 首先匹配该行代码是否包含include的module之一
                    isMatch = False
                    curModule = ""
                    depsModule = ""
                    for includeModule in includeModules:
                        # 第一个in判断是匹配开头
                        # 第二个in判断是匹配中间的project(':xxx')，这个目前是个bug，compile的module是真实的而不是ext.deps中配置的，这样导致compile找不到配置
                        # 这里不能直接用line包含includeModule，应为module有MIm、MImlibrary这样的，如果只include MIm，MImlibrary也会被修改，所以得加上: 一块匹配
                        if (includeModule + ":") in line_:
                            isMatch = True
                            curModule = includeModule
                            break
                        elif (":" + includeModule) in line_:
                            isMatch = True
                            curModule = includeModule
                            # 分割，取deps别名
                            lines = line_.split(':', 1)
                            depsModule = lines[0]
                            break

                    if isMatch:
                        #1、把依赖本地module开关打开
                        depTag = 'rootProject.ext.proDeps'
                        depTag2 = "%s:%s?project"
                        if depTag in line:
                            # 把依赖开关tag替换为true
                            line = line.replace(depTag, 'true', 1)
                        else:
                            # 未检测到依赖开关配置
                            # 再次检查是否已把开关配置写成false，如果是则修改为true
                            if line_.startswith(depTag2 % (includeModule, 'false')):
                                line = line_.replace(depTag2 % (includeModule, 'false'), depTag2 % (includeModule, 'true'), 1)
                            elif not line_.startswith(depTag2 % (includeModule, 'true')):
                                # 有bug，有的不是这个关键字而直接写的 false
                                printRed(u'%s项目没有打开源码依赖开关' % includeModule)

                        # 2、马上进入解析 ext.deps[ ] 中的配置
                        # 从build.gradle的deps配置中查出module的maven信息
                        matchObj = re.match(u".*'((com|cn)\.gome\.[^']*)'", line, re.M|re.I)
                        if matchObj:
                            ga = matchObj.group(1)
                            gas = ga.split(':')
                            module = ModuleInfo(curModule, gas[0], gas[1], depsModule)
                            moduleInfos.append(module)
            file_bak.write(line)

        file.close()
        file_bak.close()
        # 把新文件覆盖现文件
        os.remove(file_build)
        os.rename("%s.bak" % file_build, file_build)

        # 做个验证，
        if len(includeModules) - 1 > len(moduleInfos):
            printRed(u"获取setting中module的maven信息出错 - getModuleMavenInfo - 请检查")
    return moduleInfos

def writeConfigurationsExcludesAndCompileToBuildGradle(moule, moduleInfos):
    """部署配置(ConfigurationsExcludes、Compile)到build.gradle
    :param moule: 配置此module中的依赖
    :param moduleInfos: 本工程include的module信息
    :return:
    """
    pass
    moduleBuildGradle = moule.getBuildFile()
    print u"    找到build.gradle文件: %s" % moduleBuildGradle
    moduleBuildGradle_bak = moduleBuildGradle + '.bak'
    moduleBuildGradle_new = moduleBuildGradle + '.new'

    isWriteCompileConfig = False
    with open(moduleBuildGradle_new, "w") as new_file:
        # 添加排除配置
        writeExcludesToBuildGradle(new_file, moule, moduleInfos)
        print u"    添加排除配置完毕"
        for line in open(moduleBuildGradle):
            # 先把本行数据写入
            new_file.write(line)
            # 添加依赖配置
            if line.strip().startswith('dependencies'):
                # 写入compile
                writeCompileToBuildGradle(new_file, moule, moduleInfos)
                isWriteCompileConfig = True
                print u"    写入compile完毕"
    if not isWriteCompileConfig:
        printRed(u"    compile配置写入出错, 请检查")

    new_file.close()
    # 把目前的build文件备份，新生成的build文件替换原文件
    # if os.path.exists(moduleBuildGradle_bak): os.remove(moduleBuildGradle_bak)
    # os.rename(moduleBuildGradle, moduleBuildGradle_bak)
    if os.path.exists(moduleBuildGradle): os.remove(moduleBuildGradle)
    os.rename(moduleBuildGradle_new, moduleBuildGradle)

def writeExcludesToBuildGradle(new_file, curModule, moduleInfos):
    """往build.gradle中写入配置
     configurations{
       compile.exclude group: '', module: ''
     }
    :param new_file:
    :param curModule:
    :param moduleInfos: 本工程include的module信息
    :return:
    """
    configurations = []
    configurations.append('configurations{')
    for module in moduleInfos:
        if curModule.name != module.name:# 排除自己的maven配置
            configurations.append(module.compileExclude)
    configurations.append('}')
    new_file.writelines([configuration + '\n' for configuration in configurations])

def writeCompileToBuildGradle(new_file, curModule, moduleInfos):
    """往build.gradle中写入配置
    compile(deps.xxx){
      transitive = true
    }
    :param new_file:
    :param curModule:
    :param moduleInfos:
    :return:
    """
    compiles = []
    for module in moduleInfos:
        if curModule.name != module.name:# 排除自己的compile配置
            compiles.append(module.deps)
    new_file.writelines([compile + '\n' for compile in compiles])

# module 的信息（名字、groupId、artifactId）
class ModuleInfo(object):
    def __init__(self, name, groupId, artifactId, depsName):
        self.name = name
        self.groupId = groupId
        self.artifactId = artifactId
        self.depsName = depsName
        self.deps = '    compile (deps.%s){\n        transitive = true\n    }' % (name if(depsName == None or depsName == '') else depsName)
        self.compileExclude = "    compile.exclude group: '%s', module: '%s'" % (groupId, artifactId)
        self.exclude = "        exclude group: '%s', module: '%s'" % (groupId, artifactId)

    def getBuildFile(self):
        if self.groupId == '':
            # 本modulInfo对象为主工程 - 真快乐、帮帮、极简使用coredeps.gradle，其他app使用build.gradle
            coreDepsPath = os.path.join(dir_current, self.name, path_build_gome_core_deps)
            if os.path.exists(coreDepsPath):
                return coreDepsPath
            return os.path.join(dir_current, self.name, file_build_gradle)
        else:
            return os.path.join(dir_current, self.name, file_build_gradle)

    def __str__(self):
        return 'name:%s  groupId:%s  artifactId:%s  \ndeps:\n%s  \nexclude:\n%s' % (self.name, self.groupId, self.artifactId, self.deps, self.exclude)

#-----------------------------------------------------------------install apk----------------------------------------------------------------------------------------------------------------

# 寻找apk的特殊路径标示
APK_SPECIAL_PATH = os.path.join('build', 'outputs', 'apk')

def installApk():
    apkPath = findApkPath()
    if os.path.exists(apkPath):
        print '1. Start install apk: ' + apkPath
        install_output = os.popen("adb install -r %s" % (apkPath)).read()
        print install_output
        if 'Success' in install_output:
            time.sleep(1)# 延迟一秒安装app，兼容启动失败bug
            startApp(apkPath)
        else:
            print 'install fail'
    else:
        print 'Not find apk, check the exec cmd directory is in WorkSpace --- Chinglish !!!'

# 找到要操作的apk
def findApkPath():
    hasApkPath = False
    rootDir = os.listdir('.')
    for childDir in rootDir:
        if os.path.exists(os.path.join(childDir, APK_SPECIAL_PATH)):
            apkDir = os.path.join(childDir, APK_SPECIAL_PATH)
            hasApkPath = True
            break
    if hasApkPath:
        apks = []
        findApkPathByDir(apkDir, apks)
        apkNum = len(apks)
        if apkNum == 0:
            print 'Not find apk in path: ' + apkDir
            return ''
        elif apkNum == 1:
            return apks[0]
        else:
            print 'Apk num > 1, please choose one:'
            print '------------------------------'
            for i in range(apkNum):
                print '%s. %s' % (i + 1, apks[i])
            print '------------------------------'
            num = getNum(apkNum)
            return apks[num - 1]
    else:
        return ''


# 提示用户选择一个数字
def getNum(numRang):
    try:
        inputNum = int(raw_input('please input num: '))
    except NameError and ValueError:
        print 'input err, num rang: (1 - %s)' % numRang
        return getNum(numRang)
    else:
        if inputNum not in range(1, numRang + 1):
            print 'input err, num rang: (1 - %s)' % numRang
            return getNum(numRang)
        else:
            return inputNum

# 寻找apkDir目录下的所有apk文件
def findApkPathByDir(apkDir, apkList):
    dir = os.listdir(apkDir)
    for p in dir:
        absP = os.path.join(apkDir, p)
        if os.path.isdir(absP):
            findApkPathByDir(absP, apkList)
        elif absP.endswith('.apk'):
            apkList.append(absP)


# 启动app
def startApp(apkPath):
    # 1、先找到aapt命令
    # 2、通过aapt命令查询包名和launch页信息
    print '2. Use aapt cmd, find app package and launch'
    dump_output = os.popen("%s dump badging %s" % ("aapt", apkPath))
    dump_output_lines = dump_output.readlines()
    package = ""
    launch = ""
    for line in dump_output_lines:
        if line.startswith("package:"):
            # print line # package: name='cn.gome.bangbang' versionCode='206' versionName='8.0.6'
            d = splitKV(line)
            try:
                package = d['name']
            except KeyError:
                print 'package find fail'
        if line.startswith("launchable-activity:") and launch == "":
            # print line # launchable-activity: name='com.gome.ecmall.home.LaunchActivity'
            d = splitKV(line)
            try:
                launch = d['name']
            except KeyError:
                print 'launchable-activity find fail'
    if package == "" or launch == "":
        print 'find app info fail'
        return
    #/3、再通过adb命令启动app
    print u'3. Start open app...'
    start_output = os.popen("adb shell am start -n %s/%s" % (package, launch))
    print start_output.read()
    print u'如未启动app，请检查手机设置，允许app后台启动'

# 分解aapt查找出的信息，组装成字典
def splitKV(line):
    d = {}
    kvs = line.split(' ')
    for kvStr in kvs:
        if '=' in kvStr:
            kv = kvStr.split('=')
            d[kv[0]] = kv[1].replace('\'', '')
    return d

#----------------------------------------------------------upload apk-----------------------------------------------------------------------

# 上传finder配置
UPLOAD_ACCOUNT = 'gome'
UPLOAD_PW = 'jdkfjkd'
UPLOAD_URL = 'http://10.115.3.134:8085/upload'

# apk上传到finder的这个目录中 ------  可修改  ------
JOB_NAME = 'Location-App-Script'

# 在线生成二维码api
QRCODE_API = 'https://api.qrserver.com/v1/create-qr-code/?data='
# 二维码缓存目录
QR_CODE_IMG_CACHE_PAHT = os.path.join('.idea', 'caches', 'qr.png')

def uploadApk():
    apkPath = findApkPath()
    if os.path.exists(apkPath):
        print '1.Successful find apk, start upload it: ' + apkPath
        downloadUrl = uploadApkByPath(apkPath)
        if len(downloadUrl) > 1 and downloadUrl.startswith('http'):
            print '2.Upload apk succeeded, download url:'
            print '  %s' % downloadUrl
            result = generateQRCode(downloadUrl)
            if result == 1:
                print "3.QR code generate succeeded, from 'python qrcode lib'"
            elif result == 2:
                print "3.QR code generate succeeded, from 'online api'"
                print '  QR code path: %s' % QR_CODE_IMG_CACHE_PAHT
            else:
                print '3.QR code generate failed'
        else:
            print '2.Upload apk failed, %s!' % downloadUrl
    else:
        print 'Not find apk, check the exec cmd directory is in WorkSpace --- Chinglish !!!'


# 系统打开文件
def showFile(path):
    userPlatform = platform.system()					# 获取操作系统
    if userPlatform == 'Darwin':						# Mac
        subprocess.call(['open', path])
    elif userPlatform == 'Linux':						# Linux
        subprocess.call(['xdg-open', path])
    else:												# Windows
        os.startfile(path)

# 生成二维码
def generateQRCode(text):
    try:
        import qrcode
        img = qrcode.make(data=text) # 生成二维码
        img.show() # 直接显示二维码
        # img.save("baidu.jpg") # 保存二维码为文件
        return 1
    except ImportError:
        print "Please install python qrcode lib, can generate QR code !"
        pass

    try:
        import requests
        response = requests.get(QRCODE_API + text)
        if response.status_code == 200:
            # 先判断缓存目录是否存在
            if not os.path.exists(os.path.dirname(QR_CODE_IMG_CACHE_PAHT)):
                os.mkdir(os.path.dirname(QR_CODE_IMG_CACHE_PAHT))
            # 保存二维码
            with open(QR_CODE_IMG_CACHE_PAHT,'wb')as img:
                img.write(response.content)
            # 显示二维码
            showFile(QR_CODE_IMG_CACHE_PAHT)
            return 2
        else:
            return 0
    except ImportError:
        print "Please install python requests lib !"
        return 0

# 上传apk
def uploadApkByPath(apkPath):
    # 上传到Finder中后的名字，如：20200521-10:25:00.apk
    apkFile = open(apkPath, 'rb')
    upApkName = os.path.basename(apkFile.name).replace('.apk', '%s%s.apk' % ('-', time.strftime("%Y-%m-%d-%H:%M:%S", time.localtime())))
    files = {
        'file': (upApkName, apkFile),
        'job': (None, JOB_NAME),
        'platform': (None, 'android'),
    }

    try:
        import requests
        response = requests.post(UPLOAD_URL, files=files, auth=(UPLOAD_ACCOUNT, UPLOAD_PW))
        if response.status_code == 200:
            return response.text
        else:
            return ''
    except ImportError:
        print "Please install python requests lib !"
        return ''


#---------------------------------------------------------- 删除module文件 -----------------------------------------------------------------------

def deleteExIncludeModule():
    inM = getIncludeModule()
    rootFiles = os.listdir('.')
    for f in rootFiles:
        if f not in inM and os.path.exists(os.path.join(f, file_build_gradle)):
            remove_dir(f)

def remove_dir(dir):
    """
    删除文件夹
    :param dir: 路径
    :return:
    """
    dir = dir.replace('\\', '/')
    if (os.path.isdir(dir)):
        for p in os.listdir(dir):
            remove_dir(os.path.join(dir, p))
        if (os.path.exists(dir)):
            os.rmdir(dir)
    else:
        if (os.path.exists(dir)):
            os.remove(dir)
