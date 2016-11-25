#!/usr/bin/env python3
''' Sorts through Roll20's LFG HTML and returns a markdown file
    containing game listings. '''


from bs4 import BeautifulSoup
from collections import defaultdict
from jinja2 import Environment, FileSystemLoader
import json
import os
import re
import requests
import time


# Global values
with open(os.path.join(os.getcwd(), 'config.json')) as json_file:
    CONFIG = json.load(json_file)


ENV = Environment(loader=FileSystemLoader('./templates'))
TEMPLATE = ENV.get_template('listings_template.md')


def notify(message):
    ''' Sends a system notification (on Linux) and exits the program. '''
    os.system(' '.join(['notify-send', '"Roll20 Scraper"', message]))
    exit()


def catch_bad_html(f):
    ''' Decorator to handle errors when parsing html. '''
    def f_wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except AttributeError:
            notify("'Malformed HTML. Check: {}'".format(f.__name__))
    return f_wrapper


def make_soup(url):
    ''' Takes url, makes get request, and returns delicious soup. '''
    try:
        search = requests.get(url)
    except requests.exceptions.ConnectionError:
        notify('"Couldn\'t load page. Check: make_soup"')
    return BeautifulSoup(search.text, 'html.parser')


@catch_bad_html
def get_title(title_link):
    ''' Takes title link, and splits it into title and url. '''
    title = title_link.get_text()
    href = CONFIG['url'] + title_link.get('href')
    return "[{}]({})".format(title, href)


@catch_bad_html
def get_gm(data):
    ''' Extract GM name and profile url from table data. '''
    name = data.find('div', 'name').get_text()
    href = CONFIG['url'] + data.find('a', 'userprofile').get('href')
    return "[{}]({})".format(name, href)


@catch_bad_html
def get_desc(data):
    ''' Extract game description from table data. '''
    desc = data.contents[3].get_text().strip()
    return re.sub(r'\s*Read more\.{3}', r'...', desc)


def get_game_type(meta):
    ''' Use regex to determine game being played. '''
    regex = re.compile(r"({})".format('|'.join(CONFIG['games'].values())))
    game_type = re.search(regex, meta)
    return game_type.group(0) if game_type else 'Unknown'


@catch_bad_html
def check_pagination(data):
    ''' Check if there are more pages of search results. '''
    next_link = data.find('ul', 'pagination').find_all('a')[-1].get('href')
    if next_link != 'javascript:void(0);':
        return CONFIG['url'] + next_link
    else:
        return ''


@catch_bad_html
def scrape_page(data):
    ''' Process each listing on the search results page. '''
    campaign_table = data.find('div', 'campaigns').table
    for row in campaign_table.find_all('tr', 'lfglisting'):
        game_type = get_game_type(row.find('td', 'meta').get_text())
        title = get_title(row.strong.a)
        gm = get_gm(row.find('td', 'gminfo'))
        desc = get_desc(row.find_all('td')[2])
        yield game_type, {'title': title, 'gm': gm, 'desc': desc}


def write_listings(listings):
    ''' Write our listings to a markdown file. '''
    today = time.strftime('%Y-%m-%d')
    now = time.strftime('%I:%M %p')
    filename = os.path.join(CONFIG['targetDir'], 'roll20-{}.md'.format(today))
    with open(filename, 'w') as fh:
        fh.write(TEMPLATE.render({'today': today, 'now': now, 'listings': listings}))


def build_url(url, options, games):
    '''Takes the base URL, the search paramters and games list and
       uses them to build the initial URL.'''
    options_string = '&'.join(["{}={}".format(key, val) for key, val in options.items()])
    games_string = "playingstructured={}".format('%2C'.join([key for key in games.keys()]))
    return "{}/lfg/search/?{}&{}".format(url, options_string, games_string)


def main():
    ''' This will be run when script is called from the command line. '''
    url = build_url(CONFIG['url'], CONFIG['options'], CONFIG['games'])
    listings = defaultdict(list)
    while url:
        roll20_soup = make_soup(url)
        for system, values in scrape_page(roll20_soup):
            listings[system].append(values)
        url = check_pagination(roll20_soup)
    write_listings(listings)
    notify('"Listings are ready!"')


if __name__ == '__main__':
    main()
