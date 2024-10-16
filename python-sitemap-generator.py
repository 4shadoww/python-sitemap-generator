#!/usr/bin/env python3

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# Python Sitemap Generator
# Version: 0.6

# Authors
# Aleksei Tcelishchev
# Github: https://github.com/casualuser/python-sitemap-generator
# Przemek Wiejak @ przemek@wiejak.us
# GitHub: https://github.com/wiejakp/python-sitemap-generator
# Noa-Emil Nissinen
# Gitlab: https://gitlab.com/4shadoww/python-sitemap-generator

import threading
import time
import sys
from urllib.request import urlopen
from urllib.request import Request
from urllib.request import HTTPError
from urllib.parse import urljoin
from urllib.parse import urlparse
import email.utils as eut

from pprint import pprint

# from var_dump import var_dump
from lxml import etree
from lxml.html.soupparser import fromstring

# sudo apt-get install python-beautifulsoup
# sudo apt-get install python-pip
# sudo apt-get install python3-pip
# pip install setuptools
# pip install var_dump

queue = []
checked = []
threads = []
types = "text/html"

link_threads = []

# MaxThreads = 30
# MaxSubThreads = 10

# adjust to your liking
MaxThreads = 10
MaxSubThreads = 10

InitialURL = None
InitialURLInfo = None
InitialURLLen  = None
InitialURLNetloc  = None
InitialURLScheme  = None
InitialURLBase  = None

run_ini = None
run_end = None
run_dif = None

filename = "sitemap.xml"

request_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Connection": "keep-alive",
}

netloc_prefix_str = "www."
netloc_prefix_len = len(netloc_prefix_str)

def init_url(url):
    global InitialURL
    global InitialURLInfo
    global InitialURLLen
    global InitialURLNetloc
    global InitialURLScheme
    global InitialURLBase

    InitialURL = url

    InitialURLInfo = urlparse(InitialURL)
    InitialURLLen = len(InitialURL.split("/"))
    InitialURLNetloc = InitialURLInfo.netloc
    InitialURLScheme = InitialURLInfo.scheme
    InitialURLBase = InitialURLScheme + "://" + InitialURLNetloc

    if InitialURLNetloc.startswith(netloc_prefix_str):
        InitialURLNetloc = InitialURLNetloc[netloc_prefix_len:]


class RunCrawler(threading.Thread):
    # crawler start
    run_ini = time.time()
    run_end = None
    run_dif = None

    def __init__(self, url):
        threading.Thread.__init__(self)

        ProcessURL(url)

        self.start()

    def run(self):
        run = True

        while run:
            for index, thread in enumerate(threads):
                if thread.is_alive() is False:
                    del threads[index]

            for index, thread in enumerate(link_threads):
                if thread.is_alive() is False:
                    del link_threads[index]

            for index, obj in enumerate(queue):
                if len(threads) < MaxThreads:
                    thread = Crawl(index, obj)
                    threads.append(thread)

                    del queue[index]
                else:
                    break

            if len(queue) == 0 and len(threads) == 0 and len(link_threads) == 0:
                run = False

                self.done()
            else:
                print(
                    "Threads: ",
                    len(threads),
                    " Queue: ",
                    len(queue),
                    " Checked: ",
                    len(checked),
                    " Link Threads: ",
                    len(link_threads),
                )
                time.sleep(1)

    def done(self):
        print("Checked: ", len(checked))
        print("Running XML Generator...")

        # Running sitemap-generating script
        Sitemap()

        self.run_end = time.time()
        self.run_dif = self.run_end - self.run_ini

        print(self.run_dif)


class Sitemap:
    urlset = None
    encoding = "UTF-8"
    xmlns = "http://www.sitemaps.org/schemas/sitemap/0.9"

    def __init__(self):
        self.root()
        self.children()
        self.xml()

    def done(self):
        print("Done")

    def root(self):
        self.urlset = etree.Element("urlset")
        self.urlset.attrib["xmlns"] = self.xmlns

    def children(self):
        for _, obj in enumerate(checked):
            url = etree.Element("url")
            loc = etree.Element("loc")
            lastmod = etree.Element("lastmod")
            changefreq = etree.Element("changefreq")
            priority = etree.Element("priority")

            loc.text = obj["url"]
            lastmod_info = None
            lastmod_header = None
            lastmod.text = None

            if hasattr(obj["obj"], "info"):
                lastmod_info = obj["obj"].info()
                lastmod_header = lastmod_info["Last-Modified"]

            # check if 'Last-Modified' header exists
            if lastmod_header is not None:
                lastmod.text = FormatDate(lastmod_header)

            if loc.text is not None:
                url.append(loc)

            if lastmod.text is not None:
                url.append(lastmod)

            if changefreq.text is not None:
                url.append(changefreq)

            if priority.text is not None:
                url.append(priority)

            self.urlset.append(url)

    def xml(self):
        f = open(filename, "w")
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        print(
            etree.tostring(
                self.urlset, pretty_print=True, encoding="unicode", method="xml"
            ),
            file=f,
        )
        f.close()

        print("Sitemap saved in: ", filename)


