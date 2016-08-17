#!/usr/bin/env python3

'''
    Sorts through Roll20's LFG HTML and returns a markdown file
    containing game listings.
'''


from bs4 import BeautifulSoup
from collections import defaultdict
import os
import re
import requests
import time


# Global values
URL = "https://app.roll20.net"
GAMES = {
        'dragonage': 'Dragon Age RPG',
        'fantasyage': 'Fantasy AGE',
        'fate': 'FATE \( Core, Accelerated, Dresden Files, etc \)',
        'shadowrun': 'Shadowrun \( Any Edition \)',
        'wod': 'World of Darkness \( Vampire, Werewolf, Mage, etc \)', }
OPTIONS = [
        'days=',
        'dayhours=',
        'frequency=onceweekly,biweekly',
        'timeofday=7:00pm',
        'timeofday_seconds=1470952800',
        'language=English',
        'avpref=Any',
        'gametype=rpg',
        'newplayer=false',
        'yesmaturecontent=true',
        "playingstructured={}".format('%2C'.join(GAMES.keys())),
        'sortby=relevance',
        'for_event=', ]
TARGET_DIR = [
        os.path.expanduser('~'),
        'Documents',
        'RPG',
        'Roll20',
        'listings', ]


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
    href = URL + title_link.get('href')
    return "[{}]({})".format(title, href)


@catch_bad_html
def get_gm(data):
    ''' Extract GM name and profile url from table data. '''
    name = data.find('div', 'name').get_text()
    href = URL + data.find('a', 'userprofile').get('href')
    return "[{}]({})".format(name, href)


@catch_bad_html
def get_desc(data):
    ''' Extract game description from table data. '''
    desc = data.contents[3].get_text().strip()
    return re.sub(r'\s*Read more\.{3}', r'...', desc)


def get_game_type(meta):
    ''' Use regex to determine game being played. '''
    regex = re.compile(r"({})".format('|'.join(GAMES.values())))
    game_type = re.search(regex, meta)
    return game_type.group(0) if game_type else 'Unknown'


@catch_bad_html
def check_pagination(data):
    ''' Check if there are more pages of search results. '''
    next_link = data.find('ul', 'pagination').find_all('a')[-1].get('href')
    if next_link != 'javascript:void(0);':
        return URL + next_link
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
        yield game_type, (title, gm, desc)


def write_listings(listings):
    ''' Write our listings to a markdown file. '''
    today = time.strftime('%Y-%m-%d')
    now = time.strftime('%I:%M %p')
    filename = os.path.join(*TARGET_DIR, 'roll20-{}.md'.format(today))
    with open(filename, 'w') as fh:
        fh.write('# Roll20 listings for {}\nCreated {}\n\n'.format(today, now))
        for system, entries in listings.items():
            fh.write("## {}\n{} listings found.<br>\n".format(
                    system, len(entries)))
            for entry in entries:
                fh.write("### {} :: {}\n{}\n\n".format(*entry))


def main():
    ''' This will be run when script is called from the command line. '''
    url = "{}/lfg/search/?{}".format(URL, '&'.join(OPTIONS))
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
