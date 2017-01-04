"""
# TODO(mrpau-eduard):
    * Convert the json to sql to have a offline version of dubbed video mappings.

# Note:
    * Lets hard code the supported lang since it is not sure if we use ka_name, native_name or name as the default
    language name.
    * To create the google credentials do the steps below:
        1. Head to Google Developers Console and create a new project (or select the one you have.)
            - Google console: https://console.developers.google.com/project
        2. Under “API & auth”, in the API enable “Drive API”.
        3. Go to “Credentials” and choose “New Credentials > Service Account Key”.
        4. Download the json file. Move the .json file in the ~/content-pack-maker/build/credential/
        5. Rename the file as credential.json
    * Share the spreadsheet to the client_email. otherwise you can't access the spreadsheet.
        - Get the value of the client_mail from the credential.json.
        

# Reference
    * https://github.com/burnash/gspread
    * https://github.com/burnash/gspread/issues/201
"""

import errno
import gspread
import json
import os
import logging
import requests
import string
import sys
import ujson

from oauth2client.service_account import ServiceAccountCredentials
from contentpacks.khanacademy import API_URL, PROJECTION_KEYS, KA_DOMAIN, download_and_clean_kalite_data


PROJECT_PATH = os.path.join(os.getcwd())
BUILD_PATH = os.path.join(PROJECT_PATH, "build")
CREDENTIAL_DIR = os.path.join(BUILD_PATH, "credential")
GOOGLE_CREDENTIAL_FILE = os.path.join(CREDENTIAL_DIR, "credentials.json")
SCOPE = ['https://spreadsheets.google.com/feeds']

CONTETNPACK_DIR = os.path.join(PROJECT_PATH, "contentpacks")
RESOURCES_DIR = os.path.join(CONTETNPACK_DIR, "resources")
LANGUAGELOOKUP_FILE = os.path.join(RESOURCES_DIR, "languagelookup.json")

EN_LANG_CODE = "en"
BUILD_VERSION = "0.17.x"
SPREADSHEET_DEFAULT_VALUE = [
    "SERIAL", "DATE ADDED", "DATE CREATED", "TITLE", "LICENSE", "DOMAIN", "SUBJECT", "TOPIC", "TUTORIAL", "TITLE ID",
    "URL", "DURATION", "REQUIRED FOR", "TRANSCRIPT"]

LE_TRANSLATIONMAPPING = "https://docs.google.com/spreadsheets/d/1haV0KK8313lG-_Ay2REplQuMquRStZumB3zxmmtYqO0/edit#gid=0"

LE_SUPPORTED_LANG = ['english', 'arabic', 'armenian', 'bahasa indonesia', 'bangla', 'bulgarian', 'chinese', 'czech',
                     'danish', 'dari', 'deutsch', 'espanol', 'farsi', 'francais', 'greek', 'hebrew',
                     'hindi', 'italiano', 'japanese', 'kiswahili', 'korean', 'mongolian', 'nederlands', 'norsk',
                     'polish', 'portugal portugues', 'portugues', 'punjabi', 'russian', 'serbian', 'sindhi',
                     'sinhala', 'tamil', 'telugu', 'thai', 'turkce', 'ukrainian', 'urdu', 'xhosa', 'zulu']

logging.getLogger().setLevel(logging.INFO)

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
    """A handy json converter just pass the lang_code and the url of the json source."""
    data = requests.get(lang_url)
    node_data = ujson.loads(data.content)
    dump_json = os.path.join(BUILD_PATH, "%s_node_data.json" % lang_code)
    with open(dump_json, "w") as f:
        ujson.dump(node_data, f)

def access_google_spreadsheet():
    credentials = None
    _ensure_dir(os.path.dirname(GOOGLE_CREDENTIAL_FILE))
    if os.path.exists(GOOGLE_CREDENTIAL_FILE):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIAL_FILE, SCOPE)
    else:
        logging.info("Please create your google credentials.")
    gcreadentials = gspread.authorize(credentials)
    sheet = gcreadentials.open_by_url(LE_TRANSLATIONMAPPING)
    return sheet


def get_en_data():
    """Create the en_nodes.json."""
    en_nodes_path = os.path.join(BUILD_PATH, "en_nodes.json")
    logging.info("Now creating %s..." % en_nodes_path)

    if not os.path.exists(en_nodes_path):
        url = API_URL.format(projection=json.dumps(PROJECTION_KEYS), lang=EN_LANG_CODE, ka_domain=KA_DOMAIN)
        download_and_clean_kalite_data(url, lang=EN_LANG_CODE, ignorecache=False, filename="en_nodes.json")
    with open(en_nodes_path, 'r') as f:
        en_node_load = ujson.load(f)
    return en_node_load


def get_video_masterlist():
    """Get dubbed video master list"""
    lang_code = "master_list"
    dump_json = os.path.join(BUILD_PATH, "%s_node_data.json" % lang_code)
    if not os.path.exists(dump_json):
        lang_url = "http://www.khanacademy.org/api/internal/videos/localized/all"
        logging.info("Get the master list video at %s" % lang_url)
        convert_to_json(lang_url=lang_url, lang_code=lang_code)
    logging.info("Build video master list at %s" % dump_json)
    with open(dump_json, 'r') as f:
        download_node_data = ujson.load(f)
    return download_node_data


