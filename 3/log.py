
def d(message):
    # 普通
    print(message)

def i(message):
    # 绿色
    print("\033[0;36m%s\033[0m" % message)

def w(message):
    # 黄色
    print("\033[0;33m%s\033[0m" % message)

def e(message):
    # 红色
    print("\033[0;31m%s\033[0m" % message)