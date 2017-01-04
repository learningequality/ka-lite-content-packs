Learning Equality Content pack maker
=================================

Requirements:
-------
- Python 3.5

To start development:
-------

#### Create a virtual environment “content-pack” that you will work in:

- > `sudo pip install virtualenvwrapper`
- > `mkvirtualenv content-pack`
- > `workon content-pack`

#### Install additional development tools:

- > pip install -r requirements.txt
- > pip install -r requirements_dev.txt

#### To create language packs:

- Run `make langpacks` from the project root directory.
- Language packs located at `/out/langpacks/*.zip`

To run all tests, do a `py.test` from the project's root directory.

#### To update the dubbed video mappings.
- Head to Google Developers Console and create a new project (or select the one you have.)
- Google console: https://console.developers.google.com/project
- Under “API & auth”, in the API enable “Drive API”.
- Go to “Credentials” and choose “New Credentials > Service Account Key”.
- Download the json file. Move the .json file in the ~/content-pack-maker/build/credential/
- Rename the file as credential.json
- Share the spreadsheet to the client_email. otherwise you can't access the spreadsheet.
- > Run make dubbed-video-csv

Note: Get the value of the client_mail from the credential.json.
