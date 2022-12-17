#!/usr/bin/env python
# -*- coding:utf-8 -*-

import os
import sys
import socket
import time
from urllib.parse import ParseResultBytes
import tcping

from argparse import ArgumentParser, RawTextHelpFormatter
from os import path, environ, stat, name as os_name
from json import load as loadjson, dump as dumpjson
from tempfile import gettempdir

from util.cache import Cache

__version__ = "${BUILD_SOURCEBRANCHNAME}@${BUILD_DATE}"  # CI 时会被Tag替换
__description__ = "automatically update DNS records to dynamic local IP [自动更新DNS记录指向本地IP]"
__doc__ = """
ddns[%s]
(i) homepage or docs [文档主页]: https://ddns.newfuture.cc/
(?) issues or bugs [问题和帮助]: https://github.com/NewFuture/DDNS/issues
Copyright (c) New Future (MIT License)
""" % (__version__)


def get_config(key=None, default=None, path="config.json"):
    """
    读取配置
    """
    if not hasattr(get_config, "config"):
        try:
            with open(path) as configfile:
                get_config.config = loadjson(configfile)
                get_config.time = stat(path).st_mtime
        except IOError:
            with open(path, 'w') as configfile:
                configure = {
                    "id": "YOUR ID or EMAIL for DNS Provider",
                    "token": "YOUR TOKEN or KEY for DNS Provider",
                    "dns": "dnspod",
                    "ipv4": "",
                    "ipv6": "",
                    "index4": "default",
                    "index6": "default",
                    "ttl": None,
                    "proxy": None,
                    "debug": False,
                }
                dumpjson(configure, configfile, indent=2, sort_keys=True)
            sys.stdout.write(
                "New template configure file `%s` is generated.\n" % path)
            sys.exit(1)
        except:
            sys.exit('fail to load config from file: %s' % path)
    if key:
        return get_config.config.get(key, default)
    else:
        return get_config.config


def PingPort(ip, port):
    # try:
    #    socket.gethostbyaddr(ip)
    #    return True
    # except socket.herror:
    #    print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - 网络故障")
    #    return False
    try:
        Pingclass = tcping.Ping(ip, port, 1)
        Pingclass.ping(get_config('pings'))
        return Pingclass._failed
    except:
        return get_config('pings')


def PingDNS(address):
    """
    ping 主备网络
    """
    try:
        #result = os.system("ping www.baidu.com -n 3 -w 1")
        result = os.system("ping %s -n 3 -w 1" % (address))
        if result != 0:
            print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - 网络故障")
            return False
        else:
            return True
    except:
        return False

def Resolve(address):
    try:
        return socket.gethostbyname(address)
    except:
        print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - " + address + "解析失败")

def update_ip(dns, domain, type, value, cloudflare):
    """
    更新IP失败重试
    """
    retry = 0
    while retry < 3:
        try:
            if dns.update_record(domain, value, type, cloudflare):
                return True
        except:
            if retry < 3:
                retry = retry + 1
            else:
                return False


