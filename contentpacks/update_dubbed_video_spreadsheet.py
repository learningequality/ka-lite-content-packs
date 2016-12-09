"""
# TODO(Eduard James Aban):
    * Convert the json to sql to have a offline version of dubbed video mappings.
    * Retrieve subjects topics and info from en_nodes.json.
    * Make the script as management command.
    * Make a documentation for this script how to use it.

# Note:
    * Lets hard code the supported lang since it is not sure if we use ka_name, native_name or name as the default
    language name.

# Reference
    * https://github.com/burnash/gspread
    * https://github.com/burnash/gspread/issues/201
"""

import errno
import gspread
import os
import logging
import requests
import string
import sys
import ujson

from contentpacks.utils import NodeType
from oauth2client.service_account import ServiceAccountCredentials


PROJECT_PATH = os.path.join(os.getcwd())
BUILD_PATH = os.path.join(PROJECT_PATH, "build")
GOOGLE_CREDENTIAL_PATH = os.path.join(BUILD_PATH, "credential", 'credentials.json')
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
    data = requests.get(lang_url)
    node_data = ujson.loads(data.content)
    dump_json = os.path.join(BUILD_PATH, "%s_node_data.json" % lang_code)
    with open(dump_json, "w") as f:
        ujson.dump(node_data, f)
        

def _access_google_spreadsheet():
    credentials = None
    _ensure_dir(os.path.dirname(GOOGLE_CREDENTIAL_PATH))
    scope = ['https://spreadsheets.google.com/feeds']
    if os.path.exists(GOOGLE_CREDENTIAL_PATH):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIAL_PATH, scope)
    else:
        logging.info("Please create your google credentials.")
    gcreadentials = gspread.authorize(credentials)
    sheet = gcreadentials.open_by_url("https://docs.google.com/spreadsheets/d/1q9fVt5cxkR7dI7uLR1klGDK7XHjjeSvBoWYilkDqE50/edit#gid=0")
    return sheet


def get_en_data():
    BUILD_PATH = "/Users/mrpau-eduard/content-pack-maker/build"
    dump_json = os.path.join(BUILD_PATH, "en_nodes.json")
    logging.info("Load en nodes from %s" % dump_json)
    en_item_data = []
    with open(dump_json, 'r') as f:
        en_data = ujson.load(f)
    for item in en_data:
        if item["kind"] == NodeType.video:
            en_item_data.append(item)
    return en_item_data


def get_video_masterlist():
    """Get dubbed video master list"""
    lang_url = "http://www.khanacademy.org/api/internal/videos/localized/all"
    lang_code = "master_list"
    convert_to_json(lang_url=lang_url, lang_code=lang_code)
    dump_json = os.path.join(BUILD_PATH, "%s_node_data.json" % lang_code)
    logging.info("Build video master list at %s" % dump_json)
    with open(dump_json, 'r') as f:
        download_node_data = ujson.load(f)
    return download_node_data


def get_all_languagelookup_data():
    languagelookup = os.path.join(PROJECT_PATH, "resources/languagelookup.json")
    with open(languagelookup, 'r') as f:
        lang_data = ujson.load(f)
    return lang_data


def dubbed_video_data_struct(readable_id, youtube_ids, license, duration, title,):
    data_dict = {
        "date added": "",
        "date created": "",
        "domain": "",
        "required for": "",
        "subject": "",
        "topic": "",
        "transcript": "",
        "tutorial": "",
        "url": "",
        "title id": readable_id,
        "youtube_ids": youtube_ids,
        "license": license,
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
    """
    * Create a data structure base on en_node data then assign the respective dubbed video ids from the
    master list node data. This will assure us that the youtube_ids match on there respective subject/titles.
    """
    video_count = 0
    node_data = []
    seen = set()
    for index, en_val in enumerate((en_node_data), 4):
        video_count += 1
        en_readable_id = en_val.get("readable_id")
        for key, master_val in enumerate(master_node_data):
            master_readable_id = master_val.get("readable_id")
            if en_readable_id == master_readable_id and en_readable_id not in seen:
                seen.add(en_readable_id)
                video_dict = master_val.get("youtube_ids")
                video_data = get_video_dict(video_dict)
                license = en_val.get("license")
                title = en_val.get("title")
                duration = en_val.get("duration")
                nodes = dubbed_video_data_struct(readable_id=en_readable_id, youtube_ids=video_data,
                                                 license=license, title=title, duration=duration)
                node_data.append(nodes)
    dump_json = os.path.join(BUILD_PATH, "node_data.json")
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
    header_cell_range = map_cell_range(start_col=start_col, end_col=end_col, start_row=start_row, end_row=end_row)
    title_cell_list = sheet.range(header_cell_range)
    for nodes, cell in zip(node_data, title_cell_list):
        if node_key == "youtube_ids":
            node_obj = nodes.get(node_key)
            for key, video_obj in node_obj.items():
                if key == lang_column.lower():
                    cell.value = video_obj
        else:
            node_obj = nodes.get(node_key)
            cell.value = node_obj
            if cell.value is None:
                cell.value = ""
    sheet.update_cells(title_cell_list)
  
        
def update_or_create_spreadsheet(spreadsheet=None, node_data=None):
    """Map the node_data.json into the spreadsheet"""
    
    dump_json = os.path.join(BUILD_PATH, "node_data.json")
    with open(dump_json, 'r') as f:
        node_data = ujson.load(f)
        
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
    logging.info("Create sheet %s" % sheet)
    header_cell_range = map_cell_range(start_col=0, end_col=column_length, start_row=3, end_row=3)
    logging.info("Populate spreadsheet header")
    header_cell_list = sheet.range(header_cell_range)
    for val, cell in zip(spreadsheet_headers, header_cell_list):
        cell.value = val
    sheet.update_cells(header_cell_list)
    
    # Lets find first the header location to reduce waiting time finding the column location before mapping it.
    sp_headers_coordinate = []
    for obj in spreadsheet_headers:
        header_value = sheet.find(obj.upper())
        sp_headers_coordinate.append(header_value)
        
    for column_header in sp_headers_coordinate:
        logging.info("Updating values in column %s: " % column_header)
        
        if column_header.value.lower() in LE_SUPPORTED_LANG:
            update_cell_by_batch(sheet, node_data=node_data, lang_column=column_header.value, node_key="youtube_ids",
                                 start_col=column_header.col-1, end_col=column_header.col-1, start_row=4, end_row=node_obj_count)
        else:
            update_cell_by_batch(sheet, node_data=node_data, lang_column=None, node_key=column_header.value.lower(),
                                 start_col=column_header.col - 1, end_col=column_header.col - 1, start_row=4,
                                 end_row=node_obj_count)

def main():
    en_node_data = get_en_data()
    master_node_data = get_video_masterlist()
    dubbed_video_node_data(master_node_data, en_node_data)
    spreadsheet = _access_google_spreadsheet()
    update_or_create_spreadsheet(spreadsheet)

    
if __name__ == "__main__":
    main()
