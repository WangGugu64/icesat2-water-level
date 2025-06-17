import numpy as np
import rasterio
from rasterio import features
from affine import Affine
import geopandas as gpd
from shapely.geometry import Point, Polygon, LineString
from skimage.measure import label, regionprops
from skimage.morphology import binary_erosion, binary_dilation
from shapely.vectorized import contains
from tqdm import tqdm
from scipy.spatial import cKDTree
from rasterio.transform import xy
from shapely import covers
def strel_disk_4(r):
    size = 2 * r + 1
    se = np.zeros((size, size), dtype=np.uint8)
    center = r

    for i in range(size):
        for j in range(size):
            if abs(i - center) + abs(j - center) <= r:
                se[i, j] = 1

    return se
def label_mask_and_identify_goodd(mask, R, glon, glat, coast_gdf, edit):


    # STEP 1: 保留大于75%的水体
    mask[(mask < 75) | (mask == 255)] = 0
    mask[mask > 1] = 1
    mask = mask.astype(np.uint8)

    if edit == 1:
        mask[13924:14008, 22545:22635] = 0
        mask[30698:30883, 27495:27911] = 0
        mask[28528:29102, 29695:30535] = 0

    # STEP 2: 水库识别，膨胀掩膜
    se = strel_disk_4(6).astype(bool)
    res_mask = binary_dilation(mask, se)

    # 将 dam 点投影到行列号
    cols, rows = (~R) * (glon, glat)
    cols = np.floor(cols).astype(int)
    rows = np.floor(rows).astype(int)

    valid = (cols >= 0) & (cols < mask.shape[1]) & (rows >= 0) & (rows < mask.shape[0])
    cols, rows = cols[valid], rows[valid]

    r_mask = np.zeros_like(mask)
    r_mask[rows, cols] = 1

    for _ in range(6):
        r_mask = binary_dilation(r_mask, se)

    res_mask_labeled = label(res_mask, connectivity=2)

    stats = regionprops(res_mask_labeled, intensity_image=r_mask)
    idx = [i.label for i in stats if i.max_intensity == 1]
    res_mask_out = np.isin(res_mask_labeled, idx).astype(np.uint8)

    # STEP 3: 腐蚀掩膜并标记 8连通
    se = strel_disk_4(1).astype(bool)
    mask = binary_erosion(mask, se)
    mask_l = label(mask, connectivity=2)

    stats = regionprops(mask_l)
    idx = [i.label for i in stats if i.extent > 0.05 and i.area > 20]
    mask = np.isin(mask_l, idx)
    mask_l = label(mask, connectivity=2)

    print('removing coastline...')
    stats = regionprops(mask_l)
    test_ocean = np.zeros(len(stats))

    coast_sindex = coast_gdf.sindex

    for i, region in enumerate(tqdm(stats)):
        vert = region.coords
        if len(vert) > 5000:
            vert = vert[::6, :]
        else:
            vert = vert[::3, :]

        lons, lats = xy(R, vert[:, 0], vert[:, 1], offset='center')
        verts = np.vstack((lons, lats)).T

        minx, miny = np.min(verts, axis=0)
        maxx, maxy = np.max(verts, axis=0)
        bounds = (minx, miny, maxx, maxy)

        possible_matches_idx = list(coast_sindex.intersection(bounds))
        possible_matches = coast_gdf.iloc[possible_matches_idx]

        if possible_matches.empty:
            continue

        # 加速判定用 cKDTree
        verts_tree = cKDTree(verts)
        in_any_coast = np.zeros(len(verts), dtype=bool)

        # 初始化累积矩阵，注意是 False 数组（相当于 MATLAB 的 basins = zeros）
        basins = np.zeros(len(verts), dtype=int)

        for poly in possible_matches.geometry:
            if poly.is_empty:
                continue

            # 判断哪些点在多边形内
            in_poly = contains(poly, verts[:, 0], verts[:, 1])

            # 累加到 basins
            basins += in_poly.astype(int)

        # 超过 1 的地方强制设为 1，和 MATLAB 版一样
        basins[basins > 1] = 1

        # 判断覆盖比例是否 ≥ 90%
        if np.sum(basins) < 0.9 * len(basins):
            test_ocean[i] = 0
        else:
            test_ocean[i] = 1

    idx = np.where(test_ocean == 1)[0] + 1

    mask = np.isin(mask_l, idx)
    mask_l[~mask] = 0

    # 再腐蚀一次
    mask = binary_erosion(mask_l > 0, se)
    mask_l[~mask] = 0

    # 类型压缩
    m = mask_l.max()
    if m < 256:
        mask_l = mask_l.astype(np.uint8)
    elif m < 65536:
        mask_l = mask_l.astype(np.uint16)
    else:
        mask_l = mask_l.astype(np.uint32)

    # STEP 4: 提取属性
    stats = regionprops(mask_l, intensity_image=res_mask_out)
    X, Y, lake_area, extent, goodd_res = [], [], [], [], []

    for s in stats:
        X.append(s.centroid[1])
        Y.append(s.centroid[0])
        lake_area.append(10**-6 * 30 * 30 * s.area)
        extent.append(s.extent)
        goodd_res.append(s.max_intensity if s.max_intensity is not None else np.nan)

    if stats:
        lons, lats = xy(R, [s.centroid[0] for s in stats], [s.centroid[1] for s in stats], offset='center')
        lon, lat = np.array(lons), np.array(lats)
    else:
        lon, lat = 0, 0

    return mask_l, np.array(lake_area), np.array(goodd_res), lat, lon, np.array(extent)