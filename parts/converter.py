import subprocess
import os
import ezdxf
import logging
from osgeo import ogr
from osgeo import osr
from parts import ogr2ogr

class Converter:
    def __init__(self, dir_path):
        # self.dir_path = os.path.expanduser(dir_path)
        self.dir_og = dir_path
        self.dir_path = f'{dir_path}/'
        self.log_path = os.path.join(self.dir_path, f'logfile.log')
        logging.basicConfig(filename=self.log_path, level=logging.INFO)
        logging.info('this is the log-file for any errors')

    def convert_to_shp(self, file_name):
        input_gml_path = os.path.join(self.dir_path, f'{file_name}.gml')
        output_shp_path = os.path.join(self.dir_path, f'{file_name}.shp')
        driver = ogr.GetDriverByName("ESRI Shapefile")
        out_ds = driver.CreateDataSource(output_shp_path)
        srs = osr.SpatialReference()
        with open(input_gml_path, "r") as gml_file:
            srs.ImportFromXML(gml_file.read())
        layer = out_ds.CreateLayer("output_layer", srs, ogr.wkbUnknown)

        src_ds = ogr.Open(input_gml_path)
        layer_source = src_ds.GetLayerByIndex(0)

        if layer_source is not None:
            for feature in layer_source:
                new_feature = ogr.Feature(layer.GetLayerDefn())
                new_feature.SetGeometry(feature.GetGeometryRef())
                for i in range(feature.GetFieldCount()):
                    try:
                        field_name = feature.GetFieldDefnRef(i).GetNameRef()
                        field_value = feature.GetField(i)
                        if isinstance(field_value, (int, float)):
                            new_feature.SetField(field_name, field_value)
                        else:
                            new_feature.SetField(field_name, str(field_value))
                    except Exception as e:
                        # print(f"Error setting field: {e}")
                        logging.exception("An error occurred: %s", e)

                layer.CreateFeature(new_feature)
        out_ds = None
        src_ds = None

    def shp_to_dxf(self, file_name, layer_name, color):
        input_shp_path = os.path.join(self.dir_path, f'{file_name}.shp')
        output_dxf_path = os.path.join(self.dir_path, f'{file_name}.dxf')
        ogr2ogr_command = [
            "ogr2ogr",
            "-f",
            "DXF",
            output_dxf_path,
            input_shp_path,
            "-nln",
            layer_name,
            # "-oo",
            # f"LayerColor={color}",
        ]
        # subprocess.run(ogr2ogr_command)
        ogr2ogr.main(ogr2ogr_command)

        print("Shapefile successfully converted to DXF.")

    def combine_dxf(self, export_list):
        doc = ezdxf.new("R2010")
        for i in export_list:
            name = i.get('layer')
            input_dxf_file = os.path.join(self.dir_path, f'{name}.dxf')
            layer_name = i.get('feature')
            layer_color = i.get('color_rgb')
            with ezdxf.readfile(input_dxf_file) as source_doc:
                source_block = doc.modelspace().insert_block(source_doc.modelspace())
                source_block.set_attrib(layer=layer_name, color=layer_color)
        output_combined_dxf_path = os.path.join(self.dir_path, "combined_output.dxf")
        doc.saveas(output_combined_dxf_path)
        print("DXF files successfully combined with specified layer names and colors using ezdxf.")

    def merge(self, export_list_trimmed):
        target_dxf = ezdxf.new("R2010")
        target_modelspace = target_dxf.modelspace()
        for input_file in export_list_trimmed:
            feature = input_file.get('feature')
            layer = input_file.get('layer')
            color = input_file.get('color_aci')
            filename = os.path.join(self.dir_path, f'{layer}.dxf')
            input_dxf = ezdxf.readfile(filename)
            input_dxf.layers.add(name=feature, color=color)
            for entity in input_dxf.modelspace():
                entity.dxf.layer = feature
                target_modelspace.add_entity(entity.copy())
        combined = os.path.join(self.dir_path, "PDOK_combined.dxf")
        target_dxf.saveas(combined)

    def run_converter(self, export_list_data):
        export_list_trimmed = []
        for i, export_item in enumerate(export_list_data):
            try:
                feature = export_item.get('feature')
                name = export_item.get('layer')
                color = export_item.get('color_aci')
                self.convert_to_shp(name)
                self.shp_to_dxf(name, layer_name=feature, color=color)
                export_list_trimmed.append(export_item)
            except Exception as e:
                print(f"An error occurred during iteration {i}: {e}")
                logging.exception("An error occurred: %s", e)


        for trim in export_list_trimmed:
            print(self.dir_og.iterdir())
            if trim in self.dir_og.iterdir():
                print(trim)
        # for file_path in self.dir_path.iterdir():
        #     print(file_path)
        #
        #     if file_path.is_file() and (file_path.suffix == '.dxf' or file_path.suffix == '.gml' or file_path.suffix == '.log'):
        #         file_name = file_path.name
        #         z.write(file_path, arcname=file_name)

        self.merge(export_list_trimmed)
        print("Conversion completed.")
