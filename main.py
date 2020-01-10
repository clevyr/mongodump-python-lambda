import json
from os import environ, mkdir, path
from threading import Timer
import tarfile
from time import strftime, gmtime

import boto3 as boto
from bson import BSON
import hvac
from pymongo import MongoClient
import shutil
import traceback

s3 = boto.resource("s3")

def printProgressBar(iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█'):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print('\r%s |%s| %s%% %s' % (prefix, bar, percent, suffix), end = '\r')
    # Print New Line on Complete
    if iteration == total:
        print()

def renew_token(client):
    try:
        client.renew_token(increment=60 * 60 * 72)
    except hvac.exceptions.InvalidRequest as _:
        # Swallow, as this is probably a root token
        pass
    except hvac.exceptions.Forbidden as _:
        # Swallow, as this is probably a root token
        pass
    except Exception as e:
        exit(e)

def exit(error=None):
    if error is not None:
        print('Error occured, sending email...')
        print(error)
        email(error, environ.get('EMAIL_FROM'), environ.get('EMAIL_TO').split(';'))

def main():
    try:
        vault_secret = environ.get("VAULT_SECRET")
        bucket_name = environ.get("BUCKET_NAME")
        mongo_host = environ.get("MONGO_HOST")
        username = environ.get("MONGO_USERNAME")
        password = environ.get("MONGO_PASSWORD")

        if mongo_host is None:
            import inquirer
            questions = [
                inquirer.Text('mongo_host', message='What is the host of the Mongo instance?'),
                inquirer.Text('username', message='What is the username for mongo?'),
                inquirer.Password('password', message='What is the password for mongo?'),
            ]
            answers = inquirer.prompt(questions)
            mongo_host = answers['mongo_host']
            username = answers['username']
            password = answers['password']

        if vault_secret is not None:
            client = hvac.Client(
                url=environ.get('VAULT_HOST'),
                token=environ.get('VAULT_TOKEN')
            )

            renew_token(client) # Immediately renew, we don't know the TTL

            secret = client.read(vault_secret)['data']
            username = secret['username']
            password = secret['password']

        db_uri = "mongodb://{}:{}@{}/?authSource=admin".format(username, password, mongo_host)
        try:
            client = MongoClient(db_uri)
        except Exception as e:
            exit(e)

        if path.exists("/tmp/dump"):
            shutil.rmtree('/tmp/dump')
        mkdir("/tmp/dump")

        database_names = None
        try:
            database_names = client.list_database_names()
            database_names.remove('config')
        except Exception as e:
            exit(e)

        # For each database
        for db_name in database_names:
            mkdir("/tmp/dump/{}".format(db_name))
            database = client.get_database(db_name)

            # For each collection
            for collection_name in database.list_collection_names():
                # Get collection
                collection = database.get_collection(collection_name)
                # Create metadata.json
                with open("/tmp/dump/{}/{}.metadata.json".format(db_name, collection_name), "w") as f:
                    metadata = {
                        "options": {},
                        "indexes": []
                    }
                    for index in collection.list_indexes():
                        metadata["indexes"].append(index)
                    f.write(json.dumps(metadata, separators=(',',':')))

                # Create bson dump
                with open("/tmp/dump/{}/{}.bson".format(db_name, collection_name), "wb+") as f:
                    print("Dumping {}.{}".format(db_name, collection_name))
                    count = collection.count_documents({})
                    for i, doc in enumerate(collection.find()):
                        printProgressBar(i+1, count)
                        f.write(BSON.encode(doc))

        filename = "/tmp/backup-{}.tgz".format(strftime("%Y-%m-%d_%H%M%S", gmtime()))

        print("Creating {}".format(filename))
        with tarfile.open("{}".format(filename), "w:gz") as tar:
            tar.add("/tmp/dump", arcname=path.basename("dump"))

        if bucket_name is not None:
            s3.Bucket(bucket_name).upload_file(filename, path.basename(filename))
        else:
            print(f"Backup is available at {filename}")
        print("Done")
        exit()
    except Exception as e:
        exit(e)

def email(error, from_address, addresses):
    try:
        ses = boto.client('ses', region_name=environ.get('SES_REGION'))
        bucket_name = environ.get('BUCKET_NAME')
        errString = ''.join(traceback.format_exception(etype=type(error), value=error, tb=error.__traceback__))
        ses.send_email(
            Source=from_address,
            Destination={
                'ToAddresses': addresses
            },
            Message={
                'Subject': {
                    'Data': 'Error: Backup Failed'
                },
                'Body': {
                    'Text': {
                        'Data': f'The database backup for {bucket_name} failed:\n{errString}'
                    }
                }
            }
        )
    except Exception as e:
        print('Error sending email...')
        print(e)

if __name__ == "__main__":
    main()

def lambda_handler(_, __):
    main()
