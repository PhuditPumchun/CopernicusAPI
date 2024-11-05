from flask import Flask, request, jsonify, session , send_file
from CopernicusAPI import Copernicus
import os

app = Flask(__name__)
app.secret_key = "your_secret_key"
copernicus = None
metadata = None

@app.route("/login", methods=["POST"])
def login():
    global copernicus
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not (username and password):
        return jsonify({"error": "Username and password are required"}), 400

    copernicus = Copernicus(username, password)

    try:
        token = copernicus.get_keycloak()
        session["token"] = token
        return jsonify({"message": "Login successful"}), 200
    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 401


@app.route("/download_tile", methods=["POST"])
def download_tile():
    
    if "token" not in session:
        return jsonify({"error": "You need to log in first"}), 401

    data = request.get_json()
    polygon = data.get("polygon")
    dayRange = data.get("dayRange")
    cloudCover = data.get("cloudCover")
    global metadata

    if not (polygon and dayRange):
        return jsonify({"error": "Missing required parameters: 'polygon' and 'dayRange'"}), 400

    if not cloudCover:
        success = copernicus.download_tiles(polygon, dayRange)
    else:
        success = copernicus.download_tiles(polygon, dayRange,cloud_cover=cloudCover)

    if not success:
        return jsonify({"error": "Cant download or the tiles is not found"}),404

    try:
        metadata = {
            "Processing_Level": copernicus.PROCESSING_LEVEL,
            "Orbit_Number": copernicus.SENSING_ORBIT_NUMBER,
            "Cloud_Coverage_Assessment": copernicus.Cloud_Coverage_Assessment,
            "Cloudy_Pixel_Over_Land_Percentage": copernicus.CLOUDY_PIXEL_OVER_LAND_PERCENTAGE,
            "Nodata_Pixel_Percentage": copernicus.NODATA_PIXEL_PERCENTAGE,
            "Saturated_Defective_Pixel_Percentage": copernicus.SATURATED_DEFECTIVE_PIXEL_PERCENTAGE,
            "Cast_Shadow_Percentage": copernicus.CAST_SHADOW_PERCENTAGE,
            "Cloud_Shadow_Percentage": copernicus.CLOUD_SHADOW_PERCENTAGE,
            "Vegetation_Percentage": copernicus.VEGETATION_PERCENTAGE,
            "Not_Vegetated_Percentage": copernicus.NOT_VEGETATED_PERCENTAGE,
            "Water_Percentage": copernicus.WATER_PERCENTAGE,
            "Unclassified_Percentage": copernicus.UNCLASSIFIED_PERCENTAGE,
            "Medium_Probability_Clouds_Percentage": copernicus.MEDIUM_PROBA_CLOUDS_PERCENTAGE,
            "High_Probability_Clouds_Percentage": copernicus.HIGH_PROBA_CLOUDS_PERCENTAGE,
            "Thin_Cirrus_Percentage": copernicus.THIN_CIRRUS_PERCENTAGE,
            "Snow_Ice_Percentage": copernicus.SNOW_ICE_PERCENTAGE,
            "Radiative_Transfer_Accuracy": copernicus.RADIATIVE_TRANSFER_ACCURACY,
            "Water_Vapour_Retrieval_Accuracy": copernicus.WATER_VAPOUR_RETRIEVAL_ACCURACY,
            "AOT_Retrieval_Accuracy": copernicus.AOT_RETRIEVAL_ACCURACY,
            "AOT_Retrieval_Method": copernicus.AOT_RETRIEVAL_METHOD,
            "Granule_Mean_AOT": copernicus.GRANULE_MEAN_AOT,
            "Granule_Mean_Water_Vapour": copernicus.GRANULE_MEAN_WV,
            "Ozone_Source": copernicus.OZONE_SOURCE,
            "Ozone_Value": copernicus.OZONE_VALUE
        }

        return jsonify({"message": "Download initiated. Metadata has been updated."}), 200
    except Exception as e:
        return jsonify({"error": f"Download failed: {str(e)}"}), 500


@app.route("/metadata", methods=["GET"])
def get_metadata():
    if "token" not in session:
        return jsonify({"error": "You need to log in first"}), 401

    if metadata is None:
        return jsonify({"error": "Metadata not initialized. Please download a tile first."}), 400
    
    return jsonify(metadata), 200

@app.route("/metadata/<string:field_name>", methods=["GET"])
def metadata_field(field_name):
    if "token" not in session:
        return jsonify({"error": "You need to log in first"}), 401
    
    if metadata is None:
        return jsonify({"error": "Metadata not initialized. Please download a tile first."}), 400

    if field_name in metadata:
        return jsonify({field_name: metadata[field_name]}), 200
    else:
        return jsonify({"error": "Invalid metadata field specified"}), 404

@app.route("/ndvi", methods=["GET"])
def get_ndvi_image():
    if "token" not in session:
        return jsonify({"error": "You need to log in first"}), 401

    ndvi_image_path = f"{copernicus.NDVIIMG_filename}.png" 

    if not os.path.exists(ndvi_image_path):
        return jsonify({"error": "No NDVI image available. Please download and process tiles first."}), 400

    return send_file(ndvi_image_path, mimetype="image/png", as_attachment=True, download_name="ndvi_map.png")

@app.route("/ndwi", methods=["GET"])
def get_ndwi_image():
    if "token" not in session:
        return jsonify({"error": "You need to log in first"}), 401
    ndwi_image_path = f"{copernicus.NDWIIMG_filename}.png" 
    if not os.path.exists(ndwi_image_path):
        return jsonify({"error": "No NDWI image available. Please download and process tiles first."}), 400
    return send_file(ndwi_image_path, mimetype="image/png", as_attachment=True, download_name="ndwi_map.png")

@app.route("/ndbi", methods=["GET"])
def get_ndbi_image():
    if "token" not in session:
        return jsonify({"error": "You need to log in first"}), 401
    ndbi_image_path = f"{copernicus.NDBIIMG_filename}.png" 
    if not os.path.exists(ndbi_image_path):
        return jsonify({"error": "No NDBI image available. Please download and process tiles first."}), 400
    return send_file(ndbi_image_path, mimetype="image/png", as_attachment=True, download_name="ndbi_map.png")

@app.route("/ndmi", methods=["GET"])
def get_ndmi_image():
    if "token" not in session:
        return jsonify({"error": "You need to log in first"}), 401
    ndmi_image_path = f"{copernicus.NDMIIMG_filename}.png"
    if not os.path.exists(ndmi_image_path):
        return jsonify({"error": "No NDMI image available. Please download and process tiles first."}), 400
    return send_file(ndmi_image_path, mimetype="image/png", as_attachment=True, download_name="ndmi_map.png")


if __name__ == "__main__":
    app.run(debug=True)