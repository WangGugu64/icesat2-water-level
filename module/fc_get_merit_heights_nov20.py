import os
import numpy as np
import rasterio
from skimage.transform import resize
from skimage.measure import regionprops, label



def get_merit_heights_nov20(path, mask_metadata, labeled, swo_shape):
    """
    获取 MERIT Hydro 数据对应的高程值
    mask_metadata: dict，包含 'lon', 'lat', 'ew', 'ns' 字段
    labeled: numpy array，水体mask的label图
    """

    lonnum = mask_metadata['lon']
    latnum = mask_metadata['lat']

    if latnum == 0:
        mask_metadata['ns'] = 'S'

    # 获取 folderlon
    if mask_metadata['ew'] == 'W':
        if lonnum <= 30:
            folderlon = 'w030'
        elif lonnum <= 60:
            folderlon = 'w060'
        elif lonnum <= 90:
            folderlon = 'w090'
        elif lonnum <= 120:
            folderlon = 'w120'
        elif lonnum <= 150:
            folderlon = 'w150'
        else:
            folderlon = 'w180'
    else:
        if lonnum < 30:
            folderlon = 'e000'
        elif lonnum < 60:
            folderlon = 'e030'
        elif lonnum < 90:
            folderlon = 'e060'
        elif lonnum < 120:
            folderlon = 'e090'
        elif lonnum < 150:
            folderlon = 'e120'
        else:
            folderlon = 'e150'

    # 获取 folderlat
    if mask_metadata['ns'] == 'N':
        if latnum > 60:
            folderlat = 'n60'
        elif latnum > 30:
            folderlat = 'n30'
        else:
            folderlat = 'n00'
    else:
        if latnum < 30:
            folderlat = 's30'
        else:
            folderlat = 's60'


    merit_folder = os.path.join(path, 'MERIT_Hydro_elv', f'elv_{folderlat}{folderlon}')
    os.chdir(merit_folder)

    def format_lon_lat(lon, ew, lat, ns):
        lonstr = f"{int(lon):03d}"
        latstr = f"{int(lat):02d}"
        return f"{ns}{latstr}{ew}{lonstr}_elv.tif"

    def read_elev_file(lon_offset, lat_offset):
        if mask_metadata['ew'] == 'W':
            l = lonnum + lon_offset
            ew = 'w'
        else:
            l = lonnum + lon_offset
            ew = 'e'

        if mask_metadata['ns'] == 'N':
            la = latnum + lat_offset
            ns = 'n'
        else:
            la = latnum + lat_offset
            ns = 's'

        filename = format_lon_lat(l, ew, la, ns)

        if os.path.exists(filename):
            with rasterio.open(filename) as src:
                elev = src.read(1)
        else:
            elev = np.full((6000, 6000), -9999, dtype=np.float32)

        return elev

    # 读取四个高程块
    elev1 = read_elev_file(-5, +10)
    elev2 = read_elev_file(0, +10)
    elev3 = read_elev_file(-5, +5)
    elev4 = read_elev_file(0, +5)

    # 拼接成一个大图
    elev12 = np.concatenate([elev2, elev1], axis=1)
    elev34 = np.concatenate([elev4, elev3], axis=1)
    elev = np.concatenate([elev34, elev12], axis=0)

    # 重采样到 8806×19151
    elev_resized = resize(elev, swo_shape, order=0, preserve_range=True, anti_aliasing=False)

    # regionprops 获取每个label区内高程像元值
    stats = regionprops(labeled, intensity_image=elev_resized)

    merit_heights = []
    for region in stats:
        px = region.intensity_image[region.image]
        p90 = np.percentile(px, 90)
        p10 = np.percentile(px, 10)
        px_clipped = px[(px >= p10) & (px <= p90)]

        if len(px_clipped) == 0 or np.all(np.isnan(px_clipped)):
            merit_heights.append({
                'height': np.nan,
                'std': np.nan,
                'mean': np.nan
            })
            continue

        merit_heights.append({
            'height': np.nanmedian(px_clipped),
            'std': np.nanstd(px_clipped),
            'mean': np.nanmean(px_clipped)
        })

    return merit_heights
