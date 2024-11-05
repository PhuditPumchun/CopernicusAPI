from datetime import date, timedelta
import requests
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import zipfile
import os
from tqdm import tqdm
import xml.etree.ElementTree as ET
import rasterio
import numpy as np
import matplotlib.pyplot as plt
import shutil

class Copernicus:
    def __init__(self, username, password):
        self.copernicus_user = username
        self.copernicus_password = password
        self.data_collection = "SENTINEL-2"
        self.NDVIIMG_filename = "ndvi_image"  
        self.NDWIIMG_filename = "ndwi_image"  
        self.NDBIIMG_filename = "ndbi_image"  
        self.NDMIIMG_filename = "ndmi_image"  

    def get_keycloak(self) -> str:
        data = {
            "client_id": "cdse-public",
            "username": self.copernicus_user,
            "password": self.copernicus_password,
            "grant_type": "password",
        }
        try:
            r = requests.post(
                "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
                data=data,
            )
            r.raise_for_status()
            return r.json()["access_token"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to retrieve token: {e}")

    def fetch_data(self, ft, start_date, end_date, cloud_cover=None):
        filters = [
            f"Collection/Name eq '{self.data_collection}'",
            f"OData.CSC.Intersects(area=geography'SRID=4326;{ft}')",
            f"ContentDate/Start gt {start_date}T00:00:00.000Z",
            f"ContentDate/Start lt {end_date}T00:00:00.000Z"
        ]

        if cloud_cover is not None:
            filters.append(f"Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {cloud_cover})")

        filter_query = " and ".join(filters)
        url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter={filter_query}&$count=True&$top=1000"

        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            return data.get("value", [])
        except requests.exceptions.RequestException as e:
            print(f"Data retrieval error: {e}")
            return []

    def download_tiles(self, ft, dayRange, cloud_cover=None):
        start = date.today()
        today_string = start.strftime("%Y-%m-%d")
        before = start - timedelta(days=dayRange)
        before_string = before.strftime("%Y-%m-%d")
        tiles = self.fetch_data(ft, before_string, today_string, cloud_cover)
        
        if not tiles:
            print("No data found for the specified area and date range.")
            return False

        df = pd.DataFrame.from_dict(tiles)
        df["geometry"] = df["GeoFootprint"].apply(shape)
        gdf = gpd.GeoDataFrame(df).set_geometry("geometry")
        gdf = gdf[~gdf["Name"].str.contains("L1C")]
        gdf["identifier"] = gdf["Name"].str.split(".").str[0]

        if gdf.empty:
            print("No L2A tiles available.")
            return False

        print(f"Total L2A tiles found: {len(gdf)}")

        keycloak_token = self.get_keycloak()
        session = requests.Session()
        session.headers.update({"Authorization": f"Bearer {keycloak_token}"})

        for _, feat in gdf.iterrows():
            try:
                url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({feat['Id']})/$value"
                response = session.get(url, stream=True, allow_redirects=False)

                redirect_count = 0
                while response.is_redirect and redirect_count < 5:
                    url = response.headers["Location"]
                    response = session.get(url, stream=True, allow_redirects=False)
                    redirect_count += 1

                if response.status_code == 200:
                    total_size = int(response.headers.get('content-length', 0))
                    file_path = f"{feat['identifier']}.zip"

                    with open(file_path, "wb") as f, tqdm(
                        desc=f"Downloading {feat['Name']}",
                        total=total_size,
                        unit="B",
                        unit_scale=True,
                        unit_divisor=1024,
                    ) as progress_bar:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                                progress_bar.update(len(chunk))
                    
                    self.extract_tile(file_path)
                    self.read_metadata(feat['identifier'])
                    self.calculate_ndvi(feat['identifier'])
                    self.calculate_ndwi(feat['identifier'])
                    self.calculate_ndbi(feat['identifier'])
                    self.calculate_ndmi(feat['identifier'])
                    
                    safe_folder = f"{feat['identifier']}.SAFE"
                    if os.path.isdir(safe_folder):
                        shutil.rmtree(safe_folder)
                        print(f"Removed directory: {safe_folder}")
                    
                    print(f"Downloaded and processed {feat['identifier']} successfully.")
                    return True
            

                else:
                    print(f"Failed to download {feat['identifier']} - Status code: {response.status_code}")
                    return False

            except requests.exceptions.RequestException as e:
                print(f"Error downloading {feat['identifier']}: {e}")
                return False

    def extract_tile(self, file_path):
        try:
            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                print(f"Extracting {file_path}...")
                zip_ref.extractall()
            os.remove(file_path)
        except zipfile.BadZipFile:
            print(f"Error: {file_path} is not a valid zip file.")

    def read_metadata(self, tile_identifier):

        xml_file_path = os.path.join(tile_identifier + ".SAFE", "MTD_MSIL2A.xml")

        if not os.path.exists(xml_file_path):
            print(f"Metadata file not found for tile {tile_identifier}")
            return None

        tree = ET.parse(xml_file_path)
        root = tree.getroot()
                
        self.PROCESSING_LEVEL = root.findtext('.//PROCESSING_LEVEL')
        self.SENSING_ORBIT_NUMBER = root.findtext('.//SENSING_ORBIT_NUMBER')

        self.Cloud_Coverage_Assessment = root.findtext('.//Cloud_Coverage_Assessment')

        self.CLOUDY_PIXEL_OVER_LAND_PERCENTAGE = root.findtext('.//CLOUDY_PIXEL_OVER_LAND_PERCENTAGE')
        self.NODATA_PIXEL_PERCENTAGE = root.findtext('.//NODATA_PIXEL_PERCENTAGE')
        self.SATURATED_DEFECTIVE_PIXEL_PERCENTAGE = root.findtext('.//SATURATED_DEFECTIVE_PIXEL_PERCENTAGE')
        self.CAST_SHADOW_PERCENTAGE = root.findtext('.//CAST_SHADOW_PERCENTAGE')
        self.CLOUD_SHADOW_PERCENTAGE = root.findtext('.//CLOUD_SHADOW_PERCENTAGE')
        self.VEGETATION_PERCENTAGE = root.findtext('.//VEGETATION_PERCENTAGE')
        self.NOT_VEGETATED_PERCENTAGE = root.findtext('.//NOT_VEGETATED_PERCENTAGE')
        self.WATER_PERCENTAGE = root.findtext('.//WATER_PERCENTAGE')
        self.UNCLASSIFIED_PERCENTAGE = root.findtext('.//UNCLASSIFIED_PERCENTAGE')
        self.MEDIUM_PROBA_CLOUDS_PERCENTAGE = root.findtext('.//MEDIUM_PROBA_CLOUDS_PERCENTAGE')
        self.HIGH_PROBA_CLOUDS_PERCENTAGE = root.findtext('.//HIGH_PROBA_CLOUDS_PERCENTAGE')
        self.THIN_CIRRUS_PERCENTAGE = root.findtext('.//THIN_CIRRUS_PERCENTAGE')
        self.SNOW_ICE_PERCENTAGE = root.findtext('.//SNOW_ICE_PERCENTAGE')
        self.RADIATIVE_TRANSFER_ACCURACY = root.findtext('.//RADIATIVE_TRANSFER_ACCURACY')
        self.WATER_VAPOUR_RETRIEVAL_ACCURACY = root.findtext('.//WATER_VAPOUR_RETRIEVAL_ACCURACY')
        self.AOT_RETRIEVAL_ACCURACY = root.findtext('.//AOT_RETRIEVAL_ACCURACY')
        self.AOT_RETRIEVAL_METHOD = root.findtext('.//AOT_RETRIEVAL_METHOD')
        self.GRANULE_MEAN_AOT = root.findtext('.//GRANULE_MEAN_AOT')
        self.GRANULE_MEAN_WV = root.findtext('.//GRANULE_MEAN_WV')
        self.OZONE_SOURCE = root.findtext('.//OZONE_SOURCE')
        self.OZONE_VALUE= root.findtext('.//OZONE_VALUE')

    def calculate_ndvi(self, tile_identifier):
        granule_path = os.path.join(tile_identifier + ".SAFE", "GRANULE")
        if not os.path.isdir(granule_path):
            print(f"Granule directory not found for tile {tile_identifier}")
            return

        granule_subfolder = next(os.scandir(granule_path)).path
        img_data_path = os.path.join(granule_subfolder, "IMG_DATA", "R60m")

        red_band_path = None
        nir_band_path = None

        for file in os.listdir(img_data_path):
            if "B04" in file:
                red_band_path = os.path.join(img_data_path, file)
            elif "B8A" in file:
                nir_band_path = os.path.join(img_data_path, file)

        if red_band_path and nir_band_path:
            ndvi_data = self.compute_ndvi(red_band_path, nir_band_path)
            self.plot_ndvi(ndvi_data)  
        else:
            print("Required bands (B04 and B8A) not found.")

    def compute_ndvi(self, red_band_path, nir_band_path):
        with rasterio.open(red_band_path) as red:
            red_data = red.read(1).astype('float64')
        with rasterio.open(nir_band_path) as nir:
            nir_data = nir.read(1).astype('float64')

        ndvi = (nir_data - red_data) / (nir_data + red_data)
        return ndvi

    def plot_ndvi(self, ndvi_data):
        plt.figure(figsize=(10, 6))
        plt.imshow(ndvi_data, cmap='RdYlGn')
        plt.colorbar(label='NDVI Value')
        plt.title('NDVI Map')
        plt.xlabel('Pixel')
        plt.ylabel('Pixel')
        ndvi_image_path = f"{self.NDVIIMG_filename}.png" 
        if os.path.exists(ndvi_image_path):
            os.remove(ndvi_image_path)
            print(f"Removed existing NDVI image: {ndvi_image_path}")
        plt.savefig(ndvi_image_path, format='png')
        plt.close()
        
        print(f"NDVI image saved to {ndvi_image_path}")

    def calculate_ndwi(self, tile_identifier):
        granule_path = os.path.join(tile_identifier + ".SAFE", "GRANULE")
        if not os.path.isdir(granule_path):
            print(f"Granule directory not found for tile {tile_identifier}")
            return

        granule_subfolder = next(os.scandir(granule_path)).path
        img_data_path = os.path.join(granule_subfolder, "IMG_DATA", "R60m")

        green_band_path = None
        nir_band_path = None

        for file in os.listdir(img_data_path):
            if "B03" in file:
                green_band_path = os.path.join(img_data_path, file)
            elif "B8A" in file:
                nir_band_path = os.path.join(img_data_path, file)

        if green_band_path and nir_band_path:
            ndwi_data = self.compute_ndwi(green_band_path, nir_band_path)
            self.plot_ndwi(ndwi_data) 
        else:
            print("Required bands (B03 and B8A) not found.")

    def compute_ndwi(self, green_band_path, nir_band_path):
        with rasterio.open(green_band_path) as green:
            green_data = green.read(1).astype('float64')
        with rasterio.open(nir_band_path) as nir:
            nir_data = nir.read(1).astype('float64')

        ndwi = (green_data - nir_data) / (green_data + nir_data)
        return ndwi

    def plot_ndwi(self, ndwi_data):
        plt.figure(figsize=(10, 6))
        plt.imshow(ndwi_data, cmap='Blues') 
        plt.colorbar(label='NDWI Value')
        plt.title('NDWI Map')
        plt.xlabel('Pixel')
        plt.ylabel('Pixel')
        
        ndwi_image_path = f"{self.NDWIIMG_filename}.png"
        if os.path.exists(ndwi_image_path):
            os.remove(ndwi_image_path)
            print(f"Removed existing NDWI image: {ndwi_image_path}") 
        plt.savefig(ndwi_image_path, format='png')
        plt.close()
        
        print(f"NDWI image saved to {ndwi_image_path}")

    def calculate_ndbi(self, tile_identifier):
        granule_path = os.path.join(tile_identifier + ".SAFE", "GRANULE")
        if not os.path.isdir(granule_path):
            print(f"Granule directory not found for tile {tile_identifier}")
            return

        granule_subfolder = next(os.scandir(granule_path)).path
        img_data_path = os.path.join(granule_subfolder, "IMG_DATA", "R60m")

        swir_band_path = None  
        nir_band_path = None   

        for file in os.listdir(img_data_path):
            if "B11" in file:  
                swir_band_path = os.path.join(img_data_path, file)
            elif "B8A" in file: 
                nir_band_path = os.path.join(img_data_path, file)

        if swir_band_path and nir_band_path:
            ndbi_data = self.compute_ndbi(swir_band_path, nir_band_path)
            self.plot_ndbi(ndbi_data)
        else:
            print("Required bands (B11 and B8A) not found.")

    def compute_ndbi(self, swir_band_path, nir_band_path):
        with rasterio.open(swir_band_path) as swir:
            swir_data = swir.read(1).astype('float64')
        with rasterio.open(nir_band_path) as nir:
            nir_data = nir.read(1).astype('float64')

        ndbi = (swir_data - nir_data) / (swir_data + nir_data)
        return ndbi

    def plot_ndbi(self, ndbi_data):
        plt.figure(figsize=(10, 6))
        plt.imshow(ndbi_data, cmap='RdYlBu')  
        plt.colorbar(label='NDBI Value')
        plt.title('NDBI Map')
        plt.xlabel('Pixel')
        plt.ylabel('Pixel')

        ndbi_image_path = f"{self.NDBIIMG_filename}.png"
        if os.path.exists(ndbi_image_path):
            os.remove(ndbi_image_path)
            print(f"Removed existing NDBI image: {ndbi_image_path}")
        plt.savefig(ndbi_image_path, format='png')
        plt.close()

        print(f"NDBI image saved to {ndbi_image_path}")

    def calculate_ndmi(self, tile_identifier):
        granule_path = os.path.join(tile_identifier + ".SAFE", "GRANULE")
        if not os.path.isdir(granule_path):
            print(f"Granule directory not found for tile {tile_identifier}")
            return

        granule_subfolder = next(os.scandir(granule_path)).path
        img_data_path = os.path.join(granule_subfolder, "IMG_DATA", "R60m")

        nir_band_path = None  
        swir_band_path = None
        for file in os.listdir(img_data_path):
            if "B8A" in file:  
                nir_band_path = os.path.join(img_data_path, file)
            elif "B11" in file:
                swir_band_path = os.path.join(img_data_path, file)

        if nir_band_path and swir_band_path:
            ndmi_data = self.compute_ndmi(nir_band_path, swir_band_path)
            self.plot_ndmi(ndmi_data)
        else:
            print("Required bands (B8A and B11) not found.")

    def compute_ndmi(self, nir_band_path, swir_band_path):
        with rasterio.open(nir_band_path) as nir:
            nir_data = nir.read(1).astype('float64')
        with rasterio.open(swir_band_path) as swir:
            swir_data = swir.read(1).astype('float64')

        ndmi = (nir_data - swir_data) / (nir_data + swir_data)
        return ndmi

    def plot_ndmi(self, ndmi_data):
        plt.figure(figsize=(10, 6))
        plt.imshow(ndmi_data, cmap='Blues') 
        plt.colorbar(label='NDMI Value')
        plt.title('NDMI Map')
        plt.xlabel('Pixel')
        plt.ylabel('Pixel')

        ndmi_image_path = f"{self.NDMIIMG_filename}.png" 
        if os.path.exists(ndmi_image_path):
            os.remove(ndmi_image_path)
            print(f"Removed existing NDMI image: {ndmi_image_path}")
        plt.savefig(ndmi_image_path, format='png')
        plt.close()

        print(f"NDMI image saved to {ndmi_image_path}")
