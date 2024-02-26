from viktor import ViktorController
from viktor.parametrization import ViktorParametrization, GeoPointField, TextField, Text, SetParamsButton, \
    ViktorParametrization, Step, TextField, NumberField, SetParamsButton, ActionButton, DownloadButton
from viktor.views import MapPolygon, MapView, MapResult, MapPoint, MapLine, Color
from viktor.result import SetParamsResult, DownloadResult
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

# viktor-cli publish --registered-name <insert-app-name-here> --tag v0.1.0
### NO PERMISSION? /// STUCK

#
# try:
#     import osr
#     import ogr
#     print("modules 'osr' and 'ogr' are installed")
# except ImportError:
#     print("modules 'osr' and 'ogr' are not installed")
#     # Install GDAL dependencies
#     subprocess.check_call(['apt-get', 'update'])
#     subprocess.check_call(['apt-get', 'install', 'gdal-bin', 'libgdal-dev'])
#     # Install GDAL package
#     subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'GDAL'])

dev = False

# try:
#     import osgeo
#     print("modules 'osgeo.osr' and 'osgeo.ogr' are installed")
# except ImportError:
#     print("modules 'osgeo.osr' and 'osgeo.ogr' are not installed")
#     # Path to the local GDAL wheel file
#     if dev:
#         gdal_wheel_path = f"{Path(__file__).parent}/required_wheel/GDAL-3.2.3-cp39-cp39-win_amd64.whl"  # Adjust this path as needed
#     else:
#         gdal_wheel_path = f"{Path(__file__).parent}/required_wheel/GDAL-3.7.3-cp39-cp39-linux_x86_64.whl"  # Adjust this path as needed
#     # Install GDAL from the local wheel file
#     subprocess.check_call([sys.executable, "-m", "pip", "install", gdal_wheel_path])

from osgeo import ogr
from osgeo import osr

