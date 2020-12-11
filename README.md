# acoustic-gdpr-checker
Quickly find which lists in an org contain an email address and submit GDPR erasure jobs

Many orgs have more than one database whereas the GDPR tools in the UI of Acoustic Campaign only support interacting with one database at a time. How can users with tens -- if not hundreds -- of databases check each one for the existence of an email address and quickly submit GDPR erasure jobs to maintain compliance?

![Image of app](https://i.imgur.com/OdHIJ3E.png)

## Requirements

- Python 3.4+
- Bottle web framework (included)
- An Acoustic Campaign org with OAuth access

## Getting Started

1. Download the files from the repo to your local machine.
2. Ensure you have installed Python3 and it's available via commandline.
3. Install the required Python modules: `pip3 install requests xmltodict`
4. In your command line of choice, navigate to where you downloaded the files and execute `python3 main.py`
5. Go to your browser and enter localhost:8080 to view the web app.

## Using the App

You must first accept that this is a proof-of-concept and that you should consult with your legal team about how to properly fulfill GDPR requests.

1. Choose your pod and then paste in your OAuth credentials (Refresh Token/Client ID/Client Secret) and hit submit to authenticate.
2. Enter the email address you wish to check and hit submit.
3. Watch your terminal light up with the API requests executing to check all your databases!
4. Once complete, see the table of all the lists checked. The lists found to contain the email will be in green and allow you to submit a GDPR erasure request.
5. You can monitor the GDPR erasure request from the app by clicking "Check Status".

## Features

- Produces a CSV of the lists checked and any recipient ids found for an email address.
- Logs all requests/responses to a .log file so you can troubleshoot any unexpected responses or retain for compliance purposes.
