import xml.etree.ElementTree as ET
import os
import ezdxf

class GmlConverter:
    def __init__(self, file_path):
        self.namespace = {
            't': 'http://www.opengis.net/citygml/transportation/2.0',
            'imgeo': 'http://www.geostandaarden.nl/imgeo/2.1',
            'gml': 'http://www.opengis.net/gml'}
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



