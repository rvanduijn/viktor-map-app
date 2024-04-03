import subprocess
import os
import ezdxf
import logging
from pathlib import Path
import osgeo
from osgeo import gdal
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
        # ogr2ogr.main(ogr2ogr_command)

        try:
            subprocess.run(ogr2ogr_command, check=True)
            logging.info(f"Converted {file_name}.gml to {file_name}.dxf")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error converting {file_name}.gml to DXF: {e}")

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
            feature = export_item.get('feature')
            name = export_item.get('layer')
            color = export_item.get('color_aci')

            self.convert_to_dxf(name, feature, color)

        self.merge()