def get_all_languagelookup_data():
    with open(LANGUAGELOOKUP_FILE, 'r') as f:
        lang_data = ujson.load(f)
    return lang_data


def dubbed_video_data_struct(readable_id, youtube_ids, license_name, duration, title):
    data_dict = {
        "url": "",
        "title id": readable_id,
        "youtube_ids": youtube_ids,
        "license": license_name,
        "duration": duration,
        "title": title
    }
    return data_dict


def get_video_dict(video_dict=None):
    """Create a youtube_ids data structure"""
    languagelookup = get_all_languagelookup_data()
    data_dict = {v: "" for v in LE_SUPPORTED_LANG}
    for sup_lang in LE_SUPPORTED_LANG:
        for lookup_key, val in languagelookup.items():
            for video_key, youtube_id in video_dict.items():
                if val.get("ka_name") is not None and sup_lang == val.get("ka_name").lower():
                    if video_key.lower() == lookup_key.lower():
                        data_dict[sup_lang] = youtube_id
                elif val.get("native_name") is not None and sup_lang == val.get("native_name").lower():
                    if video_key.lower() == lookup_key.lower():
                        data_dict[sup_lang] = youtube_id
                elif val.get("name") is not None and sup_lang == val.get("name").lower():
                    if video_key.lower() == lookup_key.lower():
                        data_dict[sup_lang] = youtube_id
    return data_dict


def dubbed_video_node_data(master_node_data, en_node_data):
    """
    Create a data structure base on en_node data then assign the respective dubbed video ids from the
    master list node data. This will assure us that the youtube_ids match on there respective subject/titles.
    """
    node_data = []
    seen = set()
    logging.info("Creating initial data structure base on the en_nodes.json and dubbed_video master list.")
    for index, en_val in enumerate((en_node_data), 1):
        en_readable_id = en_val.get("readable_id")
        for key_id, master_val in enumerate(master_node_data):
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
    return node_data


def assign_topic_data(node_data):
    """
    * Get the fresh topics from khan en language then match each video id with its respective topics,
        tutorial, subjects and domain.
    * Create the video_node_data.json.
    
    """
    khan_json = os.path.join(BUILD_PATH, "%s_node_data.json" % "khan")
    if not os.path.exists(khan_json):
        url = API_URL.format(projection=json.dumps(PROJECTION_KEYS), lang=EN_LANG_CODE, ka_domain=KA_DOMAIN)
        convert_to_json(lang_url=url, lang_code="khan")
    logging.info("Load khan nodes from %s" % khan_json)
    with open(khan_json, 'r') as f:
        khan_en_data = ujson.load(f)
        
    video_data_dict = []
    tutorial_data_dict = []
    topic_data_dict = []
    logging.info("Assign topic base on the khan en language.")
    for key, node in khan_en_data.items():
        logging.info("Collect all nodes with a key videos.")
        if key == "videos":
            for video_obj in node:
                video_title = video_obj.get("title")
                video_id = video_obj.get("id")
                data_dict = {"video_title": video_title, "video_id": video_id}
                video_data_dict.append(data_dict)
        
        if key == "topics":
            logging.info("Collect all nodes with a key topics.")
            for topic_obj in node:
                topic_title = topic_obj.get("title")
                topic_id = topic_obj.get("id")
                for child_data in topic_obj.get("childData"):
                    logging.info("Collect child data: ", child_data)
                    # Collect all the topics which will be tutorial data of each video.
                    if child_data.get("kind") == "Video":
                        data_dict = {"tutorial_title": topic_title, "child_data": child_data, "tutorial_id": topic_id}
                        tutorial_data_dict.append(data_dict)
                    # Collect all the topics.
                    if child_data.get("kind") == "Topic":
                        data_dict = {"topic_title": topic_title, "child_data": child_data, "topic_id": topic_id}
                        topic_data_dict.append(data_dict)

    def _get_topic_child_data(topic_dict, obj_id):
        for topic in topic_dict:
            topic_child_data = topic.get("child_data")
            if topic_child_data.get("id") == obj_id:
                logging.info("Match topic:(%s) to (%s)" % (obj_id, topic.get("topic_title")))
                return topic
        return {}

    khan_data_dict = []
    seen = set()
    logging.info("Assign topics to the video data.")
    for video_data in video_data_dict:
        video_title = video_data.get("video_title")
        video_id = video_data.get("video_id")
        for tutorial_data in tutorial_data_dict:
            tutorial_child_data = tutorial_data.get("child_data")
            if video_id == tutorial_child_data.get("id") and video_id not in seen:
                seen.add(video_id)
                tutorial_title = tutorial_data.get("tutorial_title")
                tutorial_id = tutorial_data.get("tutorial_id")
                topic_data = _get_topic_child_data(topic_data_dict, tutorial_id)
                subject_data = _get_topic_child_data(topic_data_dict, topic_data.get("topic_id"))
                domain_data = _get_topic_child_data(topic_data_dict, subject_data.get("topic_id"))
                data = {"domain": domain_data.get("topic_title"), "topic_title": topic_data.get("topic_title"),
                        "tutorial_title": tutorial_title, "video_title": video_title,
                        "subject_title": subject_data.get("topic_title")}
                khan_data_dict.append(data)
    
    for obj_id, node in enumerate((node_data), 1):
        node["serial"] = obj_id
        title = node.get("title")
        for index, khan_data in enumerate(khan_data_dict):
            if title == khan_data.get("video_title"):
                node["tutorial"] = khan_data.get("tutorial_title")
                node["domain"] = khan_data.get("domain")
                node["topic"] = khan_data.get("topic_title")
                node["subject"] = khan_data.get("subject_title")
    dump_json = os.path.join(BUILD_PATH, "video_node_data.json")
    logging.info("Save new dubbed_video data in %s" % dump_json)
    with open(dump_json, "w") as f:
        ujson.dump(node_data, f)
                
                

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
    """Convert the numbers into letters"""
    d, m = divmod(n, len(b))
    return convert_number_to_column(d - 1, b) + b[m] if d else b[m]


