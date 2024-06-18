from pathlib import Path
from geopy.geocoders import Nominatim
import sys
import subprocess
from viktor.core import Storage
import shutil
import pyproj
import requests
import time
import tempfile
from os import listdir
import zipfile
from os.path import isfile, join
from pathlib import Path

import xml.etree.ElementTree as ET
import os
import ezdxf


class Pdok:
    def __init__(self, lon, lat, dir_path):
        # self.street = street
        # self.number = number
        # self.city = city
        # self.country = "Netherlands"
        # self.address = f'{self.street} {self.number}, {self.city}, {self.country}'

        self.rd_coord = [lon, lat]
        self.dir_path = str(dir_path)

    def location_request(self, address):

        geolocator = Nominatim(user_agent="my-app")
        location = geolocator.geocode(address)
        wgs84 = pyproj.CRS('EPSG:4326')
        rd = pyproj.CRS('EPSG:28992')
        transformer = pyproj.Transformer.from_crs(wgs84, rd)
        rd_coord = transformer.transform(location.latitude, location.longitude)

        return rd_coord

    def download_range(self, coord, range):

        x, y = coord
        rad = int(range / 2)

        x1 = x - rad
        x2 = x + rad
        y1 = y - rad
        y2 = y + rad

        range_str = f"POLYGON(({x1} {y1},{x2} {y1},{x2} {y2},{x2} {y1},{x1} {y1}))"
        print(range_str)

        return range_str

    def rename_file_extension(self, directory, old_extension, new_extension):
        # Loop through all files in the directory
        for filename in os.listdir(directory):
            # Check if the file has the old extension
            if filename.endswith(old_extension):
                # Rename the file with the new extension
                new_filename = os.path.splitext(filename)[0] + new_extension
                os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename))

    def settings_bgt(self, poly_range):

        url = 'https://api.pdok.nl/lv/bgt/download/v1_0/delta/custom'
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        data = {
            "featuretypes": [
                "begroeidterreindeel",
                "onbegroeidterreindeel",
                "ondersteunendwaterdeel",
                "ondersteunendwegdeel",
                # "ongeclassificeerdobject",
                "overbruggingsdeel",
                # "overigbouwwerk",
                "spoor",
                "tunneldeel",
                # "vegetatieobject",
                "waterdeel",
                "wegdeel"
            ],
            "format": "citygml",
            "geofilter": poly_range
        }
        settings = {'url': url, 'headers': headers, 'data': data}

        return settings

    def settings_dkk(self, poly_range):
        url = 'https://api.pdok.nl/kadaster/kadastralekaart/download/v5_0/full/custom'
        headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
        data = {
            "featuretypes": [
                "kadastralegrens",
                # "pand"
            ],
            "format": "gml",
            "geofilter": poly_range
        }
        settings = {'url': url, 'headers': headers, 'data': data}

        return settings

    def bgt_request(self, sett_bgt):

        url = sett_bgt.get('url')
        headers = sett_bgt.get('headers')
        data = sett_bgt.get('data')

        response_filter = requests.post(url=url, headers=headers, json=data)
        request_id = response_filter.json().get('downloadRequestId')
        request_id_url = f'https://api.pdok.nl/lv/bgt/download/v1_0/delta/custom/{request_id}/status'

        return request_id_url

    def dkk_request(self, sett_dkk):

        url = sett_dkk.get('url')
        headers = sett_dkk.get('headers')
        data = sett_dkk.get('data')

        response_filter = requests.post(url, headers=headers, json=data)
        print(f'Response status code: {response_filter.status_code}')
        print(f'Response text: {response_filter.text}')
        try:
            print(f'response {response_filter.json()}')
        except requests.exceptions.JSONDecodeError:
            print("Failed to parse the response as JSON.")
        request_id = response_filter.json().get('downloadRequestId')
        print(f'request id {request_id}')
        request_id_url = f'https://api.pdok.nl/kadaster/kadastralekaart/download/v5_0/delta/custom/{request_id}/status'

        return request_id_url

    def unpack(self, download_get):
        with tempfile.TemporaryFile() as fp:
            fp.write(download_get.content)
            fp.seek(0)

            print(tempfile.gettempdir())
            file_name = '/'.join([tempfile.gettempdir(), 'bgt-api-download.zip'])

            with open(file_name, 'wb') as outfile:
                outfile.write(fp.read())
            print(self.dir_path)

            # home_dir = os.path.expanduser('~')
            # downloads_dir = os.path.join(home_dir, 'Downloads')

            # extract_path = '/'.join([self.dir_path, self.address])
            # print(extract_path)


            with zipfile.ZipFile(file_name, "r") as zip_ref:
                zip_ref.extractall(self.dir_path)

            self.rename_file_extension(self.dir_path, '.xml', '.gml')

    def iterate(self, req_url):

        sleeper_amt = 10
        response_list = []

        for i in range(sleeper_amt):
            time.sleep(1)
            response = requests.get(req_url)
            json_response = response.json()
            response_list.append(json_response)

            if response.status_code == 201:
                download = json_response.get('_links').get('download').get('href')
                url_request = f'https://api.pdok.nl{download}'
                download_get = requests.get(url_request)

                self.unpack(download_get)
                print("File downloaded and saved to temp folder.")

                break

            elif response.status_code == 200:
                print("Download running..")

            else:
                print(f"Error: {response.status_code}")

        return response_list

    def run(self, size):
        # rd_coord = self.location_request(self.address)
        poly_range = self.download_range(self.rd_coord, size)

        sett_bgt = self.settings_bgt(poly_range)
        sett_dkk = self.settings_dkk(poly_range)

        req_bgt = self.bgt_request(sett_bgt)
        req_dkk = self.dkk_request(sett_dkk)

        resp_bgt = self.iterate(req_bgt)
        resp_dkk = self.iterate(req_dkk)

        return resp_bgt
