import requests
from pprint import pprint
from pathlib import Path

class Omgevingsloket:
    def __init__(self, dir_path, lat, lon):
        self.dir_path = str(dir_path)
        self.lat = lat
        self.lon = lon
        self.dir_og = Path(__file__).parent.parent / 'file_storage'
        self.api_key = "98824d36b6db89aa1214a518e6c55923"
        self.url = "https://ruimte.omgevingswet.overheid.nl/ruimtelijke-plannen/api/opvragen/v4/plannen/_zoek"

    def plan_settings(self):
        payload = {
            "_geo": {
                "intersects": {
                    "type": "Point",
                    "coordinates": [self.lon, self.lat]
                }
            }
        }

        headers = {
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json',
            'Accept-Crs': 'epsg:28992'
        }

        params = {
            'regelStatus': ['geldend'],
            'planType': ['bestemmingsplan'],
        }

        response = requests.post(self.url, json=payload, headers=headers, params=params)

        return response

    def get_gml_file(self, url, name):

        # Local file path where the GML file will be saved
        # local_filename = f'{self.dir_og}/{name}.gml'
        local_filename = self.dir_og / f'{name}.gml'
        print(local_filename)
        # Send a GET request to the URL
        response = requests.get(url)

        # Check if the request was successful
        if response.status_code == 200:
            with open(local_filename, 'wb') as file:
                file.write(response.content)
            print(f"File downloaded and saved as {local_filename}")
        else:
            print(f"Failed to download the file. Status code: {response.status_code}")

    def search_plannen_all(self, plannen):
        for plan in plannen:
            paraplu = plan.get('isParapluplan')
            url = plan.get('verwijzingNaarGml')
            print(f"Paraplu: {paraplu}, URL: {url}")
            if not paraplu and url:
                name = plan.get('naam')
                datum = plan.get('planstatusInfo').get('datum')
                filename = f'{datum}_{name}'
                self.get_gml_file(url, filename)

    def run(self):
        response = self.plan_settings()
        pprint(response.content)
        if response.status_code == 200:
            data = response.json()
            embedded = data.get('_embedded')
            plannen = embedded.get('plannen')
            self.search_plannen_all(plannen)

        else:
            pprint(f"Error: {response.status_code} - {response.text}")


if __name__ == '__main__':
    # Example coordinates
    lat = 52.19
    lon = 4.421

    dir_path = Path(__file__).parent.parent / 'file_storage'
    print(dir_path)
    ol = Omgevingsloket(dir_path, lat, lon)
    ol.run()
