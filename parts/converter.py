import subprocess
import os
import ezdxf
import ezdxf.entities
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
        logging.basicConfig(filename=self.log_path, level=logging.CRITICAL)
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
            # No option for color here, handled in merge method
        ]

        try:
            subprocess.run(ogr2ogr_command, check=True)
            logging.info(f"Converted {file_name}.gml to {file_name}.dxf")
        except subprocess.CalledProcessError as e:
            logging.error(f"Error converting {file_name}.gml to DXF: {e}")

    def merge(self, export_list_data):
        target_dxf = ezdxf.new("R2010")
        target_modelspace = target_dxf.modelspace()

        print(self.dir_og)
        for export_item in export_list_data:
            layer_name = export_item['layer']
            color = export_item['color_aci']
            service = export_item['service']

            dxf_file = self.dir_og / f"{layer_name}.dxf"
            if dxf_file.exists():
                print(dxf_file.stem)
                input_dxf = ezdxf.readfile(str(dxf_file))

                layer_name_face = layer_name + "_face"
                layer_name_edge = layer_name + "_edge"

                if layer_name_face not in target_dxf.layers:
                    target_dxf.layers.new(name=layer_name_face, dxfattribs={'color': color})

                if layer_name_edge not in target_dxf.layers:
                    target_dxf.layers.new(name=layer_name_edge, dxfattribs={'color': color})

                for entity in input_dxf.modelspace():
                    if isinstance(entity, ezdxf.entities.Hatch):
                        entity.dxf.layer = layer_name_face
                        entity.dxf.color = color
                        target_modelspace.add_entity(entity.copy())

                    elif isinstance(entity, (ezdxf.entities.LWPolyline, ezdxf.entities.Polyline, ezdxf.entities.Line)):
                        entity.dxf.layer = layer_name_edge
                        entity.dxf.color = color
                        target_modelspace.add_entity(entity.copy())

                for entity in input_dxf.modelspace():
                    if isinstance(entity, ezdxf.entities.Hatch):
                        for path in entity.paths:
                            if isinstance(path, ezdxf.entities.PolylinePath):
                                # Extract vertices from the polyline path
                                vertices = path.vertices
                                # Create a new LWPolyline with the correct layer and color
                                lwpolyline = target_modelspace.add_lwpolyline(
                                    vertices,
                                    close=True,
                                )
                                lwpolyline.dxf.layer = layer_name_edge
                                # lwpolyline.dxf.color = 7  # Use a different color as needed

                    # else:
                    #     if service == 'dkk':
                    #         entity.dxf.color = 255  # White
                    #     else:
                    #         entity.dxf.color = 7  # Black

        combined_path = self.dir_og / "PDOK_combined.dxf"
        target_dxf.saveas(str(combined_path))

        # Add a comment with the CRS information
        with open(combined_path, 'a') as f:
            f.write(f'\n0\nCOMMENT\n1\nCRS=EPSG:28992\n')

        logging.info(f"Combined DXF files saved as {combined_path}")

    def run_converter(self, export_list_data):
        for export_item in export_list_data:
            feature = export_item.get('feature')
            name = export_item.get('layer')
            color = export_item.get('color_aci')

            self.convert_to_dxf(name, feature, color)

        self.merge(export_list_data)
