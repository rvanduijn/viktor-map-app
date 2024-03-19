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
from osgeo import ogr
from osgeo import osr
from pathlib import Path
import uuid

print(f'OSGEO VERSION --- {osgeo.__version__}')

# CURRENT VERSION
# viktor-cli publish --registered-name pdok-app --tag v0.1.7.1

def validate_step_1(params, **kwargs):

    if params.step_1.width > params.step_1.height:
        raise UserError("The design is not feasible")

def coords(params, **kwargs):

    lat = ""
    lon = ""

    if params.step_1.search_method == 'Ingevoerde adres':
        if params.step_1.street and params.step_1.number and params.step_1.city:
            address = f'{params.step_1.street} {params.step_1.number}, {params.step_1.city}, Netherlands'
            geolocator = Nominatim(user_agent="my-app")
            location = geolocator.geocode(address)
            lat = location.latitude
            lon = location.longitude
    else:
        if params.step_1.drag_location:
            lat = params.step_1.drag_location.lat
            lon = params.step_1.drag_location.lon

    return f'{lat}, {lon}'

class Parametrization(ViktorParametrization):
    step_1 = Tab('Selecteer de locatie')
    step_1.introduction_text = Text(
        "## Welcome bij de PDOK app! \n"
        "Met behulp van deze app kan je kaartlagen van de BGT en DKK downloaden in .dxf-formaat. "
        "Selecteer een gebied en bereik, klik op 'verder' om de download te starten."
    )

    step_1.street = TextField("""Straatnaam""")
    step_1.number = TextField("""Huisnummer""")
    step_1.city = TextField("""Plaatsnaam""")

    # zoek_fields = SetParamsButton("Zoek locatie met adres", "", flex=100)
    # step_1.bu = ActionButton('Zoek locatie met adres', method='search_location',  flex=100)
    # step_1.set_params = SetParamsButton('Set params to some fixed value', method='set_params')

    step_1.drag_text = Text("### OF gebruik de pin.. \n")
    step_1.drag_location = GeoPointField('Klik op de pin en sleep deze op de kaart om een  locatie te selecteren:')
    # step_1.zoek_pin = SetParamsButton("Zoek locatie met pin", "", flex=100)

    step_1.resultaat = Text("### Resultaat: \n")
    step_1.search_method = OptionField('Zoekmethode', options=['Ingevoerde adres', 'Pin-drop'], variant='radio-inline', flex=100)
    step_1.coordinaten = OutputField('Coordinaten locatie:', value=coords, flex=100)


    step_2 = Tab('Download de bestanden')
    step_2.step_2 = Text(
        "## Welcome op de dowload-pagina! \n"
        "Op deze pagina kan je de gewenste bestanden downloaden. "
        "LET OP: momenteel kan je nog geen download-bereik instellen."
    )

    # step_2.reach_text = Text("### Download-bereik: \n")
    # step_2.download_range = NumberField('', variant='slider', min=100, max=2000, step=100, flex=100)

    step_2.download_range_text = Text(
        "### Stap 1 \n"
        "Klik eerst op 'Haal bestanden binnen'"
        "Deze knop download de DKK- en BGT-kaarten van de gekozen locatie"
    )
    step_2.button = ActionButton('Haal bestanden binnen', method='perform_action', flex=100)

    step_2.introduction_text = Text(
        "### Stap 2 \n"
        "Klik vervolgens op 'Converteer en download'"
        "De knop bereid de download voor en zet de bestanden om naar DXF"
    )
    step_2.download_btn = DownloadButton("Converteer en download", "perform_download", longpoll=True, flex=100)