class Crawl(threading.Thread):
    def __init__(self, index, obj):
        threading.Thread.__init__(self)

        self.index = index
        self.obj = obj

        self.start()

    def run(self):
        temp_status = None
        temp_object = None

        try:
            print(self.obj["url"])
            temp_req = Request(self.obj["url"], headers=request_headers)
            temp_res = urlopen(temp_req)
            temp_code = temp_res.getcode()
            temp_type = temp_res.info()["Content-Type"]

            temp_status = temp_res.getcode()
            temp_object = temp_res

            if temp_code == 200:
                if types in temp_type:
                    temp_content = temp_res.read()

                    # var_dump(temp_content)

                    temp_data = fromstring(temp_content)

                    temp_thread = threading.Thread(
                        target=ParseThread, args=(self.obj["url"], temp_data)
                    )

                    link_threads.append(temp_thread)
                    temp_thread.start()

        except HTTPError as e:
            temp_status = e.code
            pass

        self.obj["obj"] = temp_object
        self.obj["sta"] = temp_status

        ProcessChecked(self.obj)


def dump(obj):
    """return a printable representation of an object for debugging"""
    newobj = obj

    if "__dict__" in dir(obj):
        newobj = obj.__dict__

        if " object at " in str(obj) and "__type__" not in newobj:
            newobj["__type__"] = str(obj)

            for attr in newobj:
                newobj[attr] = dump(newobj[attr])

    return newobj


def FormatDate(datetime):
    datearr = eut.parsedate(datetime)
    date = None

    try:
        year = str(datearr[0])
        month = str(datearr[1])
        day = str(datearr[2])

        if int(month) < 10:
            month = "0" + month

        if int(day) < 10:
            day = "0" + day

        date = year + "-" + month + "-" + day
    except IndexError:
        pprint(datearr)

    return date


def ParseThread(url, data):
    temp_links = data.xpath("//a")

    for _, temp_link in enumerate(temp_links):
        temp_attrs = temp_link.attrib

        if "href" not in temp_attrs:
            continue

        protocol_exclude_list = [
            'mailto:',
            'tel:'
        ]
        temp_src = url
        temp_url = temp_attrs.get("href")

        if any(temp_url.startswith(protocol) for protocol in protocol_exclude_list):
            continue

        path = JoinURL(temp_src, temp_url)

        # var_dump(path)

        exclude_list = [
            "/photoviewer/",
            "/user/",
            "/login/",
            "/your-account/",
            "/your-order/",
            "/venuesdetail/",
            "/newsfeed/",
            "/promoters/",
            "/events/add/",
            "/select_seating_places/",
            "/?category=",
            "/feedback_promoter/",
            "/?news_not_found",
            "/engine/",
            "/author/",
            "/vendors/",
            "/events/select_seating_places/",
        ]

        if (path is not False) and not any(map(path.__contains__, exclude_list)):
            ProcessURL(path, temp_src)


def JoinURL(src, url):
    value = False

    url_info = urlparse(url)
    src_info = urlparse(src)

    # url_scheme = url_info.scheme
    # src_scheme = src_info.scheme

    url_netloc = url_info.netloc
    src_netloc = src_info.netloc

    if src_netloc.startswith(netloc_prefix_str):
        src_netloc = src_netloc[netloc_prefix_len:]

    if url_netloc.startswith(netloc_prefix_str):
        url_netloc = url_netloc[netloc_prefix_len:]

    if url_netloc == "" or url_netloc == InitialURLNetloc:
        url_path = url_info.path
        src_path = src_info.path

        src_new_path = urljoin(InitialURLBase, src_path)
        url_new_path = urljoin(src_new_path, url_path)

        path = urljoin(src_new_path, url_new_path)

        # print path

        value = path

    return value


def ProcessURL(url, src=None, obj=None):
    found = False

    for value in queue:
        if value["url"] == url:
            found = True
            break

    for value in checked:
        if value["url"] == url:
            found = True
            break

    if found is False:
        temp = {}
        temp["url"] = url
        temp["src"] = src
        temp["obj"] = obj
        temp["sta"] = None

        queue.append(temp)


def ProcessChecked(obj):
    found = False

    for item in checked:
        if item["url"] == obj["url"]:
            found = True
            break

    if found is False:
        checked.append(obj)

def print_usage():
    print("usage: " + sys.argv[0] + " URL OUTPUT")


def main():
    global filename
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    init_url(sys.argv[1])
    filename = sys.argv[2]

    RunCrawler(InitialURL)


if __name__ == "__main__":
    main()
