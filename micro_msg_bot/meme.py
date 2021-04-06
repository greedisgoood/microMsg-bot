import requests
import shelve
import time
from bs4 import BeautifulSoup
from functools import lru_cache
from threading import Lock
from .logger import logger

user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36'
session = requests.Session()
session.headers['user-agent'] = user_agent


def large_img(url):
    if url.startswith('//'):
        url = 'http:' + url
    if url.endswith('!dtb'):
        url = url[:-4]
    return url.replace('/bmiddle/', '/large/', 1)


@lru_cache()
def search(keyword):
    resp = session.get('https://www.doutula.com/search', params={'keyword': keyword})

    if resp.status_code != 200:
        logger.info('www.doutula.com new session %s', session.cookies.get_dict())
        resp = session.get('https://www.doutula.com/search', params={'keyword': keyword})

    soup = BeautifulSoup(resp.text, 'lxml')
    result = ((i.get('data-original'), i.get('data-backup')[:-4]) for i in soup.select('img[data-original]') if i.get('class') != ['gif'])
    return [[large_img(url) for url in imgs] for imgs in result]


def download_gif(f, *url):
    for u in url:
        resp = requests.get(u, allow_redirects=False)
        if resp.status_code == 200:
            f.write(resp.content)
            f.flush()
            return


keyword_dict_locks = Lock()
keyword_locks = {}
searched_lock = Lock()


def image_url(keyword):
    with keyword_dict_locks:
        kw_lock = keyword_locks.get(keyword, None)
        if not kw_lock:
            kw_lock = Lock()
            keyword_locks[keyword] = kw_lock

    with kw_lock:
        img = None
        with searched_lock:
            with shelve.open('searched') as searched:
                imgs = searched.get(keyword, None)
                if imgs:
                    img = imgs.pop(0)
                    imgs.append(img)
                    searched[keyword] = imgs
        if img:
            return img

        if not img:
            imgs = search(keyword)
            logger.info('New keyword "%s", %d result%s', keyword, len(imgs), 's' if len(imgs) > 1 else '')
            imgs = imgs[:10]
        if imgs:
            img = imgs.pop(0)
            imgs.append(img)
            with searched_lock:
                with shelve.open('searched') as searched:
                    searched[keyword] = imgs
            return img