def main():

    # 日志级别
    ################################################
    #basicConfig(level="DEBUG")

    # 读入传参
    ################################################
    parser = ArgumentParser(description=__description__,epilog=__doc__, formatter_class=RawTextHelpFormatter)
    parser.add_argument('-v', '--version',action='version', version=__version__)
    parser.add_argument('-c', '--config',default="config.json", help="配置文件路径")
    parser.add_argument('-a', '--cache',default="ddns.cache", help="缓存文件路径")
    config_file = parser.parse_args().config
    get_config(path=config_file)
    CACHE_FILE = parser.parse_args().cache

    # 声明DNS更新类
    ################################################
    dns_provider = str(get_config('dns', 'dnspod').lower())  # dns_provider是类名称
    dns = getattr(__import__('dns', fromlist=[dns_provider]), dns_provider)  # dns是类

    # 载入配置
    ################################################
    dns.Config.ID = get_config('id')
    dns.Config.TOKEN = get_config('token')
    dns.Config.TTL = get_config('ttl')

    # 建立缓存，配置文件修改则重建
    ################################################
    cache = Cache(CACHE_FILE)
    if get_config.time >= cache.time:
        cache.clear()
        cache["dns"] = {}
        cache["ddns"] = ""
        print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - 检测到配置文件改动，清空缓存")

    # 预读缓存到内存
    ################################################
    prefetch = {}
    prefetch["dns"] = cache["dns"]
    prefetch["ddns"] = cache["ddns"]

    # IF1 检查网络是否正常
    # YES 解析服务器域名 -> IF2
    ################################################
    if PingPort("www.baidu.com", 443) < get_config('pings'):
        # 判断解析域名缓存是否为空，为空触发解析（len(prefetch["dns"])多一个备用服务器）
        # 将解析的地址写入缓存，后续直接验证IP是否可用不可用再进行解析，避免频繁解析。
        if not prefetch["dns"] or len(prefetch["dns"]) < len(get_config('addresslis4')):
            prefetch["dns"] = {}
            prefetch["ddns"] = ""
            #解析备用服务器
            try:
                prefetch["dns"][get_config('backser')] = socket.gethostbyname(get_config('backser'))
            except:
                print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - " + get_config('backser') + "解析失败")
            # 遍历解析服务器
            for Lisdata in get_config('addresslis4'):
                try:
                    prefetch["dns"][Lisdata["name"]] = socket.gethostbyname(Lisdata["name"])
                except:
                    print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - " + Lisdata["name"] + "解析失败")
            #将解析结果写入缓存
            cache["dns"] = prefetch["dns"]
            cache.write()
        #若所有域名都解析失败判定为异常
        if len(prefetch["dns"]) == 0:
            dns_check = False
            print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - 所有服务器解析失败")
        else:
            dns_check = True

        ## IF2 缓存是否有效、缓存内IP是否存在
        ## YES 触发更新 -> IF3
        ################################################
        update = False
        if dns_check and prefetch["ddns"]:
            try:
                # 缓存的DDNS值（域名记录值）等于“backser解析后的地址”或“tunnelscname的值”直接触发更新
                if prefetch["ddns"] == prefetch["dns"][(get_config('backser'))] or prefetch["ddns"] == get_config('tunnelscname'):
                    update = True
                else:
                    # 缓存的DDNS值测试连接失败次数超过pings设定的值时触发更新
                    if PingPort(prefetch["ddns"], get_config('port')) >= get_config('pings'):
                        update = True
            except:
                update = True

        ## IF3 域名解析正常、没有缓存、更新标志位为启用
        ## YES 进入IP筛选程序 -> IF4
        ################################################
        if dns_check and (not prefetch["ddns"] or update):
            Fadd = []
            ipdat = []
            dictlen = 0
            for key, values in prefetch["dns"].items():
                #列表嵌套字典
                ipdat.append({key: values})
                ipdat[dictlen]["dorps"] = 0
                ipdat[dictlen]["times"] = 0
                try:
                    #测试连接
                    Pingclass = tcping.Ping(values, get_config('port'), 2)
                    Pingclass.ping(get_config('pings'))
                    #连接错误数
                    ipdat[dictlen]["dorps"] = Pingclass._failed
                    #连接时间，取平均数
                    ipdat[dictlen]["times"] = round(
                        sum(Pingclass._conn_times)/len(Pingclass._conn_times), 2)
                #运行出错直接判定为连接失败
                except:
                    ipdat[dictlen]["dorps"] = get_config('pings')
                #将连接失败次数X1000毫秒例入排序
                if ipdat[dictlen]["dorps"] > 0:
                    ipdat[dictlen]["times"] += 1000*Pingclass._failed
                #将连接失败的域名重新更新IP地址
                if ipdat[dictlen]["dorps"] >= get_config('pings'):
                    try:
                        prefetch["dns"][key] = socket.gethostbyname(key)
                        #将重新解析的结果写入缓存
                        cache["dns"] = prefetch["dns"]
                        cache.write()
                    except:
                        print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - " + key + "二次解析失败")
                #循环计位
                dictlen += 1
            #排序得出最快、出错最低的IP
            Fadd = sorted(ipdat, key=lambda i: (i['dorps'], i['times']))[0]


            # IF4 验证返回的IP并更新域名
            # YES 更新域名
            ################################################
            if Fadd['dorps'] < get_config('pings'):
                FastIP = list(Fadd.values())[0]
                domain = get_config('ipv4')
                if FastIP != prefetch["ddns"]:
                    cache["ddns"] = FastIP
                    if update_ip(dns, domain, "A", FastIP, False):
                        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + " - 更新地址：" + domain + "(" + FastIP + ")")
                    else:
                        cache["ddns"] = ""
                        print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - DDNS更新失败")
            #所有中转服务器不可用，切换到 CloudFlare Tunnels 地址
            else:
                cname = get_config('tunnelscname')
                domain = get_config('ipv4')
                if cname != prefetch["ddns"]:
                    cache["ddns"] = cname
                    if update_ip(dns, domain, "CNAME", cname, True):
                        print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())) + " - 更新地址：" + domain + "(" + cname + ")")
                    else:
                        cache["ddns"] = ""
                        print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - DDNS更新失败")
    #IF1-ERR
    else:
        print(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())) + " - 网络检查未通过")

    #结束
    pass
    return 0
    
if __name__ == '__main__':
    main()
    sys.exit(0)