class Controller(ViktorController):
    label = "My Map Entity Type"
    parametrization = Parametrization

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

    # def run_dxf(self, folder_name):
    #     export_list = [
    #         {'layer': "dkk_pand", 'color': 254},
    #         {'layer': "dkk_kadastralegrens", 'color': 251},
    #         {'layer': "bgt_begroeidterreindeel", 'color': 253},
    #         {'layer': "bgt_onbegroeidterreindeel", 'color': 83},
    #         {'layer': "bgt_ondersteunendwaterdeel", 'color': 115},
    #         {'layer': "bgt_ondersteunendwegdeel", 'color': 85},
    #         {'layer': "bgt_ongeclassificeerdobject", 'color': 0},
    #         # {'layer': "bgt_overigbouwwerk", 'color': 0},
    #         # {'layer': "bgt_spoor", 'color': 0},
    #         # {'layer': "bgt_tunneldeel", 'color': 0},
    #         {'layer': "bgt_waterdeel", 'color': 153},
    #         {'layer': "bgt_wegdeel", 'color': 252},
    #     ]
    #
    #     gml = GmlConverter(folder_name)
    #     gml.run_combined(export_list)

    def search_location(self, params, **kwargs):
        address = f'{params.step_1.street} {params.step_1.number}, {params.step_1.city}, Netherlands'
        geolocator = Nominatim(user_agent="my-app")
        location = geolocator.geocode(address)

        return location

    def perform_action(self, params, **kwargs):
        # address = f'{params.step_1.street} {params.step_1.number}, {params.step_1.city}, Netherlands'
        entity_folder_path = Path(__file__).parent  # entity_type_a
        dir_path = entity_folder_path / 'file_storage'

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

        base = Pdok(params.step_1.street, params.step_1.number, params.step_1.city, dir_path)
        base.run()
        print(base)



    def set_params(self, params, **kwargs):
        address = f'{params.step_1.street} {params.step_1.number}, {params.step_1.city}, Netherlands'

        geolocator = Nominatim(user_agent="my-app")
        location = geolocator.geocode(address)
        lat = location.latitude
        lon = location.longitude
        return SetParamsResult({
            "street": params.step_1.street,
            "number": params.step_1.number,
            "city": params.step_1.city,
            "lat": location.latitude,
            "lon": location.longitude,
        })

    def perform_download(self, params, **kwargs):
        # Prepare the path where files are located
        entity_folder_path = Path(__file__).parent  # entity_type_a
        dir_path = entity_folder_path / 'file_storage'
        abs_dir_path = os.path.abspath(dir_path)
        # path = Path(dir_path, f"{params.step_1.street} {params.step_1.number}, {params.step_1.city}, Netherlands")
        # path = Path(dir_path, uuid_dir)
        self.run_dxf(dir_path, abs_dir_path)

        # Create a temporary file to store the zip archive
        with tempfile.NamedTemporaryFile(delete=False) as tmp_zip:
            # Create a zip archive and add files to it
            with zipfile.ZipFile(tmp_zip.name, 'w', zipfile.ZIP_DEFLATED) as z:
                # Iterate over files in the directory and add only files with extensions .dxf or .gml to the zip archive
                for file_path in dir_path.iterdir():
                    if file_path.is_file() and (file_path.suffix == '.dxf' or file_path.suffix == '.gml' or file_path.suffix == '.log'):
                        file_name = file_path.name
                        z.write(file_path, arcname=file_name)

        # Read the zip archive content
        with open(tmp_zip.name, 'rb') as f:
            zip_content = f.read()

        # Return a DownloadResult with the zip content and file name
        return DownloadResult(zip_content, file_name="my_file.zip")


    @MapView('PDOK kaart', duration_guess=1)
    def get_map_view(self, params, **kwargs):
        # Create points using the provided street, number, and city
        features = []
        print(params)
        print(f'OSGEO VERSION --- {osgeo.__version__}')
        # print(ogr.__version__)

        if params.step_1.drag_location and params.step_1.search_method == 'Pin-drop':
            features.append(MapPoint.from_geo_point(params.step_1.drag_location))

        if params.step_1.street and params.step_1.number and params.step_1.city:
            address = f'{params.step_1.street} {params.step_1.number}, {params.step_1.city}, Netherlands'
            geolocator = Nominatim(user_agent="my-app")
            location = geolocator.geocode(address)
            lat = location.latitude
            lon = location.longitude

            if params.step_1.search_method == 'Ingevoerde adres':
                features.append(MapPoint(lat, lon))
                params.data = [lat, lon]


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
    pass