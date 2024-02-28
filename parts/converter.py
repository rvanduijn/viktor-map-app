import subprocess
import os
import ezdxf
from osgeo import ogr
from osgeo import osr

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