def update_cell_by_batch(sheet, node_data,  lang_column, node_key, start_col, end_col, start_row, end_row):
    """Update the cell by batch """
    header_cell_range = map_cell_range(start_col=start_col, end_col=end_col, start_row=start_row, end_row=end_row)
    logging.info("Updating cell range at %s" % header_cell_range)
    title_cell_list = sheet.range(header_cell_range)
    video_count = 0
    for nodes, cell in zip(node_data, title_cell_list):
        if node_key == "youtube_ids":
            node_obj = nodes.get(node_key)
            for key, video_obj in node_obj.items():
                if key == lang_column.lower():
                    video_count += 1
                    cell.value = video_obj
        else:
            node_obj = nodes.get(node_key)
            cell.value = node_obj
            if cell.value is None:
                cell.value = ""
    if node_key == "youtube_ids":
        logging.info("Total video count for %s: (%s)" % (lang_column, video_count))
    sheet.update_cells(title_cell_list)
  
        
def update_or_create_spreadsheet(spreadsheet=None):
    """Map the node_data.json into the spreadsheet"""
    dump_json = os.path.join(BUILD_PATH, "video_node_data.json")
    logging.info("Lets update the spreadsheet using the %s" % dump_json)
    with open(dump_json, 'r') as f:
        node_data = ujson.load(f)
        
    spreadsheet_headers = list(SPREADSHEET_DEFAULT_VALUE)
    node_obj_count = len(node_data)
    for sup_lang in LE_SUPPORTED_LANG:
        spreadsheet_headers.append(sup_lang.upper())
    column_length = len(spreadsheet_headers)
    try:
        logging.info("Create spreadsheet %s with columns:(%s) and rows:(%s)" % (BUILD_VERSION, column_length, node_obj_count))
        spreadsheet.add_worksheet(title=BUILD_VERSION, rows=node_obj_count, cols=column_length+2)
    except Exception as e:
        logging.info(e)
    sheet = spreadsheet.worksheet(BUILD_VERSION)
    logging.info("Create sheet %s" % sheet)
    header_cell_range = map_cell_range(start_col=0, end_col=column_length, start_row=3, end_row=3)
    logging.info("Populate spreadsheet header")
    header_cell_list = sheet.range(header_cell_range)
    for val, cell in zip(spreadsheet_headers, header_cell_list):
        cell.value = val
    sheet.update_cells(header_cell_list)
    
    logging.info("Find first the header location to reduce waiting time finding the column location before mapping it.")
    sp_headers_coordinate = []
    for obj in spreadsheet_headers:
        header_value = sheet.find(obj.upper())
        sp_headers_coordinate.append(header_value)
    logging.info("Header coordinates:", sp_headers_coordinate)
        
    for column_header in sp_headers_coordinate:
        logging.info("Updating values in column %s: " % column_header)
        
        if column_header.value.lower() in LE_SUPPORTED_LANG:
            logging.info("Update column(%s) with the node of count(%s)" % (column_header, node_obj_count))
            update_cell_by_batch(sheet, node_data=node_data, lang_column=column_header.value, node_key="youtube_ids",
                                 start_col=column_header.col-1, end_col=column_header.col-1, start_row=4, end_row=node_obj_count)
        else:
            logging.info("Update column(%s) with the node of count(%s)" % (column_header, node_obj_count))
            update_cell_by_batch(sheet, node_data=node_data, lang_column=None, node_key=column_header.value.lower(),
                                 start_col=column_header.col - 1, end_col=column_header.col - 1, start_row=4,
                                 end_row=node_obj_count)


def main():
    en_node_data = get_en_data()
    master_node_data = get_video_masterlist()
    node_data = dubbed_video_node_data(master_node_data, en_node_data)
    assign_topic_data(node_data)
    spreadsheet = access_google_spreadsheet()
    update_or_create_spreadsheet(spreadsheet)

    
if __name__ == "__main__":
    main()
