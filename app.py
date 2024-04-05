import os.path

from viktor import ViktorController
from viktor.parametrization import ViktorParametrization, GeoPointField, TextField, Text, SetParamsButton, \
    ViktorParametrization, Step, TextField, NumberField, SetParamsButton, ActionButton, DownloadButton, OutputField, OptionField, Tab, HiddenField
from viktor.views import MapPolygon, MapView, MapResult, MapPoint, MapLine, Color
from viktor.result import SetParamsResult, DownloadResult
from viktor.errors import UserError
from parts.connector import Pdok
from parts.converter import Converter
from geopy.geocoders import Nominatim
import logging
import pyproj
import shutil
import tempfile
import zipfile
import osgeo
from osgeo import gdal
from osgeo import ogr
from osgeo import osr

from pathlib import Path
import uuid

# print(f'OSGEO VERSION --- {osgeo.__version__}')

# CURRENT VERSION
# viktor-cli publish --registered-name pdok-app --tag v0.1.7.8

def validate_step_1(params, **kwargs):

    if params.width > params.height:
        raise UserError("The design is not feasible")

def coords(params, **kwargs):

    lat = ""
    lon = ""

    if params.search_method == 'Ingevoerde adres':
        if params.street and params.number and params.city:
            address = f'{params.street} {params.number}, {params.city}, Netherlands'
            geolocator = Nominatim(user_agent="my-app")
            location = geolocator.geocode(address)
            lat = location.latitude
            lon = location.longitude
    else:
        if params.drag_location:
            lat = params.drag_location.lat
            lon = params.drag_location.lon

    return f'{lat}, {lon}'

class Parametrization(ViktorParametrization):
    introduction_text = Text(
        "## Welcome bij de PDOK app! \n"
        # "Met behulp van deze app kan je kaartlagen van de BGT en DKK downloaden in .dxf-formaat. "
        # "Selecteer een gebied en bereik, klik op 'verder' om de download te starten."
    )

    search_method = OptionField("### Kies je zoekmethode: \n", options=['Ingevoerde adres', 'Pin-drop'], variant='radio-inline', flex=100)
    coordinaten = OutputField('Coordinaten locatie:', value=coords, flex=100)

    adres_typen = Text("### Voer een adres in: \n")
    street = TextField("""Straatnaam""")
    number = TextField("""Huisnummer""")
    city = TextField("""Plaatsnaam""")

    # zoek_fields = SetParamsButton("Zoek locatie met adres", "", flex=100)
    # bu = ActionButton('Zoek locatie met adres', method='search_location',  flex=100)
    # set_params = SetParamsButton('Set params to some fixed value', method='set_params')

    drag_text = Text("### of gebruik de pin.. \n")
    drag_location = GeoPointField('Klik op de pin en sleep deze op de kaart om een  locatie te selecteren:')
    # zoek_pin = SetParamsButton("Zoek locatie met pin", "", flex=100)

    # download_range = NumberField('', variant='slider', min=100, max=2000, step=100, flex=100)
    download_range = OptionField('#### Straal rondom locatie:', options=[250, 500, 1000], default=500)



    download_range_text = Text(
        "### Download de bestanden \n"
        "Deze knop download de DKK- en BGT-kaarten van de gekozen locatie"
        "De knop bereid de download voor en zet de bestanden om naar DXF"

    )
    download_btn = DownloadButton("Converteer en download", "perform_download", longpoll=True, flex=100)


class Controller(ViktorController):
    label = "My Map Entity Type"
    parametrization = Parametrization

    def download_files(self, dir_path, lon, lat,  range_meters):
        if dir_path.exists():
            # Directory already exists, delete its contents
            for item in dir_path.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
        else:
            # Directory does not exist, create it
            dir_path.mkdir(parents=True)

        log_path = dir_path / "logfile.log"
        logging.basicConfig(filename=log_path, level=logging.INFO)

        base = Pdok(lon, lat,  dir_path)
        base.run(size=range_meters)


    def run_dxf(self, dir_folder, abs_dir_path):
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

        c = Converter(dir_folder, abs_dir_path)
        c.run_converter(export_list_data)

    def search_location(self, params, **kwargs):
        address = f'{params.street} {params.number}, {params.city}, Netherlands'
        geolocator = Nominatim(user_agent="my-app")
        location = geolocator.geocode(address)

        return location

    def location_by_adress(self, address):
        geolocator = Nominatim(user_agent="my-app")
        location = geolocator.geocode(address)
        wgs84 = pyproj.CRS('EPSG:4326')
        rd = pyproj.CRS('EPSG:28992')
        transformer = pyproj.Transformer.from_crs(wgs84, rd)
        rd_coord = transformer.transform(location.latitude, location.longitude)

        return rd_coord

    def filter_and_zip(self, dir_path):
        # Create a temporary file to store the zip archive
        with tempfile.NamedTemporaryFile(delete=False) as tmp_zip:
            # Create a zip archive and add files to it
            with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_DEFLATED) as z:
                # Iterate over files in the directory and add only files with extensions .dxf or .gml to the zip archive
                for file_path in dir_path.iterdir():
                    if file_path.is_file() and (file_path.suffix == '.dxf' or file_path.suffix == '.gml' or file_path.suffix == '.shp'):
                        file_name = file_path.name
                        z.write(file_path, arcname=file_name)

        # Read the zip archive content
        with open(tmp_zip.name, 'rb') as f:
            zip_content = f.read()

        return zip_content

    def perform_download(self, params, **kwargs):
        entity_folder_path = Path(__file__).parent  # entity_type_a
        dir_path = entity_folder_path / 'file_storage'
        abs_dir_path = os.path.abspath(dir_path)

        if params.drag_location and params.search_method == 'Pin-drop':
            print(params.drag_location)
            wgs84_lon = params.drag_location.lon
            wgs84_lat = params.drag_location.lat
            wgs84 = pyproj.CRS('EPSG:4326')
            rd = pyproj.CRS('EPSG:28992')
            transformer = pyproj.Transformer.from_crs(wgs84, rd)
            rd_coord = transformer.transform(wgs84_lat, wgs84_lon)
            lon = rd_coord[0]
            lat = rd_coord[1]

        elif params.street and params.number and params.city and params.search_method == 'Ingevoerde adres':
            rd_coord = self.location_by_adress(params)
            lon = rd_coord[0]
            lat = rd_coord[1]

        else:
            lon = None
            lat = None

        range_meters = params.download_range
        self.download_files(dir_path, lon, lat, range_meters)
        self.run_dxf(dir_path, abs_dir_path)
        zip_content = self.filter_and_zip(dir_path)

        # Return a DownloadResult with the zip content and file name
        return DownloadResult(zip_content, file_name="my_file.zip")


    @MapView('PDOK kaart', duration_guess=1)
    def get_map_view(self, params, **kwargs):
        # Create points using the provided street, number, and city
        features = []
        print(params)
        print(f'OSGEO VERSION --- {osgeo.__version__}')
        # print(ogr.__version__)

        if params.drag_location and params.search_method == 'Pin-drop':
            features.append(MapPoint.from_geo_point(params.drag_location))
            print(params.drag_location.lat)

        if params.street and params.number and params.city:
            address = f'{params.street} {params.number}, {params.city}, Netherlands'
            geolocator = Nominatim(user_agent="my-app")
            location = geolocator.geocode(address)
            lat = location.latitude
            lon = location.longitude

            if params.search_method == 'Ingevoerde adres':
                features.append(MapPoint(lat, lon))
                params.data = [lat, lon]


        return MapResult(features)



if __name__ == "__main__":
    pass