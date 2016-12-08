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
import string

from bs4 import BeautifulSoup
from oauth2client.service_account import ServiceAccountCredentials
from urllib.request import urlopen
from contentpacks.khanacademy import PROJECTION_KEYS, API_URL, KA_DOMAIN, download_and_clean_kalite_data
from contentpacks.utils import NodeType, get_lang_ka_name, get_lang_native_name, get_lang_name
from contentpacks.languagechannels import known_language_channels

# Reference https://github.com/burnash/gspread
# https://github.com/burnash/gspread/issues/201
# http://stackoverflow.com/questions/23861680/convert-spreadsheet-number-to-column-letter

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
    "URL", "DURATION", "REQUIRED FOR", "TRANSCRIPT"]

LE_SUPPORTED_LANG = ['arabic', 'armenian', 'bahasa indonesia', 'bangla', 'bulgarian', 'chinese', 'czech',
                     'danish', 'dari', 'deutsch', 'english', 'espanol', 'farsi', 'francais', 'greek', 'hebrew',
                     'hindi', 'italiano', 'japanese', 'kiswahili', 'korean', 'mongolian', 'nederlands', 'norsk',
                     'polish', 'portugal portugues', 'portugues', 'punjabi', 'russian', 'serbian', 'sindhi',
                     'sinhala', 'tamil', 'telugu', 'thai', 'turkce', 'ukrainian', 'urdu', 'xhosa', 'zulu']


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
    dump_json = os.path.join(BUILD_PATH, "%s_node_data.json" % lang_code)
    with open(dump_json, "w") as f:
        ujson.dump(node_data, f)
        
        
def check_subjects_in_en_data(lang_code=None, force=False,):
    _ensure_dir(BUILD_PATH)
    projection = json.dumps(PROJECTION_KEYS)
    lang_url = API_URL.format(projection=projection, lang=lang_code, ka_domain=KA_DOMAIN)
    convert_to_json(lang_url, lang_code )
    en_url = API_URL.format(projection=json.dumps(PROJECTION_KEYS), lang=EN_LANG_CODE, ka_domain=KA_DOMAIN)
    convert_to_json(en_url, EN_LANG_CODE)
       

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
    dump_json = os.path.join(BUILD_PATH, "en_nodes.json")
    en_item_data = []
    with open(dump_json, 'r') as f:
        en_data = ujson.load(f)
    for item in en_data:
        if item["kind"] == NodeType.video:
            en_item_data.append(item)
    return en_item_data


def _get_youtubes_ids(subjects):
    for yt_id in re.finditer(YOUTUBE_ID_REGEX, str(subjects)):
        youtube_id = yt_id.group().replace("v=", "")
        return youtube_id


def map_youtube_api_to_spreadsheet(spreadsheet=None):
    for langcode, channel_id in known_language_channels.items():
        video_count = 0
        playlist_count = 0
        YOUR_API_KEY = "AIzaSyCMzba_1AeFaAipFNNC44Pmztegmxdctx8"
        channel_id = channel_id.get("channel_id")
        channel = requests.get(
            "https://www.googleapis.com/youtube/v3/playlists?part=snippet%2CcontentDetails&channelId={0}&maxResults=50&key={1}".format(
                channel_id, YOUR_API_KEY))
        channel_node_data = ujson.loads(channel.content)
        for playlist_data in channel_node_data.get("items"):
            playlist_id = playlist_data.get("id")
            playlist = requests.get(
                "https://www.googleapis.com/youtube/v3/playlistItems?part=snippet%2CcontentDetails%2Cstatus&maxResults=50&playlistId={0}&key={1}".format(
                    playlist_id, YOUR_API_KEY))
            playlist_node_data = ujson.loads(playlist.content)
            playlist_count += 1
            for video_data in playlist_node_data.get('items'):
                video_id = video_data["contentDetails"].get(u'videoId', {})
                description = video_data["snippet"].get(u'description', {})
                video_count += 1
                en_youtube_id = _get_youtubes_ids(description)
                print("title", en_youtube_id)
        logging.info("Langcode:(%s) playlist_count:(%s) video_count:(%s) " % (langcode, playlist_count, video_count))


def get_video_masterlist():
    lang_url = "http://www.khanacademy.org/api/internal/videos/localized/all"
    lang_code = "master_list"
    # convert_to_json(lang_url=lang_url, lang_code=lang_code)
    dump_json = os.path.join(BUILD_PATH, "%s_node_data.json" % lang_code )
    with open(dump_json, 'r') as f:
        download_node_data = ujson.load(f)
    return download_node_data


def get_all_languagelookup_data():
    languagelookup = os.path.join(PROJECT_PATH, "resources/languagelookup.json")
    with open(languagelookup, 'r') as f:
        lang_data = ujson.load(f)
    return lang_data


def dubbed_video_data_struct(readable_id, youtube_ids, license_name, duration, title,):
    data_dict = {
        "readable_id": readable_id,
        "youtube_ids": youtube_ids,
        "license_name": license_name,
        "duration": duration,
        "title": title
    }
    return data_dict


