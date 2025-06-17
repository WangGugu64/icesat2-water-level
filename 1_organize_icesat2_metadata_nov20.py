import os
import glob
import h5py
import pickle
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

def extract_metadata(file_path):
    """提取单个 HDF5 文件的元数据"""
    try:
        with h5py.File(file_path, 'r') as f:
            lon_min = f.attrs['geospatial_lon_min']
            lon_max = f.attrs['geospatial_lon_max']
            lat_min = f.attrs['geospatial_lat_min']
            lat_max = f.attrs['geospatial_lat_max']
            start_time = f.attrs['time_coverage_start']
            if isinstance(start_time, bytes):
                start_time = start_time.decode()

            laser_names = [group for group in f.keys() if 'gt' in group]
            laser_out = [{'Name': name} for name in laser_names]

        meta = {
            'filename': os.path.basename(file_path),
            'lon_min': lon_min,
            'lon_max': lon_max,
            'lat_min': lat_min,
            'lat_max': lat_max,
            'year': int(start_time[0:4]),
            'month': int(start_time[5:7]),
            'day': int(start_time[8:10]),
            'lasers': laser_out
        }

        return meta, None  # 返回元数据和无错误

    except Exception as e:
        return None, f"Error reading file: {os.path.basename(file_path)} - {str(e)}"

def batch_extract_metadata(input_folder, output_path, max_workers=8):
    """批量提取 HDF5 文件元数据，多线程并行处理"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 搜索符合条件的文件
    files = [os.path.join(input_folder, f) for f in glob.glob(os.path.join(input_folder, "*.h5"))
             if os.path.getsize(os.path.join(input_folder, f)) >= 10000]

    metadata = []
    errors = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {executor.submit(extract_metadata, file_path): file_path for file_path in files}

        for count, future in enumerate(as_completed(future_to_file), 1):
            result, error = future.result()
            if result:
                metadata.append(result)
            if error:
                errors.append(error)
            print(f"Finished {count} of {len(files)}")

    # 保存元数据
    with open(output_path, 'wb') as f:
        pickle.dump(metadata, f)

    # 写入错误日志
    if errors:
        log_path = os.path.splitext(output_path)[0] + '_error.log'
        with open(log_path, 'w') as log_file:
            log_file.write(f"Metadata extraction errors ({datetime.now()}):\n")
            for err in errors:
                log_file.write(err + '\n')

    print("Batch metadata extraction complete.")
    print(f"Metadata saved to: {output_path}")
    if errors:
        print(f"Errors logged to: {log_path}")

# 使用方法
if __name__ == "__main__":
    input_folder = r"F:\ATL08_006-20250418_031619"
    output_path = r"D:\Code\icesat2-water-levels-main\icesat2-water-levels-main\ICESat_2_metadata\atl_metadata_optimized.pkl"
    batch_extract_metadata(input_folder, output_path, max_workers=8)
