import os
import glob
import pickle
import numpy as np
import geopandas as gpd
import rasterio
from module import (
    fc_label_mask_and_identify_goodd_nov20,
    fc_get_mask_metadata_func_nov20,
    fc_get_merit_heights_nov20,
    fc_get_IS2_water_data_nov20,
    fc_organize_IS2_data_nov20,
    inpoly
)

# STEP 0: 配置路径
atl08_metadata_path = r"D:\Code\icesat2-water-levels-main\icesat2-water-levels-main\ICESat_2_metadata"
gswo_mask_path = r"D:\Code\icesat2-water-levels-main\icesat2-water-levels-main\SWO"
gdw_path = r"D:\Code\icesat2-water-levels-main\icesat2-water-levels-main\Global Dam Watch database version 1.0\GDW_v1_0_shp\GDW_v1_0_shp"
coast_path = r"D:\Code\icesat2-water-levels-main\icesat2-water-levels-main\GSHHS"
mask_output_path = r"D:\Code\icesat2-water-levels-main\icesat2-water-levels-main\mask"
results_output_path = r"D:\Code\icesat2-water-levels-main\icesat2-water-levels-main\results"
merit_path = r"D:\Code\icesat2-water-levels-main\icesat2-water-levels-main"

# 加载 ATL08 metadata（假设是 pickle 格式）
with open(os.path.join(atl08_metadata_path, 'atl_metadata_optimized.pkl'), 'rb') as f:
    metadata = pickle.load(f)

# 获取 GSWO water mask 文件列表
mask_files = glob.glob(os.path.join(gswo_mask_path, '*.tif'))
mask_files = [f for f in mask_files if os.path.getsize(f) > 10000]

# 读取 GDW dam dataset
gdw = gpd.read_file(os.path.join(gdw_path, 'GDW_barriers_v1_0.shp'))
glat = gdw['LAT_RIV'].values
glon = gdw['LONG_RIV'].values

# 读取海岸线
coast = gpd.read_file(os.path.join(coast_path, 'GSHHS_i_L1.shp'))

# 遍历 GSWO water masks
for n, mask_file in enumerate(mask_files, start=1):
    print("Reading in mask:", os.path.basename(mask_file))

    with rasterio.open(mask_file) as src:
        mask = src.read(1)
        shape = src.shape
        R = src.transform
        profile = src.profile
        bounds = src.bounds  # 左下右上
        R1 = {
            'lon_limits': (bounds.left, bounds.right),
            'lat_limits': (bounds.bottom, bounds.top),
            'shape': src.shape  # (rows, cols)
        }
    edit = 0

    # STEP 1: CREATE WATER MASK
    mask_l, lake_area, goodd_res, lat, lon, extent = fc_label_mask_and_identify_goodd_nov20.label_mask_and_identify_goodd(
        mask, R, glon, glat, coast, edit
    )

    if len(lat) > 0 and (lat[0] != 0 or len(lat) > 1):
        output_name1 = os.path.basename(mask_file).replace('.tif', 'labeled.tif')
        output_name2 = os.path.basename(mask_file).replace('.tif', 'stats.pkl')

        print("Writing mask...")
        # 保存 GeoTIFF
        labeled_tif_path = os.path.join(mask_output_path, output_name1)
        with rasterio.open(labeled_tif_path, 'w', **profile) as dst:
            dst.write(mask_l, 1)

        # 保存统计数据
        stats = {
            'lake_area': lake_area,
            'goodd_res': goodd_res,
            'lat': lat,
            'lon': lon,
            'extent': extent
        }
        with open(os.path.join(mask_output_path, output_name2), 'wb') as f:
            pickle.dump(stats, f)

        print(os.path.basename(mask_file))

        # STEP 2: GET HEIGHT FROM MERIT HYDROGRAPHY DATASET
        print("Getting merit heights...")
        mask_metadata = fc_get_mask_metadata_func_nov20.get_mask_metadata_func_nov20(os.path.basename(mask_file))

        merit_heights = fc_get_merit_heights_nov20.get_merit_heights_nov20(merit_path, mask_metadata, mask_l, shape)
        merit_output_name = f"merit_heights_{mask_metadata['lonstr']}{mask_metadata['ew']}_{mask_metadata['latstr']}{mask_metadata['ns']}_v1.pkl"
        with open(os.path.join(mask_output_path, merit_output_name), 'wb') as f:
            pickle.dump(merit_heights, f)

        # STEP 3: READ IN ICESAT-2 DATA
        print("Reading in IS2...")
        water_data, count = fc_get_IS2_water_data_nov20.get_IS2_water_data_nov20(mask_l, metadata, R1, R)

        # STEP 4: ORGANIZE ICESAT-2 DATA BY WATER BODY
        print("Organizing IS2...")
        if count > 1:
            complete_output = fc_organize_IS2_data_nov20.organize_IS2_data(water_data, merit_heights, extent, goodd_res, lake_area)
            if complete_output:
                result_output_name = f"results_{mask_metadata['lonstr']}{mask_metadata['ew']}_{mask_metadata['latstr']}{mask_metadata['ns']}_v1.pkl"
                with open(os.path.join(results_output_path, result_output_name), 'wb') as f:
                    pickle.dump({'complete_output': complete_output, 'water_data': water_data}, f)

        print(f"Finished {os.path.basename(mask_file)} ({n}/{len(mask_files)})")

print("All done!")
