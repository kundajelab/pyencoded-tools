import hashlib
import os.path
import subprocess
import time
import csv
import encodedcc
import argparse
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(filename="log.txt", filemode="w", format='%(message)s', level=logging.INFO)
logging.getLogger("requests").setLevel(logging.WARNING)
#############################
# Set defaults


def getArgs():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        )
    parser.add_argument('--infile',
                        help="TSV file with data, needs headers")
    parser.add_argument('--key',
                        default='default',
                        help="The keypair identifier from the keyfile.  \
                        Default is --key=default")
    parser.add_argument('--keyfile',
                        default=os.path.expanduser("~/keypairs.json"),
                        help="The keypair file.  Default is --keyfile=%s" % (os.path.expanduser("~/keypairs.json")))
    parser.add_argument('--debug',
                        default=False,
                        action='store_true',
                        help="Print debug messages.  Default is False.")
    parser.add_argument('--update',
                        default=False,
                        action="store_true",
                        help="Allows script to update, default is false")
    args = parser.parse_args()
    return args


class NewFile():
    def __init__(self, dictionary):
        self.data = dictionary
        self.post_input = {}
        # get controlled_by list
        if dictionary.get("controlled_by"):
            control = dictionary.pop("controlled_by")
            self.post_input["controlled_by"] = control.split(",")
        # get aliases list
        if dictionary.get("aliases"):
            alias = dictionary.pop("aliases")
            self.post_input["aliases"] = alias.split(",")
        # make flowcell dict
        flowcell_dict = {}
        for val in ["lane", "barcode", "flowcell", "machine"]:
            flowcell_dict[val] = dictionary.pop(val)
        # make post_input dict
        path = dictionary.pop("file_path")
        for key in dictionary.keys():
            if key == "submitted_file_name":
                if any(dictionary.get("submitted_file_name")):
                    self.post_input["submitted_file_name"] = dictionary["submitted_file_name"]
                else:
                    self.post_input["submitted_file_name"] = path.rsplit("/", 1)[-1]
            else:
                if dictionary.get(key):
                    self.post_input[key] = dictionary[key]
        # add flowcell_details to post_input
        self.post_input["flowcell_details"] = [flowcell_dict]
        # calculate

        md5sum = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024*1024), b''):
                md5sum.update(chunk)
        # add md5sum to post_input
        self.post_input["md5sum"] = md5sum.hexdigest()

    def post_file(self, connection):

        ####################
        # POST metadata
        r = encodedcc.new_ENCODE(connection, "files", self.post_input)
        print(r)
        #####################
        # POST file to S3
        '''item = r["@graph"][0]
        creds = item['upload_credentials']
        env = os.environ.copy()
        env.update({
            'AWS_ACCESS_KEY_ID': creds['access_key'],
            'AWS_SECRET_ACCESS_KEY': creds['secret_key'],
            'AWS_SECURITY_TOKEN': creds['session_token'],
        })
        print("Uploading file.")
        path = self.data["file_path"]
        print(path)
        start = time.time()
        subprocess.check_call(['aws', 's3', 'cp', path, creds['upload_url']], env=env)
        end = time.time()
        duration = end - start
        print("Uploaded in %.2f seconds" % duration)'''

######################
# Main


def main():
    args = getArgs()
    key = encodedcc.ENC_Key(args.keyfile, args.key)
    connection = encodedcc.ENC_Connection(key)
    print("Running on", connection.server)
    if args.update:
        print("This is an UPDATE run, data will be changed")
    else:
        print("This is a TEST run, nothing gets altered")
    with open(args.infile, "r") as tsvfile:
        reader = csv.DictReader(tsvfile, delimiter='\t')
        for row in reader:
            newF = NewFile(row)
            if args.update:
                newF.post_file(connection)
            else:
                print("Data to POST: ", newF.post_input)

if __name__ == '__main__':
    main()