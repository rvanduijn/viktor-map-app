import os
import time
import tempfile
import zipfile
import requests
import pyproj
from geopy.geocoders import Nominatim
from PIL import Image
from io import BytesIO


class Pdok:
    def __init__(self, lon, lat, dir_path):
        self.rd_coord = [lon, lat]
        self.dir_path = str(dir_path)

    def _geocode_address(self, address):
        geolocator = Nominatim(user_agent="my-app")
        location = geolocator.geocode(address)
        wgs84 = pyproj.CRS('EPSG:4326')
        rd = pyproj.CRS('EPSG:28992')
        transformer = pyproj.Transformer.from_crs(wgs84, rd)
        rd_coord = transformer.transform(location.latitude, location.longitude)
        return rd_coord

    def _create_polygon_range(self, coord, range):
        x, y = coord
        rad = int(range / 2)
        x1, x2 = x - rad, x + rad
        y1, y2 = y - rad, y + rad
        return f"POLYGON(({x1} {y1},{x2} {y1},{x2} {y2},{x2} {y1},{x1} {y1}))"

    def _rename_file_extension(self, directory, old_extension, new_extension):
        for filename in os.listdir(directory):
            if filename.endswith(old_extension):
                new_filename = os.path.splitext(filename)[0] + new_extension
                os.rename(os.path.join(directory, filename), os.path.join(directory, new_filename))

    def _prepare_request_settings(self, poly_range, bgt=True):
        base_urls = {
            'bgt': 'https://api.pdok.nl/lv/bgt/download/v1_0/delta/custom',
            'dkk': 'https://api.pdok.nl/kadaster/kadastralekaart/download/v5_0/full/custom'
        }
        feature_types = {
            'bgt': [
                "begroeidterreindeel", "onbegroeidterreindeel", "ondersteunendwaterdeel",
                "ondersteunendwegdeel", "overbruggingsdeel", "spoor", "tunneldeel",
                "waterdeel", "wegdeel"
            ],
            'dkk': ["kadastralegrens"]
        }
        formats = {
            'bgt': 'citygml',
            'dkk': 'gml'
        }

        service_type = 'bgt' if bgt else 'dkk'

        url = base_urls[service_type]
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        data = {
            "featuretypes": feature_types[service_type],
            "format": formats[service_type],
            "geofilter": poly_range
        }
        return {'url': url, 'headers': headers, 'data': data}

    def _request_data(self, settings):
        response = requests.post(settings['url'], headers=settings['headers'], json=settings['data'])
        try:
            request_id = response.json().get('downloadRequestId')
        except requests.exceptions.JSONDecodeError:
            print("Failed to parse the response as JSON.")
            return None
        return f"{settings['url']}/{request_id}/status"

    def _get_wms_image(self, lat, lon, range):
        wms_url = "https://service.pdok.nl/hwh/luchtfotorgb/wms/v1_0"
        bbox = f"{lon - range},{lat - range},{lon + range},{lat + range}"
        params = {
            'service': 'WMS',
            'request': 'GetMap',
            'version': '1.3.0',
            'layers': 'Actueel_orthoHR',
            'styles': '',
            'crs': 'EPSG:28992',
            'bbox': bbox,
            'width': 1000,
            'height': 1000,
            'format': 'image/jpeg'
        }
        response = requests.get(wms_url, params=params)
        image = Image.open(BytesIO(response.content))
        return image

    def _unpack_zip(self, content, wms_image, wms_image_zoom):
        with tempfile.TemporaryFile() as fp:
            fp.write(content)
            fp.seek(0)
            zip_file_path = os.path.join(tempfile.gettempdir(), 'bgt-api-download.zip')
            with open(zip_file_path, 'wb') as outfile:
                outfile.write(fp.read())

            # Extract and add WMS image
            with zipfile.ZipFile(zip_file_path, "a") as zip_ref:
                zip_ref.extractall(self.dir_path)
                wms_image_path = os.path.join(self.dir_path, 'wms_image.jpg')
                wms_image.save(wms_image_path)
                zip_ref.write(wms_image_path, 'wms_image.jpg')

                wms_image_path_zoom = os.path.join(self.dir_path, 'wms_image_zoom.jpg')
                wms_image_zoom.save(wms_image_path_zoom)
                zip_ref.write(wms_image_path_zoom, 'wms_image_zoom.jpg')

            self._rename_file_extension(self.dir_path, '.xml', '.gml')


    def _poll_status(self, req_url):
        sleeper_amt = 10
        response_list = []
        for _ in range(sleeper_amt):
            time.sleep(1)
            response = requests.get(req_url)
            response_list.append(response.json())
            if response.status_code == 201:
                download_url = f"https://api.pdok.nl{response.json().get('_links').get('download').get('href')}"
                download_get = requests.get(download_url)
                return download_get.content

            elif response.status_code == 200:
                print("Download running..")

            else:
                print(f"Error: {response.status_code}")
        return None

    def run(self, size):
        poly_range = self._create_polygon_range(self.rd_coord, size)
        bgt_settings = self._prepare_request_settings(poly_range, bgt=True)
        dkk_settings = self._prepare_request_settings(poly_range, bgt=False)
        # print(dkk_settings)
        bgt_req_url = self._request_data(bgt_settings)
        dkk_req_url = self._request_data(dkk_settings)
        # print(dkk_req_url)
        bgt_content = self._poll_status(bgt_req_url)
        dkk_content = self._poll_status(dkk_req_url)

        wms_image = self._get_wms_image(self.rd_coord[1], self.rd_coord[0], 500)
        wms_image_zoom = self._get_wms_image(self.rd_coord[1], self.rd_coord[0], 50)

        try:
            contents = {'bgt': bgt_content, 'dkk': dkk_content}
            for key, content in contents.items():
                if content:
                    self._unpack_zip(content, wms_image, wms_image_zoom)
            print("Files downloaded and saved to temp folder.")
        except Exception as e:
            print(f"Failed to download some files. Error: {e}")


        # if bgt_content and dkk_content:
        #     self._unpack_zip(bgt_content, wms_image, wms_image_zoom)
        #     self._unpack_zip(dkk_content, wms_image, wms_image_zoom)
        #     print("Files downloaded and saved to temp folder.")
        # else:
        #     print("Failed to download some files.")

        return bgt_content, dkk_content
