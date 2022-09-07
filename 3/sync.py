#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import requests
import os.path

'''
# 版本号同步
1. 同步AAR两种方式:
    1). 指定AAR key数组进行同步
    2). 按AAR_VERSION_SYNC_START/AAR_VERSION_SYNC_END同步
2. 版本同步范围, 支持多个
    1) 1-真快乐, 2-帮客, 3-帮帮, 4-Mini, 5-Pop

例: 
指定keys同步多个应用
./apkflyw sync -f gradle.properties -s 1,2 -p 1 -k AAR_MCP_GSHARE_VERSION,AAR_GSHARE_BUS_VERSION,AAR_VIEW_TRACKER_VERSION

按AAR_VERSION_SYNC_START/AAR_VERSION_SYNC_END标记位同步多个应用
./apkflyw sync -f gradle.properties -s 1,2 -p 1 

按AAR_VERSION_SYNC_START/AAR_VERSION_SYNC_END标记位同步单个应用
./apkflyw sync -f gradle.properties -s 1 -p 1 

# 查询服务器版本号
1. 查询仅支持单应用查询
2. 查询其他参数使用同同步命令

例：
./apkflyw sync -f gradle.properties -s 1 -p 1 -q
./apkflyw sync -f gradle.properties -s 1 -p -q 1 -k AAR_MCP_GSHARE_VERSION,AAR_GSHARE_BUS_VERSION,AAR_VIEW_TRACKER_VERSION
'''

# 版本同步服务接口地址
requrl = f"http://10.2.117.52:8000"

query_url = requrl + "/module/aar/version/query"
sync_url = requrl + "/module/aar/version/sync"

def sync_version(score, platform, keys, path, query):
    local_versions = readProperties(path)
    update_versions = []
    # 指定keys后只同步keys版本，否则比对本地全部版本
    if(keys is not None):
        if(len(keys) != 0):
            key_arr = keys.replace(" ", "").split(',')
            for line in local_versions:
                item = line.split("=")
                for key in key_arr:
                    if(item[0] == key):
                        update_versions.append(line)
    else:
        start_index = 0
        end_index = 0
        for item in local_versions:
            if(item.find("AAR_VERSION_SYNC_START") != -1):
                start_index = local_versions.index(item)
            if(item.find("AAR_VERSION_SYNC_END") != -1):
                end_index = local_versions.index(item)
        if(start_index < end_index):
            update_versions = local_versions[start_index + 1:end_index]
        else:
            raise Exception("版本文件内未配置AAR_VERSION_SYNC_START/AAR_VERSION_SYNC_END")

    try:
        if(query):
             # item_api是spyne的function名，itemData是传入参数名
            postdata = json.dumps({"itemData": update_versions, "score": score, "platform": platform})

            req = requests.post(query_url, data=postdata)
            json_data = json.loads(req.text)
            print("============查询结果============\n")
            for item in json_data:
                print(str(item))
        else:
            # item_api是spyne的function名，itemData是传入参数名
            postdata = json.dumps({"itemData": update_versions, "score": score, "platform": platform})

            req = requests.post(sync_url, data=postdata)
            print(req.text)
            json_data = json.loads(req.text)

            versions_dict = {}
            for item in local_versions:
                versions_dict[item.split("=")[0]] = item.split("=")[1]

            for key, value in versions_dict.items():
                for item in json_data:
                    dic = item
                    if(key in item):
                        server_version_array = dic[key].split("-")[0].split(".")
                        local_version_array = value.split("-")[0].split(".")
                        server_version_int_array = []
                        local_version_int_array = []
                        for item in server_version_array:
                            server_version_int_array.append(int(item))
                        for item in local_version_array:
                            local_version_int_array.append(int(item))

                        if(local_version_int_array < server_version_int_array):
                            # 客户端小于服务器版本号，覆盖本地
                            replace(path, key, value, dic[key])
                            continue
    except Exception as ex:
        raise Exception("同步接口请求异常: " + ex.args)

# 修改文件内容
def replace(path, index, original, amend):
    with open(path, "r", encoding="utf-8") as f:
        # readlines以列表的形式将文件读出
        lines = f.readlines()
        with open(path, "w", encoding="utf-8") as f_w:
            for line in lines:
                if index in line:
                    line = line.replace(original, amend)
                f_w.write(line)

# 读取本地gradle.properties信息
def readProperties(path):
    config = []
    # 如未配置gradle.properties，取根目录默认文件
    if(os.path.exists(path)):
        file = open(path, 'r', encoding="utf-8")
        data = file.readlines()
        file.close()

        for line in data:
            line = line.replace(" ", "").rstrip("\n")
            if(line.find("=") != -1 and line.find("#") == -1 and line.find("VERSION") != -1):
                config.append(line)

    return config

if __name__ == '__main__':
    sync_version("1", "1", None, '/Users/gome007/Gome/workspace/OnlyApp/GWorkDevOnlyApp/gradle.properties', None)