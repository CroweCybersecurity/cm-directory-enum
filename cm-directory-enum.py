#! python3

"""
Author:: Eric DePree
Date::   2018
Description:: A tool for enumerating information from Cisco CallManager
"""

import re
import argparse
import requests
from urllib.parse import urlparse
from urllib.parse import parse_qs
import xml.etree.ElementTree as ET

def query_and_print_data(ip_address, port, serach_id, input_format, request_session):
    """Recursive function for doing simple GET requests, XML parsing, data output."""
    xml_tags_regular_expression = re.compile(r'<[^>]+>')

    call_manager_search_url = 'http://{0}:{1}/ccmcip/xmldirectorylist.jsp?start={2}'.format(ip_address, port, serach_id)

    # GET a page from the call manager
    base_response = request_session.get(call_manager_search_url)
    base_response_data = base_response.text

    # Assorted flags and variables for XML processing
    parsed_name = ''
    parsed_telephone = ''
    contact_found = False
    additional_data_found = False

    # Legacy input processing. This may be removed in the future after further testing
    if input_format == 'legacy':
        for line in base_response_data.splitlines():
            # Entering a contact block
            if '<DirectoryEntry>' in line:
                contact_found = True
            # Print and exit a contact block
            elif '</DirectoryEntry>' in line:
                print('{0}\t{1}'.format(parsed_name, parsed_telephone))

                parsed_name = ''
                parsed_telephone = ''
                contact_found = False
            # Entering an XML block with a URL for additional user information
            elif '<Name>Next</Name>' in line:
                additional_data_found = True
            # Recursively get the next page of user information
            elif additional_data_found is True:
                xml_stripped_data = xml_tags_regular_expression.sub('', line).strip()
                parsed_url = urlparse(xml_stripped_data)
                parsed_url_id = parse_qs(parsed_url.query)['start'][0]
                additional_data_found = False

                query_and_print_data(ip_address, port, parsed_url_id, input_format, request_session)
            # Obtain user information from a contact block
            elif contact_found is True and '<Name>' in line:
                parsed_name = xml_tags_regular_expression.sub('', line).strip()
            elif contact_found is True and '<Telephone>' in line:
                parsed_telephone = xml_tags_regular_expression.sub('', line).strip()

    elif input_format == 'xml':
        root = ET.fromstring(base_response_data)

        # Print all contacts from the XML
        for directory_entry in root.findall('DirectoryEntry'):
            directory_name = directory_entry.find('Name')
            directory_telephone = directory_entry.find('Telephone')
            print('{0}\t{1}'.format(directory_name.text, directory_telephone.text))

        # Get the next page of results
        for soft_key_item in root.findall('SoftKeyItem'):
            if soft_key_item.find('Name').text == 'Next':
                parsed_url = urlparse(soft_key_item.find('URL').text)
                parsed_url_id = parse_qs(parsed_url.query)['start'][0]
                query_and_print_data(ip_address, port, parsed_url_id, input_format, request_session)

if __name__ == '__main__':
    # Command line arguments
    parser = argparse.ArgumentParser(description="Enumerate Cisco CallManager information.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    server_group = parser.add_argument_group('directory server parameters')
    server_group.add_argument('-s', dest='server', default='127.0.0.1', required=True, help='IP address')
    server_group.add_argument('-p', dest='port', type=int, default=8080, help='port')
    server_group.add_argument('-i', dest='id', type=int, default=1, help='starting ID')

    parsing_group = parser.add_argument_group('parsing and output parameters')
    parsing_group.add_argument('-f', dest='input_format', choices=['xml', 'legacy'], default='xml',
                               help='the format of informtion recieved from the server')
    args = parser.parse_args()

    # Recursively query user information from the server
    request_session = requests.Session()
    query_and_print_data(args.server, args.port, args.id, args.input_format, request_session)
