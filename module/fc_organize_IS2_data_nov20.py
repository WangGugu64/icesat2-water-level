import numpy as np
from scipy.spatial.distance import pdist, squareform
from pyproj import Transformer

def organize_IS2_data(water_data, merit_heights, extent, goodd_res, lake_area):
    complete_output = []

    mask_ids = np.array([wd['mask_id'] for wd in water_data])
    unique_mask_ids = np.unique(mask_ids)

    for mask_id in unique_mask_ids:
        indices = np.where(mask_ids == mask_id)[0]
        result = {
            'mask_id': mask_id,
            'area': lake_area[mask_id],
            'extent': extent[mask_id],
            'goodd_res': goodd_res[mask_id],
            'flag': 0
        }

        heights, stds, xpts, ypts, doys, months, years = [], [], [], [], [], [], []

        for idx in indices:
            wd = water_data[idx]
            if wd['std'] < 0.25 and wd['num_points'] >= 3 and -15 < wd['height'] < 8000:
                result['flag'] = 1
                heights.append(wd['height'])
                stds.append(wd['std'])

                raw_x, raw_y = np.array(wd['raw_x_pts']), np.array(wd['raw_y_pts'])
                D = pdist(np.column_stack((raw_x, raw_y)))
                D_mean = np.mean(squareform(D), axis=1)
                min_idx = np.argmin(D_mean)
                xpts.append(raw_x[min_idx])
                ypts.append(raw_y[min_idx])

                doys.append(wd['doy'])
                months.append(wd['month'])
                years.append(wd['year'])

        if result['flag'] == 1:
            heights = np.array(heights)
            stds = np.array(stds)
            xpts = np.array(xpts)
            ypts = np.array(ypts)
            doys = np.array(doys)
            months = np.array(months)
            years = np.array(years)

            ht_std = np.std(heights)
            IP = (heights <= heights.mean() + 3 * ht_std) & (heights >= heights.mean() - 3 * ht_std)

            result['med_height'] = np.median(heights[IP])
            result['mean_height'] = np.mean(heights[IP])
            result['height_range'] = np.max(heights[IP]) - np.min(heights[IP])
            result['std'] = np.mean(stds[IP])

            xp, yp = xpts[IP], ypts[IP]
            if len(xp) > 1:
                D = pdist(np.column_stack((xp, yp)))
                D_mean = np.mean(squareform(D), axis=1)
                min_idx = np.argmin(D_mean)
                result['lon'] = float(xp[min_idx])
                result['lat'] = float(yp[min_idx])
            else:
                result['lon'] = float(xp[0])
                result['lat'] = float(yp[0])

            result['heights'] = heights[IP].tolist()
            result['stds'] = stds[IP].tolist()
            result['doys'] = doys[IP].tolist()
            result['months'] = months[IP].tolist()
            result['years'] = years[IP].tolist()
            result['num_obs'] = len(heights[IP])

            complete_output.append(result)

    # 移除空湖泊 (flag == 0)
    complete_output = [co for co in complete_output if co['flag'] == 1]

    # 加上 MERIT 高程+geoid 偏移
    if complete_output:
        lats = np.array([co['lat'] for co in complete_output])
        lons = np.array([co['lon'] for co in complete_output])
        lons[lons < 0] += 360  # 将负经度转为0-360

        geoidoffsets = geoidheight_batch(lats, lons)

        for i, co in enumerate(complete_output):
            merit = merit_heights[co['mask_id']]
            co['merit_height'] = merit['height'] + geoidoffsets[i]
            co['merit_std'] = merit['std']
            co['geoid_offset'] = geoidoffsets[i]

    return complete_output


def geoidheight_batch(lats, lons, model='egm96'):
    """
    批量计算EGM96大地水准面高度偏移，单位: meters
    这里为了简化，示意用固定值或近似模型代替。你可以替换成真正的geoid模型。
    """
    # 例子：假设全用0（如果你有真实egm96栅格或者pyproj+egm96 geoid，可以在此调用）
    return np.zeros_like(lats)