class Pdok:
    def __init__(self, street, number, city):
        self.street = street
        self.number = number
        self.city = city
        self.country = "Netherlands"
        self.address = f'{self.street} {self.number}, {self.city}, {self.country}'

        entity_folder_path = Path(__file__).parent  # entity_type_a
        self.dir_path = str(entity_folder_path.parent / 'file_storage')

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
                "ongeclassificeerdobject",
                "overbruggingsdeel",
                "overigbouwwerk",
                "spoor",
                "tunneldeel",
                "vegetatieobject",
                "waterdeel",
                "wegdeel"
            ],
            "format": "citygml",
            "geofilter": poly_range
        }
        settings = {'url': url, 'headers': headers, 'data': data}

        return settings

    def settings_dkk(self, poly_range):
        url = 'https://api.pdok.nl/kadaster/kadastralekaart/download/v4_0/full/custom'
        headers = {'accept': 'application/json', 'Content-Type': 'application/json'}
        data = {
            "featuretypes": [
                "kadastralegrens",
                "pand"
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
        request_id = response_filter.json().get('downloadRequestId')
        request_id_url = f'https://api.pdok.nl/kadaster/kadastralekaart/download/v4_0/delta/custom/{request_id}/status'

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
            extract_path = '/'.join([self.dir_path, self.address])



            with zipfile.ZipFile(file_name, "r") as zip_ref:
                zip_ref.extractall(extract_path)

            self.rename_file_extension(extract_path, '.xml', '.gml')

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

    def run(self, size=1000):

        rd_coord = self.location_request(self.address)
        poly_range = self.download_range(rd_coord, size)

        sett_bgt = self.settings_bgt(poly_range)
        sett_dkk = self.settings_dkk(poly_range)

        req_bgt = self.bgt_request(sett_bgt)
        req_dkk = self.dkk_request(sett_dkk)

        resp_bgt = self.iterate(req_bgt)
        resp_dkk = self.iterate(req_dkk)

        return resp_bgt

class GmlConverter:
    def __init__(self, file_path):
        self.namespace = {
            't': 'http://www.opengis.net/citygml/transportation/2.0',
            'imgeo': 'http://www.geostandaarden.nl/imgeo/2.1',
            'gml': 'http://www.opengis.net/gml'}
        # self.file_path = os.path.expanduser(f"~/Downloads/{file_path}")
        self.file_path = file_path

    def create_dxf(self, file_name):
        dxf_path = f'{self.file_path}{file_name}.dxf'

        doc = ezdxf.new(dxfversion='R2010')

        # Create a new DXF model space
        msp = doc.modelspace()

        return [doc, msp, dxf_path]

    def get_gml(self, file_name):
        gml_path = f'{self.file_path}{file_name}.gml'
        print(gml_path)
        # Load the XML file
        tree = ET.parse(gml_path)
        root = tree.getroot()

        # Find the Polygon element
        # polygons = root.findall('.//t:TrafficArea/imgeo:geometrie2dWegdeel/gml:Polygon', self.namespace)
        polygons = root.findall('.//gml:posList', self.namespace)
        # temp_fix dkk_kadastralegrens

        if len(polygons) == 0:
            polygons = root.findall('.//gml:posList', {
            't': 'http://www.opengis.net/citygml/transportation/2.0',
            'imgeo': 'http://www.geostandaarden.nl/imgeo/2.1',
            'gml': 'http://www.opengis.net/gml/3.2'})

        return polygons

    def off_convert(self, polygons, dxf_file):
        for polygon in polygons:
            # Extract the coordinates from the posList element
            pos_list = polygon.findall('.//gml:posList', self.namespace)[0].text.split()
            coordinates = [(float(pos_list[i]), float(pos_list[i + 1])) for i in range(0, len(pos_list), 2)]
            pts = len(coordinates)

            if pts > 2:
                print(coordinates)
                # create hatch object
                hatch = dxf_file.add_hatch(color=2, dxfattribs={'layer': 'test'})#'rgb':(0, 0, 0)})
                hatch.paths.add_polyline_path(coordinates, is_closed=True)

            # else:
            dxf_file.add_lwpolyline(coordinates)

    def convert(self, polygons, dxf_file, layer_name, color_number, z_offset):
        # Extract the coordinates from each posList element

        coordinates_list = []
        for pos_list in polygons:
            pos_list_text = pos_list.text.strip()
            if pos_list_text:
                pos_list_values = pos_list_text.split()
                coordinates = [(float(pos_list_values[i]), float(pos_list_values[i + 1])) for i in
                               range(0, len(pos_list_values), 2)]
                coordinates_list.append(coordinates)

                pts = len(coordinates)

                if layer_name == "dkk_kadastralegrens":
                    dxf_file.add_lwpolyline(coordinates, dxfattribs={'layer': layer_name})

                elif pts > 2:
                    # print(coordinates)
                    # create hatch object
                    hatch = dxf_file.add_hatch(dxfattribs={'layer': layer_name, 'color': color_number})
                    hatch.paths.add_polyline_path(coordinates, is_closed=False)

                dxf_file.add_lwpolyline(coordinates)





    def run(self, file_name, color_number, z_offset, combined_file):
        data = self.get_gml(file_name)
        layer_name = file_name


        if combined_file:
            file_name = 'combined_file'

        cr_dxf = self.create_dxf(file_name)
        doc = cr_dxf[0]
        # doc.layers.add(name=layer_name)

        dxf_file = cr_dxf[1]
        dxf_path = cr_dxf[2]
        self.convert(data, dxf_file, layer_name, color_number, z_offset)

        # layer = doc.layers.get(layer_name)

        doc.saveas(dxf_path)

    def run_combined(self, export_list):
        cr_dxf = self.create_dxf('combined_file')
        dxf_file = cr_dxf[1]
        dxf_path = cr_dxf[2]
        doc = cr_dxf[0]

        for item in export_list:
            layer_name = item.get('layer')
            color_number = item.get('color')
            z_offset = item.get('z-offset')
            data = self.get_gml(layer_name)
            # doc.layers.add(name=layer_name)
            self.convert(data, dxf_file, layer_name, color_number, z_offset)

            # layer = doc.layers.get(layer_name)

        doc.saveas(dxf_path)


class Converter:
    def __init__(self, file_path):
        self.file_path = os.path.expanduser(file_path)

    def convert_to_shp(self, file_name):

        # Input GML file path
        # input_gml_path = "../test_files/bgt_wegdeel.gml"
        input_gml_path = f'{self.file_path}{file_name}.gml'

        # Input Shapefile file path
        # input_shp_path = "../test_files/output.shp"
        output_shp_path = f'{self.file_path}{file_name}.shp'

        # Define driver for Shapefile format
        driver = ogr.GetDriverByName("ESRI Shapefile")

        # Create a new Shapefile dataset
        out_ds = driver.CreateDataSource(output_shp_path)

        # Create a spatial reference object for the GML file
        srs = osr.SpatialReference()
        srs.ImportFromXML(open(input_gml_path, "r").read())

        # Create a new layer in the Shapefile
        layer = out_ds.CreateLayer("output_layer", srs, ogr.wkbUnknown)

        # Read features from the GML file
        src_ds = ogr.Open(input_gml_path)
        layer_source = src_ds.GetLayerByIndex(0)

        # Parse features and add them to the Shapefile layer
        for feature in layer_source:
            new_feature = ogr.Feature(layer.GetLayerDefn())
            new_feature.SetGeometry(feature.GetGeometryRef())  # Set geometry directly

            # Copy attributes from the GML feature to the Shapefile feature
            for i in range(feature.GetFieldCount()):
                try:
                    field_name = feature.GetFieldDefnRef(i).GetNameRef()
                    new_feature.SetField(field_name, feature.GetField(i))
                except:
                    pass

            layer.CreateFeature(new_feature)

        # Close the Shapefile dataset
        out_ds = None
        src_ds = None

    def shp_to_dxf(self, file_name, layer_name, color):

        # Input Shapefile file path
        # input_shp_path = "../test_files/output.shp"
        input_shp_path = f'{self.file_path}{file_name}.shp'

        # Output DXF file path
        # output_dxf_path = "../test_files/output.dxf"
        output_dxf_path = f'{self.file_path}{file_name}.dxf'

        # Layer name and color
        layer_name = layer_name
        color = color

        # Run ogr2ogr command for conversion with layer color
        ogr2ogr_command = [
            "ogr2ogr",
            "-f",
            "DXF",
            output_dxf_path,
            input_shp_path,
            "-nln",
            layer_name,
            "-oo",
            f"LayerColor={color}",
        ]

        # Run ogr2ogr command for conversion
        # ogr2ogr_command = ["ogr2ogr", "-f", "DXF", output_dxf_path, input_shp_path]
        # ogr2ogr_command = ["ogr2ogr", "-f", "DXF", output_dxf_path, input_shp_path, "-nln", file_name]

        subprocess.run(ogr2ogr_command)

        # Print a message indicating successful conversion
        print("Shapefile successfully converted to DXF.")

    def combine_dxf(self, export_list):
        # Output combined DXF file path
        output_combined_dxf_path = "combined_output.dxf"

        # # List of input DXF files to be combined with their corresponding layer names and colors
        # input_dxf_files = [("output.dxf", "Layer1", (255, 0, 0)),  # Layer1 with RGB color (255,0,0) for red
        #                    ("output2.dxf", "Layer3", (0, 0, 255))]  # Layer3 with RGB color (0,0,255) for blue

        input_dxf_files = []
        for i in export_list:
            name = i.get('layer')
            layer_setting = (f'{self.file_path}{name}.dxf', i.get('feature'), i.get('color_rgb'))
            input_dxf_files.append(layer_setting)


        # Create a new DXF document for the combined output
        doc = ezdxf.new("R2010")

        # Combine DXF files and set layer colors
        for input_dxf_file, layer_name, layer_color in input_dxf_files:
            # Load the input DXF file
            with ezdxf.readfile(input_dxf_file) as source_doc:
                # Create a new block reference for the entire content of the source document
                source_block = doc.modelspace().insert_block(source_doc.modelspace())

                # Set the layer name and color for the block reference
                source_block.set_attrib(layer=layer_name, color=layer_color)

        # Save the combined DXF document
        doc.saveas(output_combined_dxf_path)

        # Print a message indicating successful combination with layer names and colors
        print("DXF files successfully combined with specified layer names and colors using ezdxf.")


    def merge(self, input_files):
        # Create a target DXF file
        target_dxf = ezdxf.new("R2010")

        # Get modelspace of target DXF file
        target_modelspace = target_dxf.modelspace()

        # Iterate over input DXF files
        for input_file in input_files:
            feature = input_file.get('feature')
            layer = input_file.get('layer')
            color = input_file.get('color_aci')
            filename = f'{self.file_path}{layer}.dxf'

            # Read the input DXF file
            input_dxf = ezdxf.readfile(filename)
            input_dxf.layers.add(name=feature, color=color)

            # Iterate over entities in the modelspace of the input DXF file
            for entity in input_dxf.modelspace():
                entity.dxf.layer = feature
                # Copy entity to the modelspace of the target DXF file
                target_modelspace.add_entity(entity.copy())

        # Save the merged DXF file
        combined = f'{self.file_path}PDOK_combined.dxf'
        target_dxf.saveas(combined)




    def run_converter(self, export_list_data):
        print(self.file_path)
        base_dxf = ezdxf.new()
        combined = f'{self.file_path}combined-file.dxf'

        layers = []
        export_list_trimmed = []
        for e, i in enumerate(export_list_data):
            try:
                feature = i.get('feature')
                name = i.get('layer')
                color = i.get('color_aci')
                filename = f'{self.file_path}{name}.dxf'
                layers.append(filename)

                print(name)
                self.convert_to_shp(name)
                self.shp_to_dxf(name, layer_name=feature, color=color)
                export_list_trimmed.append(i)

            except:
                print(f"an error occured during iteration {e}.")

        self.merge(export_list_trimmed)


class Parametrization(ViktorParametrization):
    # step_1 = Step('Step 1 - without views')
    introduction_text = Text(
        "## Welcome bij de PDOK app! \n"
        "Met behulp van deze app kan je kaartlagen van de BGT en DKK downloaden in .dxf-formaat"
        "Selecteer een gebied en bereik, klik op 'verder' om de download te starten"
    )

    street = TextField("""Straatnaam""")
    number = TextField("""Huisnummer""")
    city = TextField("""Plaatsnaam""")
    # country = "Netherlands"
    zoek_fields = SetParamsButton("Zoek locatie met adres", "", flex=100)

    drag_text = Text("### OF gebruik de pin.. \n")
    drag_location = GeoPointField('Klik op de pin en sleep deze op de kaart om een  locatie te selecteren:')
    zoek_pin = SetParamsButton("Zoek locatie met pin", "", flex=100)

    reach_text = Text("### Download-bereik (m): \n")
    download_range = NumberField('', variant='slider', min=100, max=2000, step=100, flex=100)

    button = ActionButton('Download omgeving', method='perform_action')
    download_btn = DownloadButton("Download file", "perform_download", longpoll=True)


# if __name__ == "__main__":
#     street = "Schoutendreef"
#     number = "59"
#     city = "Den Haag"
#
#     # cl = Pdok("Schoutendreef", "59", "Den Haag")
#     cl = Pdok(street, number, city)
#     cl.run()


class Controller(ViktorController):
    label = "My Map Entity Type"
    parametrization = Parametrization

    def run_dxf(self, folder_name):
        # gml = GmlConverter(folder_name)
        #
        # export_list = [
        #     {'layer': "dkk_pand", 'color': 254},
        #     {'layer': "dkk_kadastralegrens", 'color': 251},
        #     {'layer': "bgt_begroeidterreindeel", 'color': 253},
        #     {'layer': "bgt_onbegroeidterreindeel", 'color': 83},
        #     {'layer': "bgt_ondersteunendwaterdeel", 'color': 115},
        #     {'layer': "bgt_ondersteunendwegdeel", 'color': 85},
        #     {'layer': "bgt_ongeclassificeerdobject", 'color': 0},
        #     # {'layer': "bgt_overigbouwwerk", 'color': 0},
        #     # {'layer': "bgt_spoor", 'color': 0},
        #     # {'layer': "bgt_tunneldeel", 'color': 0},
        #     {'layer': "bgt_waterdeel", 'color': 153},
        #     {'layer': "bgt_wegdeel", 'color': 252},
        # ]
        #
        # # for item in export_list:
        # #     gml.run(item.get('layer'), item.get('color'))
        #
        # gml.run_combined(export_list)


        export_list_data = [
            {'service': 'dkk', 'feature': 'pand', 'layer': "dkk_pand", 'color_rgb': (), 'color_aci': 254, "z_value": 0},
            {'service': 'dkk', 'feature': 'kadastralegrens', 'layer': "dkk_kadastralegrens", 'color_rgb': (),
             'color_aci': 251, "z_value": -10},
            {'service': 'bgt', 'feature': 'begroeidterreindeel', 'layer': "bgt_begroeidterreindeel", 'color_rgb': (),
             'color_aci': 253, "z_value": -50},
            {'service': 'bgt', 'feature': 'onbegroeidterreindeel', 'layer': "bgt_onbegroeidterreindeel",
             'color_rgb': (), 'color_aci': 83, "z_value": -40},
            {'service': 'bgt', 'feature': 'ondersteunendwaterdeel', 'layer': "bgt_ondersteunendwaterdeel",
             'color_rgb': (), 'color_aci': 115, "z_value": -60},
            {'service': 'bgt', 'feature': 'ondersteunendwegdeel', 'layer': "bgt_ondersteunendwegdeel", 'color_rgb': (),
             'color_aci': 85, "z_value": -20},
            {'service': 'bgt', 'feature': 'ongeclassificeerdobject', 'layer': "bgt_ongeclassificeerdobject",
             'color_rgb': (), 'color_aci': 0, "z_value": -5},
            {'service': 'bgt', 'feature': 'waterdeel', 'layer': "bgt_waterdeel", 'color_rgb': (166, 166, 166),
             'color_aci': 153, "z_value": -70},
            {'service': 'bgt', 'feature': 'wegdeel', 'layer': "bgt_wegdeel", 'color_rgb': (171, 187, 205),
             'color_aci': 252, "z_value": -30},
        ]
        c = Converter(folder_name)
        c.run_converter(export_list_data)

    def perform_action(self, params, **kwargs):
        address = f'{params.street} {params.number}, {params.city}, Netherlands'
        print(address)
        base = Pdok(params.street, params.number, params.city)
        base.run()
        print(base)


    def perform_download(self, params, **kwargs):
        # Prepare the path where files are located
        entity_folder_path = Path(__file__).parent  # entity_type_a
        dir_path = entity_folder_path.parent / 'file_storage'
        path = Path(dir_path, f"{params.street} {params.number}, {params.city}, Netherlands")


        self.run_dxf(f'{path}/')

        # Create a temporary file to store the zip archive
        with tempfile.NamedTemporaryFile(delete=False) as tmp_zip:
            # Create a zip archive and add files to it
            with zipfile.ZipFile(tmp_zip, 'w', zipfile.ZIP_DEFLATED) as z:
                # Iterate over files in the directory and add them to the zip archive
                for file_path in path.iterdir():
                    file_name = file_path.name
                    z.write(file_path, arcname=file_name)

        # Read the zip archive content
        with open(tmp_zip.name, 'rb') as f:
            zip_content = f.read()

        # Return a DownloadResult with the zip content and file name
        return DownloadResult(zip_content, file_name="my_file.zip")


    @MapView('Map view', duration_guess=1)
    def get_map_view(self, params, **kwargs):
        # Create points using the provided street, number, and city
        features = []

        def location_request(address):
            geolocator = Nominatim(user_agent="my-app")
            location = geolocator.geocode(address)
            wgs84 = pyproj.CRS('EPSG:4326')
            rd = pyproj.CRS('EPSG:28992')
            transformer = pyproj.Transformer.from_crs(wgs84, rd)
            rd_coord = transformer.transform(location.latitude, location.longitude)

            return rd_coord


        return MapResult(features)

if __name__ == "__main__":
    # entity_folder_path = Path(__file__).parent  # entity_type_a
    # file_path = entity_folder_path.parent / 'file_storage'
    # print(file_path)
    # # with file_path.open() as f:

    pass