"""
TODOS(Eduard James Aban):
* Create new spreadsheet and dump all the updated subjects to the Gdoc.
* Check the English data then compare it on the selected language.
* Check another option using the youtube playlist as source of dubbed video mappings.
* Check the khan locale names used so we can write it on the spreadsheet.
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
from contentpacks.utils import get_lang_name, get_lang_native_name, get_lang_code_list, get_lang_ka_name
from contentpacks.utils import NodeType

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
BUILD_VERSION = "0.17.x"
SPREADSHEET_DEFAULT_VALUE = [
    "SERIAL", "DATE ADDED", "DATE CREATED", "TITLE", "LICENSE", "DOMAIN", "SUBJECT", "TOPIC", "TUTORIAL", "TITLE ID",
    "URL", "DURATION", "REQUIRED FOR", "TRANSCRIPT", "ENGLISH", "ARABIC", "ARMENIAN", "BENGALI", "BAHASA INDONESIA", "BANGLA BULGARIAN",
    "CHINESE", "CZECH", "DANISH	DARI", "DEUTSCH", "ESPANOL", "FARSI" "FRANCAIS", "GREEK", "HEBREW", "HINDI", "ITALIANO",
    "JAPANESE", "KISWAHILI", "KOREAN", "MONGOLIAN",	"NEDERLANDS", "NEPALI", "NORSK", "POLISH", "PORTUGUES",
    "PORTUGAL PORTUGUES", "PUNJABI", "RUSSIAN",  "SERBIAN", "SINDHI", "SINHALA", "TAMIL", "TELUGU", "THAI",
    "TURKCE", "UKRAINIAN", "URDU", "XHOSA", "ZULU"
    ]


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
        

def convert_to_json(lang_url, lang_code):
    data = requests.get(lang_url)
    node_data = ujson.loads(data.content)
    dump_json = os.path.join(BUILD_PATH, "%s-node_data.json" % lang_code)
    with open(dump_json, "w") as f:
        ujson.dump(node_data, f)
        
        
def check_subjects_in_en_data(lang_code=None, force=False,):
    _ensure_dir(BUILD_PATH)
    projection = json.dumps(PROJECTION_KEYS)
    lang_url = API_URL.format(projection=projection, lang=lang_code, ka_domain=KA_DOMAIN)
    convert_to_json(lang_url, lang_code )
    en_url = API_URL.format(projection=json.dumps(PROJECTION_KEYS), lang=EN_LANG_CODE, ka_domain=KA_DOMAIN)
    convert_to_json(en_url, EN_LANG_CODE)
       

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


def _access_google_spreadsheet():
    _ensure_dir(os.path.dirname(GOOGLE_CREDENTIAL_PATH))
    scope = ['https://spreadsheets.google.com/feeds']
    credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIAL_PATH, scope)
    gcreadentials = gspread.authorize(credentials)
    sheet = gcreadentials.open_by_url("https://docs.google.com/spreadsheets/d/1q9fVt5cxkR7dI7uLR1klGDK7XHjjeSvBoWYilkDqE50/edit#gid=0")
    return sheet


def _scrape_subject(url):
    url_obj = urlopen(url).read()
    soup = BeautifulSoup(url_obj)
    subjects = soup.find_all("a", class_="subject-link")
    return subjects



def get_en_data():
    BUILD_PATH = "/Users/mrpau-eduard/content-pack-maker/build"
    languagelookup = os.path.join(BUILD_PATH, "en_nodes.json")
    en_item_data = []
    with open(languagelookup, 'r') as f:
        en_data = ujson.load(f)
    for item in en_data:
        if item["kind"] == NodeType.video:
            en_item_data.append(item)
    return en_item_data


def get_all_languagelookup_data():
    languagelookup = os.path.join(PROJECT_PATH, "resources/ka_language_support.json")
    with open(languagelookup, 'r') as f:
        language_codes = ujson.load(f)
    return language_codes


def create_new_sheet(spreadsheet):
    # Create New worksheet
    try:
        spreadsheet.add_worksheet(title=BUILD_VERSION, rows=10000, cols=100)
    except Exception as e:
        logging.info(e)
    # Update sheet with the dafaut header value
    sheet = spreadsheet.worksheet(BUILD_VERSION)
    for index, val in enumerate((SPREADSHEET_DEFAULT_VALUE), 1):
        sheet.update_cell(3, index, val)
        logging.info("Updating sheet for column:(%s), value:(%s)" % (index, val))
    en_subjects = get_en_data()
    title_count = 0
    for index, val in enumerate((en_subjects), 4):
        title_count +=1
        item_title = val.get("title")
        license_name = val.get("license_name")
        duration = val.get("duration")
        youtube_id = val.get("youtube_id")
        title_id = val.get("readable_id")
        try:
            sheet.update_cell(index, 4, item_title)
            sheet.update_cell(index, 5, license_name)
            sheet.update_cell(index, 10, title_id)
            sheet.update_cell(index, 12, duration)
            sheet.update_cell(index, 15, youtube_id)
        except Exception as e:
            logging.warning(e)
        if index == 1000:
            break
    logging.info("Total tiltles added: (%s)" % title_count)


def map_spreadsheet_values(spreadsheet=None):
    spreadsheet = spreadsheet.worksheet(BUILD_VERSION)
    langcode_list = get_all_languagelookup_data()
    for lang in langcode_list:
        subject_data_list = []
        url = "https://%s.khanacademy.org" % lang
        subjects = _scrape_subject(url)
        for subject in subjects:
            dubbed_youtube_ids = _get_youtubes_ids(subject)
            subject_data_dict = _create_data_struct(subject=subject.text, youtube_id=dubbed_youtube_ids)
            subject_data_list.append(subject_data_dict)
        locale_name = (langcode_list[lang]).upper()
        print("local_names", locale_name)
        for subject_data in subject_data_list:
            subject_title = subject_data.get("title")
            subject_youtub_id = subject_data.get("youtube_id")
            print("langcode: %s subject: %s subject_youtub_id: %s" % (url, subject_title, subject_youtub_id))

            # Mapping of row and column
            try:
                header_subject = spreadsheet.find(subject_title)
                header_title = spreadsheet.find(locale_name)
                print("value: (%s) col: (%s) column: (%s)" % (header_title.value, header_title.col, header_title.row))
                print("value: (%s) col: (%s) row: (%s)" % (header_subject.value, header_subject.col, header_subject.row))
                spreadsheet.update_cell(row=header_subject.row, col=header_title.col, val=subject_youtub_id)
            except Exception as e:
                print("Exception subject not found:", e)


def main():
    # check_subjects_in_en_data()
    spreadsheet = _access_google_spreadsheet()
    # create_new_sheet(spreadsheet)
    map_spreadsheet_values(spreadsheet=spreadsheet)

    




if __name__ == "__main__":
    main()
