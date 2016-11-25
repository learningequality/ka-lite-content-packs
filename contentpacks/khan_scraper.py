"""
TODOS(Eduard James Aban):
* Create new spreadsheet and dump all the updated subjects to the Gdoc.
* Check the English data then compare it on the selected language.
* Check another option using the youtube playlist as source of dubbed video mappings.
"""

import errno
import re
import os
import gspread
import ujson
import sys
import logging
import json
import requests

from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
from urllib.request import urlopen
from contentpacks.generate_dubbed_video_mappings import main as generate_dubbed_video_mappings
from contentpacks.khanacademy import PROJECTION_KEYS, API_URL, KA_DOMAIN, download_and_clean_kalite_data



# Reference https://github.com/burnash/gspread
# https://github.com/burnash/gspread/issues/201

YOUTUBE_ID_REGEX = r"v=([\/\w\-\%]*)\w+"
KHAN_URL = ["https://sw.khanacademy.org"]
PROJECT_PATH = os.path.join(os.getcwd())
BUILD_PATH = os.path.join(PROJECT_PATH, "build")
GOOGLE_CREDENTIAL_PATH = os.path.join(BUILD_PATH, "credential", 'credentials.json')
DUBBED_VIDEOS_MAPPING_FILEPATH = os.path.join(BUILD_PATH, "dubbed_video_mappings.json")
EN_LANGUAGELOOKUP = "english"
EN_LANG_CODE = "en"


def _ensure_dir(path):
    """Create the entire directory path, if it doesn't exist already."""
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno == errno.EEXIST:
            # file already exists
            if not os.path.isdir(path):
                # file exists but is not a directory
                raise OSError(errno.ENOTDIR, "Not a directory: '%s'" % path)
            pass  # directory already exists
        else:
            raise

def get_langcode_list():
    pass
        

def convert_to_json(lang_url, lang_code):
    data = requests.get(lang_url)
    node_data = ujson.loads(data.content)
    dump_json = os.path.join(BUILD_PATH, "%s-node_data.json" % lang_code)
    with open(dump_json, "w") as f:
        ujson.dump(node_data, f)
        
        
def check_subjects_in_en_data(lang_code=None, force=False,):
    _ensure_dir(BUILD_PATH)
    projection = json.dumps(PROJECTION_KEYS)
    lang_code = "ar"
    lang_url = API_URL.format(projection=projection, lang=lang_code, ka_domain=KA_DOMAIN)
    convert_to_json(lang_url, lang_code )
    en_url = API_URL.format(projection=json.dumps(PROJECTION_KEYS), lang=EN_LANG_CODE, ka_domain=KA_DOMAIN)
    convert_to_json(en_url, EN_LANG_CODE)
    
        
        
def generate_en_video_lookup():
    if os.path.exists(os.path.join(BUILD_PATH, "dubbed_video_mappings.json")):
        logging.info('Dubbed videos json already exist at %s' % (DUBBED_VIDEOS_MAPPING_FILEPATH))
    else:
        generate_dubbed_video_mappings()
    dubbed_videos_path = os.path.join(BUILD_PATH, "dubbed_video_mappings.json")
    with open(dubbed_videos_path, 'r') as f:
        dubbed_videos_load = ujson.load(f)
    video_dict = dubbed_videos_load.get(EN_LANGUAGELOOKUP)
    en_video_list = video_dict.keys()
    return en_video_list


def _create_data_struct(subject=None, youtube_id=None):
    dict_data = {
        "title": str(subject),
        "youtube_id": str(youtube_id)
    }
    return dict_data


def _get_youtubes_ids(subjects):
    for yt_id in re.finditer(YOUTUBE_ID_REGEX, str(subjects)):
        youtube_id = yt_id.group().replace("v=", "")
        return youtube_id


def _scrape_subject(url):
    url_obj = urlopen(url).read()
    soup = BeautifulSoup(url_obj)
    subjects = soup.find_all("a", class_="subject-link")
    return subjects


def access_google_spreadsheet():
    _ensure_dir(os.path.dirname(GOOGLE_CREDENTIAL_PATH))
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIAL_PATH, scope)
    gcreadentials = gspread.authorize(credentials)
    sheet = gcreadentials.open_by_url("https://docs.google.com/spreadsheets/d/1FpW_nDb3KaydTFo4TGuPvuPPTS_fkekkID4TxletYmo/edit#gid=0").sheet1
    return sheet
    

def map_spreadsheet_values(urls=None, spreadsheet=None):
    subject_data_list = []
    for url in urls:
        subjects = _scrape_subject(url)
        for subject in subjects:
            dubbed_youtube_ids = _get_youtubes_ids(subject)
            subject_data_dict = _create_data_struct(subject=subject.text, youtube_id=dubbed_youtube_ids)
            subject_data_list.append(subject_data_dict)
    _as_column = spreadsheet.find("KISWAHILI")
    for subject_data in subject_data_list:
        subject_title = subject_data.get("title")
        subject_youtub_id = subject_data.get("youtube_id")
        
        # Mapping of row and column
        try:
            _as_row = spreadsheet.find(subject_title)
            print("value: (%s) col: (%s) row: (%s)" % (_as_column.value, _as_column.col, _as_column.row))
            print("value: (%s) col: (%s) row: (%s)" % (_as_row.value, _as_row.col, _as_row.row))
            spreadsheet.update_cell(_as_row.row, _as_column.col, subject_youtub_id)
        except Exception as e:
            print(e)
    return subject_data_list


def main():
    khan_url = KHAN_URL
    check_subjects_in_en_data()
    generate_en_video_lookup()
    spreadsheet = access_google_spreadsheet()
    map_spreadsheet_values(urls=khan_url, spreadsheet=spreadsheet)


if __name__ == "__main__":
    main()