def get_video_dict(video_dict=None):
    languagelookup = get_all_languagelookup_data()
    data_dict = {v: "" for v in LE_SUPPORTED_LANG}
    for sup_lang in LE_SUPPORTED_LANG:
        for lookup_key, val in languagelookup.items():
            for video_key, youtube_id in video_dict.items():
                if val.get("ka_name") is not None and sup_lang == val.get("ka_name").lower():
                    if video_key == lookup_key:
                        data_dict[sup_lang] = youtube_id
                elif val.get("native_name") is not None and sup_lang == val.get("native_name").lower():
                    if video_key == lookup_key:
                        data_dict[sup_lang] = youtube_id
                elif val.get("name") is not None and sup_lang == val.get("name").lower():
                    if video_key == lookup_key:
                        data_dict[sup_lang] = youtube_id
    return data_dict


def dubbed_video_node_data(master_node_data, en_node_data):
    video_count = 0
    node_data = []
    for index, en_val in enumerate((en_node_data), 4):
        video_count += 1
        en_readable_id = en_val.get("readable_id")
        seen = set()
        for key, master_val in enumerate(master_node_data):
            master_readable_id = master_val.get("readable_id")
            if en_readable_id == master_readable_id and en_readable_id not in seen:
                seen.add(en_readable_id)
                video_dict = master_val.get("youtube_ids")
                video_data = get_video_dict(video_dict)
                license_name = en_val.get("license_name")
                title = en_val.get("title")
                duration = en_val.get("duration")
                nodes = dubbed_video_data_struct(readable_id=en_readable_id, youtube_ids=video_data,
                                                 license_name=license_name, title=title, duration=duration)
                node_data.append(nodes)
    logging.info("Total video_count:(%s)" % video_count)
    
    return node_data


def map_cell_range(start_col, end_col, start_row, end_row):
    """Get the cell range to update the cells by batch"""
    # Sample (A4:C4)
    cell_range = '{col_i}{row_i}:{col_f}{row_f}'.format(
        col_i=convert_number_to_column(start_col),
        col_f=convert_number_to_column(end_col),
        row_i=start_row,
        row_f=end_row)
    return cell_range


def convert_number_to_column(n, b=string.ascii_uppercase):
    """Lets convert the numbers into letters this will enable us to map in the spreadsheet column"""
    d, m = divmod(n, len(b))
    return convert_number_to_column(d - 1, b) + b[m] if d else b[m]


def update_cell_by_batch(sheet, node_data,  node_key, start_col, end_col, start_row, end_row):
    header_cell_range = map_cell_range(start_col=start_col, end_col=end_col, start_row=start_row, end_row=end_row)
    title_cell_list = sheet.range(header_cell_range)
    for nodes, cell in zip(node_data, title_cell_list):
        title = nodes.get(node_key)
        cell.value = title
    sheet.update_cells(title_cell_list)
  
        
def update_or_create_spreadsheet(spreadsheet=None, node_data=None):
    spreadsheet_headers = list(SPREADSHEET_DEFAULT_VALUE)
    node_obj_count = len(node_data)
    for sup_lang in LE_SUPPORTED_LANG:
        spreadsheet_headers.append(sup_lang.upper())
    column_length = len(spreadsheet_headers)
    try:
        spreadsheet.add_worksheet(title=BUILD_VERSION, rows=node_obj_count, cols=column_length+2)
    except Exception as e:
        logging.info(e)
    sheet = spreadsheet.worksheet(BUILD_VERSION)
    logging.info("Populate spreadsheet header")
    header_cell_range = map_cell_range(start_col=0, end_col=column_length, start_row=3, end_row=3)
    header_cell_list = sheet.range(header_cell_range)
    for val, cell in zip(spreadsheet_headers, header_cell_list):
        cell.value = val
    sheet.update_cells(header_cell_list)
        
    logging.info("Populate title column")
    update_cell_by_batch(sheet, node_data=node_data, node_key="title", start_col=3, end_col=3, start_row=4,
                         end_row=node_obj_count)
    
    logging.info("Populate license column")
    update_cell_by_batch(sheet, node_data=node_data, node_key="license_name", start_col=4, end_col=4, start_row=4,
                         end_row=node_obj_count)
    
    logging.info("Populate title column")
    update_cell_by_batch(sheet, node_data=node_data, node_key="readable_id", start_col=8, end_col=8, start_row=4,
                         end_row=node_obj_count)

    logging.info("Populate title column")
    update_cell_by_batch(sheet, node_data=node_data, node_key="duration", start_col=11, end_col=11, start_row=4,
                         end_row=node_obj_count)


def main():
    # spreadsheet = _access_google_spreadsheet()
    en_node_data = get_en_data()
    master_node_data = get_video_masterlist()
    node_data = dubbed_video_node_data(master_node_data, en_node_data)
    # update_or_create_spreadsheet(spreadsheet, node_data)

    
if __name__ == "__main__":
    main()
