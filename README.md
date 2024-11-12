# Copernicus API Integration
เป็น API ที่เขียนผ่าน flask โดยสามารถล็อคอิน ดึงข้อมูลดาวเทียมจาก Copernicus Eco system ดูข้อมูล Metadata และประมวณผลข้อมูล NDVI, NDWI, NDBI และ NDMI ผ่าน RESTful API

## เริ่มต้นการใช้งาน

### ข้อกำหนดเบื้องต้น

เวอร์ชั่นของโมดูลและภาษาเป็นดังนี้ :

- Python 3.12.6
- `requests` 2.32.3
- `pandas` 2.2.3
- `geopandas` 1.0.1
- `shapely` 2.0.6
- `tqdm` 4.66.6
- `rasterio` 1.4.2
- `numpy` 2.1.2
- `Flask` 3.0.3

มีการจัดทำ Vitual environment ไว้ให้เรียบร้อยแล้ว โดยสามารถใช้งานได้โด้ยผ่านคำสั่ง:

```bash
env/Scripts/Activate
```

### โครงสร้างของโปรเจค

ภายในโปรเจคมีโครงสร้าง ดังนี้ :
- CopernicusAPI.py ไฟล์ฟังก์ชั่นการทำงานของ CopernicusAPI
- App.py ไฟล์ API ที่ใช้งานจริง

## การใช้งาน
รัน App.py เพื่อเปิดเซิร์ฟเวอร์ API บนเครื่อง จะมีการแสดง URL และพอร์ต (ค่าเริ่มต้น: http://127.0.0.1:5000)

### 1.ล็อคอิน (POST)
ใช้ล็อคอินเข้าสู่ระบบ โดยยิงรีเควสที่ /login และส่ง JSON ดังนี้
```json
{
  "username": "<อีเมลของคุณที่ใช้ล็อคอิน Copernicus>",
  "password": "<รหัสผ่านของคุณที่ใช้ล็อคอิน Copernicus>"
}
```
หากล็อคอินสำเร็จ ระบบจะตอบกลับด้วย Status Code 200

### 2. ดาวน์โหลดข้อมูล (POST)
ใช้ดาวน์โหลดข้อมูลของดาวเทียม โดยยิงรีเควสที่ /download_tile และส่ง JSON ดังนี้
```json
{
  "polygon": "<พื้นที่ที่ต้องการค้นหาในรูปแบบ Polygon>",
  "dayRange": "<ต้องการข้อมูลกี่วันย้อนหลัง>",
  "cloudCover" : "<ปริมาณความหนาแน่นของเมฆที่ต้องการ>"
}
```
ระบบจะทำการค้นหาข้อมูลแผนที่ และดาวน์โหลดอันแรกสุด หลังจากนั้นจะแตกไฟล์ เก็บข้อมูล metadata สร้างรูป NDVI,NDWI,NDBI,NDMI เมื่อเก็บข้อมูลและสร้างรูปเสร็จสิ้น จะลบไฟล์ที่ดาวน์โหลดและตอบกลับด้วย Status Code 200
* หมายเหตุ cloudCover เป็น Optional ไม่จำเป็นต้องส่งไปด้วยก็ได้

### 3. ดึงข้อมูล Metadata (GET)
ใช้ดึงข้อมูล Metadata ที่เราได้เก็บไว้ โดยยิงรีเควสที่ /metadata และระบบจะส่ง metadata ทั้งหมดมาและ Status Code 200 ทั้งนี้ สามารถใช้ /metadata/<field_name> เพื่อรับ metadata เฉพาะเจาะจงได้
metadata ที่ทำการเก็บ
1. Orbit_Number
2. Cloud_Coverage_Assessment
3. Cloudy_Pixel_Over_Land_Percentage
4. Nodata_Pixel_Percentage
5. Saturated_Defective_Pixel_Percentage
6. Cast_Shadow_Percentage
7. Cloud_Shadow_Percentage
8. Vegetation_Percentage
9. Not_Vegetated_Percentage
10. Water_Percentage
11. Unclassified_Percentage
12. Medium_Probability_Clouds_Percentage
13. High_Probability_Clouds_Percentage
14. Thin_Cirrus_Percentage
15. Snow_Ice_Percentage
16. Radiative_Transfer_Accuracy
17. Water_Vapour_Retrieval_Accuracy
18. AOT_Retrieval_Accuracy
19. AOT_Retrieval_Method
20. Granule_Mean_AOT
21. Granule_Mean_Water_Vapour
22. Ozone_Source
23. Ozone_Value

### 4. ดึงข้อมูลรูปภาพ NDVI, NDWI, NDBI, NDMI (GET)
ใช้ดึงข้อมูลรูปภาพ NDVI,NDWI,NDBI และ NDMI โดยยิงรีเควสที่ /ndvi /ndwi /ndbi หรือ /ndmi เพื่อรับค่ารูปภาพได้













