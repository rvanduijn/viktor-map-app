import subprocess
import os
import ezdxf
import logging
from pathlib import Path
from osgeo import ogr
from osgeo import osr
from parts import ogr2ogr

class Converter:
    def __init__(self, dir_path, abs_dir_path):
        # self.dir_path = os.path.expanduser(dir_path)
        self.dir_og = Path(__file__).parent.parent.parent / 'file_storage'
        self.dir_og = dir_path
        self.dir_path = f'{abs_dir_path}/'
        self.dir_path = dir_path
        self.log_path = self.dir_og / "logfile.log"
        logging.basicConfig(filename=self.log_path, level=logging.INFO)
        logging.info('this is the log-file for any errors')

    def convert_to_dxf(self, file_name, feature_name, color):
        input_gml_path = self.dir_og / f'{file_name}.gml'
        output_dxf_path = self.dir_og / f'{file_name}.dxf'
        print(input_gml_path)
        print(output_dxf_path)
        # Convert GML to DXF
        ogr2ogr_command = [
            "ogr2ogr",
            "-f",
            "DXF",
            str(output_dxf_path),
            str(input_gml_path),
            "-nln",
            feature_name,
            # "-oo",
            # f"LayerColor={color}",
        ]
        try:
            subprocess.run(ogr2ogr_command, check=True)
            logging.info(f"Converted {file_name}.gml to {file_name}.dxf")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error converting {file_name}.gml to DXF: {e}")

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
        # input_shp_path = os.path.join(self.dir_path, f'{file_name}.shp')
        # output_dxf_path = os.path.join(self.dir_path, f'{file_name}.dxf')
        input_shp_path = self.dir_path / f'{file_name}.dxf'
        output_dxf_path = self.dir_path / f'{file_name}.dxf'

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

    # def merge(self):
    #     target_dxf = ezdxf.new("R2010")
    #     target_modelspace = target_dxf.modelspace()
    #
    #     for dxf_file in self.dir_og.glob('*.dxf'):
    #         file_name = dxf_file.stem  # Get the file name without the suffix
    #         print(dxf_file.stem)
    #         input_dxf = ezdxf.readfile(str(dxf_file))
    #         for entity in input_dxf.modelspace():
    #             entity.dxf.layer = file_name
    #             target_modelspace.add_entity(entity.copy())
    #
    #     combined_path = self.dir_og / "PDOK_combined.dxf"
    #     target_dxf.saveas(str(combined_path))
    #     logging.info(f"Combined DXF files saved as {combined_path}")
    #
    # def merge(self, export_list_trimmed):
    #     target_dxf = ezdxf.new("R2010")
    #     target_modelspace = target_dxf.modelspace()
    #     for input_file in export_list_trimmed:
    #         feature = input_file.get('feature')
    #         layer = input_file.get('layer')
    #         color = input_file.get('color_aci')
    #
    #         filename = os.path.join(self.dir_path, f'{layer}.dxf')
    #
    #         if filename in self.dir_og.iterdir():
    #             print(filename)
    #
    #         input_dxf = ezdxf.readfile(filename)
    #         input_dxf.layers.add(name=feature, color=color)
    #         for entity in input_dxf.modelspace():
    #             entity.dxf.layer = feature
    #             target_modelspace.add_entity(entity.copy())
    #     combined = os.path.join(self.dir_path, "PDOK_combined.dxf")
    #     target_dxf.saveas(combined)

    def merge(self):
        target_dxf = ezdxf.new("R2010")
        target_modelspace = target_dxf.modelspace()

        print(self.dir_og)
        for dxf_file in self.dir_og.glob('*.dxf'):
            print(dxf_file.stem)
            file_name = dxf_file.stem  # Get the file name without the extension
            input_dxf = ezdxf.readfile(str(dxf_file))
            layer_name = file_name  # Use the file name as the layer name
            input_dxf.layers.add(name=layer_name)  # Assuming color is not needed
            for entity in input_dxf.modelspace():
                entity.dxf.layer = layer_name
                target_modelspace.add_entity(entity.copy())

        combined_path = self.dir_og / "PDOK_combined.dxf"
        target_dxf.saveas(str(combined_path))
        logging.info(f"Combined DXF files saved as {combined_path}")

    def run_converter(self, export_list_data):
        for i, export_item in enumerate(export_list_data):
            # try:
            feature = export_item.get('feature')
            name = export_item.get('layer')
            color = export_item.get('color_aci')
            # self.convert_to_shp(name)
            # self.shp_to_dxf(name, layer_name=feature, color=color)

            self.convert_to_dxf(name, feature, color)

            # except Exception as e:
            #     print(f"An error occurred during iteration {i}: {e}")
            #     logging.exception("An error occurred: %s", e)

        self.merge()
