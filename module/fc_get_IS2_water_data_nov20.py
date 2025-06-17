import os
import h5py
import numpy as np
import rasterio
from datetime import datetime
from collections import defaultdict


def calendar_to_doy(year, month, day):
    return datetime(year, month, day).timetuple().tm_yday


def get_IS2_water_data_nov20(mask, metadata, R, transform):
    LonLimits = R['lon_limits']
    LatLimits = R['lat_limits']

    water_data = []
    count = 1

    os.chdir(r'F:\ATL08_006-20250418_031619\\')

    for meta in metadata:
        if (meta['lon_min'] < LonLimits[1] and meta['lon_max'] > LonLimits[0] and
                meta['lat_min'] < LatLimits[1] and meta['lat_max'] > LatLimits[0]):

            lasers = meta['lasers']
            filename = meta['filename']

            with h5py.File(filename, 'r') as f:
                for laser in lasers:
                    laser_name = laser['Name']
                    try:
                        lon = f[f'{laser_name}/land_segments/longitude'][:]
                        lat = f[f'{laser_name}/land_segments/latitude'][:]
                    except KeyError:
                        continue

                    I, J, valid_mask = geographic_to_discrete(transform, mask.shape, lat, lon)
                    if np.sum(np.isnan(I)) < len(I):
                        elev = f[f'{laser_name}/land_segments/terrain/h_te_mean'][:]
                        terrain_flag = f[f'{laser_name}/land_segments/terrain_flg'][:]
                        uncertainty = f[f'{laser_name}/land_segments/terrain/h_te_uncertainty'][:]
                        elev = elev[valid_mask]
                        lat = lat[valid_mask]
                        lon = lon[valid_mask]
                        terrain_flag = terrain_flag[valid_mask]
                        uncertainty = uncertainty[valid_mask]

                        mask_val = mask[I, J]

                        year = meta['year']
                        month = meta['month']
                        day = meta['day']
                        doy = calendar_to_doy(year, month, day)

                        unique_bodies = np.unique(mask_val)

                        if len(unique_bodies) > 1:
                            for body in unique_bodies[1:]:
                                ind = np.where(mask_val == body)[0]
                                if len(ind) > 2:
                                    heights = elev[ind]
                                    p90 = np.percentile(heights, 90)
                                    p10 = np.percentile(heights, 10)

                                    all_X = lon[ind].copy()
                                    all_Y = lat[ind].copy()

                                    outliers = (heights > p90) | (heights < p10)
                                    all_X = all_X[~outliers]
                                    all_Y = all_Y[~outliers]
                                    heights = heights[~outliers]

                                    entry = {
                                        'id': count,
                                        'mask_id': int(body),
                                        'raw_num_points': len(ind),
                                        'raw_x_pts': lon[ind],
                                        'raw_y_pts': lat[ind],
                                        'raw_heights': elev[ind],
                                        'terrain_flag': terrain_flag[ind],
                                        'uncertainty': uncertainty[ind],
                                        'height': np.median(heights),
                                        'std': np.std(heights),
                                        'num_points': len(heights),
                                        'med_x': np.median(all_X),
                                        'med_y': np.median(all_Y),
                                        'laser': laser_name,
                                        'doy': doy,
                                        'month': month,
                                        'year': year,
                                        'filename': filename
                                    }

                                    water_data.append(entry)
                                    count += 1
    return water_data, count - 1


def geographic_to_discrete(transform, shape, lat, lon):
    rows, cols = rasterio.transform.rowcol(transform, lon, lat)
    rows = np.array(rows)
    cols = np.array(cols)
    valid = (rows >= 0) & (rows < shape[0]) & (cols >= 0) & (cols < shape[1])
    rows = rows[valid]
    cols = cols[valid]
    return rows, cols, valid