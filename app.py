from viktor import ViktorController
from viktor.parametrization import ViktorParametrization, GeoPointField, TextField, Text, SetParamsButton, \
    ViktorParametrization, Step, TextField, NumberField, SetParamsButton, ActionButton, DownloadButton, OutputField, OptionField
from viktor.views import MapPolygon, MapView, MapResult, MapPoint, MapLine, Color
from viktor.result import SetParamsResult, DownloadResult
from viktor.errors import UserError
from parts.connector import Pdok
from parts.converter import Converter
from geopy.geocoders import Nominatim
import pyproj
import tempfile
import zipfile
from pathlib import Path

data = []

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
    step_1 = Step('Step 1 - selecteer je locatie', views="get_map_view")
    step_1.introduction_text = Text(
        "## Welcome bij de PDOK app! \n"
        "Met behulp van deze app kan je kaartlagen van de BGT en DKK downloaden in .dxf-formaat"
        "Selecteer een gebied en bereik, klik op 'verder' om de download te starten"
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

    step_2 = Step('Step 2 - with views', views='get_map_view_2')
    step_2.reach_text = Text("### Download-bereik (m): \n")
    step_2.download_range = NumberField('', variant='slider', min=100, max=2000, step=100, flex=100)

    step_2.button = ActionButton('Download omgeving', method='perform_action')
    step_2.download_btn = DownloadButton("Download file", "perform_download", longpoll=True)


class Controller(ViktorController):
    label = "My Map Entity Type"
    parametrization = Parametrization

    def run_dxf(self, folder_name):
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

    def search_location(self, params, **kwargs):
        address = f'{params.street} {params.number}, {params.city}, Netherlands'
        geolocator = Nominatim(user_agent="my-app")
        location = geolocator.geocode(address)
        print(location.latitude)
        print(location.longitude)
        return location

    def perform_action(self, params, **kwargs):
        address = f'{params.street} {params.number}, {params.city}, Netherlands'
        print(address)
        base = Pdok(params.street, params.number, params.city)
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
        print(params)
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


    @MapView('Map view 2', duration_guess=1)
    def get_map_view_2(self, params, **kwargs):
        features = []
        print(f'params2 {params}')

        a = [MapPoint(54.814614, -26.785331),
        MapPoint(54.610949, -15.190123),
        MapPoint(50.824269, -15.429211),
        MapPoint(50.864828, -26.741683)]

        return MapResult(features)

if __name__ == "__main__":
    pass