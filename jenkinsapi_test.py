#! /usr/bin/env python
# -*- coding: utf-8 -*-
# __author__ = "mxl"

import jenkinsapi
from jenkinsapi.jenkins import Jenkins
from jenkinsapi.build import Build

def get_server_instance():
    server = Jenkins("http://10.115.3.136:8080/jenkins", username = 'qiudongchao', password = 'hyxf1988', useCrumb = True)
    return server

def get_job_details():
    server = get_server_instance()
    for j in server.get_jobs():
        job_instance = server.get_job(j[0])
        print 'Job Name:%s' %(job_instance.name)
        print 'Job Description:%s' %(job_instance.get_description())
        print 'Is Job running:%s' %(job_instance.is_running())
        print 'Is Job enabled:%s' %(job_instance.is_enabled())
        print '-----------------------'

def build_job(job_name):
    server = get_server_instance()
    if (server.has_job(job_name)):
        job_instance = server.get_job(job_name)
        print 'Is Job running:%s' %(job_instance.is_running())
        server.build_job(job_name)
        print 'Job build add Queue !'

def stop_job(job_name):
    server = get_server_instance()
    if (server.has_job(job_name)):
        job_instance = server.get_job(job_name)
        url = job_instance.__dict__['_data']['lastBuild']['url']
        number = job_instance.__dict__['_data']['lastBuild']['number']
        print url
        print number
        build = Build(url, number, job_instance)
        print 'Is Job running:%s' %(build.is_running())
        result = build.stop()
        print 'build stop result:%s' %(result)

if __name__ == '__main__':
    print get_server_instance().version
    # build_job('GomeStaff-master')
    # stop_job('GomeStaff-master')


# 可以通过 crul 直接build，每个用户Token不一样
# curl -X POST 'http://qiudongchao:ba1812a1861e5d33d48a602ceb4693aa@10.115.3.136:8080/jenkins/job/GomeStaff-master/build'

# 获取useCrumb
# curl -H "Host: 10.115.3.136:8080"
# -H "Accept: */*"
# -H "User-Agent: python-requests/2.26.0"
# -H "Authorization: Basic cWl1ZG9uZ2NoYW86aHl4ZjE5ODg="
# --compressed "http://10.115.3.136:8080/jenkins/crumbIssuer/api/python"



# JenkinsApi
# https://jenkinsapi.readthedocs.io/en/latest/api.html

# Python Jenkins
# https://python-jenkins.readthedocs.io/en/latest/api.html