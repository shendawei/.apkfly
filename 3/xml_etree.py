#!/usr/bin/env python3
# encoding: utf-8

import xml.etree.ElementTree as ET


def modify_project_xml(ps, project_xml_path):
    """
    修改project.xml
    :param ps:
    :param project_xml_path:
    :return:
    """

    tree = ET.parse(project_xml_path)
    root = tree.getroot()

    for p_xml in root.iter('project'):
        for p in ps:
            if p_xml.get('url').endswith('/%s.git' % p[0]):
                # 命中一个project
                print('修改%s开始' % p[0])
                print(p_xml.attrib)
                p_xml.set('branch', p[1])
                p_xml.set('groups', p[2])
                print(p_xml.attrib)
                print('修改%s完毕' % p[0])
                print('-' * 50)

    # 覆盖原文件
    tree.write(project_xml_path)
    print('覆盖原文件完毕')
