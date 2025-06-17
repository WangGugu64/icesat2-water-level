def get_mask_metadata_func_nov20(name):
    """解析文件名中的经纬度信息，生成用于命名的字符串"""

    mask_metadata = {'name': name}

    echeck = name.find('0E_')
    if echeck != -1:
        mask_metadata['ew'] = 'E'
        if echeck == 11:
            mask_metadata['lon'] = int(name[echeck])
            mask_metadata['lonstr'] = '00' + name[echeck]
        elif echeck == 12:
            mask_metadata['lon'] = int(name[echeck-1:echeck+1])
            mask_metadata['lonstr'] = '0' + name[echeck-1:echeck+1]
        elif echeck == 13:
            mask_metadata['lon'] = int(name[echeck-2:echeck+1])
            mask_metadata['lonstr'] = name[echeck-2:echeck+1]
        nstart = echeck
    else:
        wcheck = name.find('0W_')
        if wcheck != -1:
            mask_metadata['ew'] = 'W'
            if wcheck == 11:
                mask_metadata['lon'] = int(name[wcheck])
                mask_metadata['lonstr'] = '00' + name[wcheck]
            elif wcheck == 12:
                mask_metadata['lon'] = int(name[wcheck-1:wcheck+1])
                mask_metadata['lonstr'] = '0' + name[wcheck-1:wcheck+1]
            elif wcheck == 13:
                mask_metadata['lon'] = int(name[wcheck-2:wcheck+1])
                mask_metadata['lonstr'] = name[wcheck-2:wcheck+1]
            nstart = wcheck
        else:
            nstart = None  # 如果都没找到，防止后续报错

    if nstart is not None:
        name_s = name[nstart:]
        ncheck = name_s.find('Nv')
        if ncheck != -1:
            mask_metadata['ns'] = 'N'
            if ncheck == 4:
                mask_metadata['lat'] = int(name_s[ncheck-1])
                mask_metadata['latstr'] = '0' + name_s[ncheck-1]
            elif ncheck == 5:
                mask_metadata['lat'] = int(name_s[ncheck-2:ncheck])
                mask_metadata['latstr'] = name_s[ncheck-2:ncheck]

        scheck = name_s.find('Sv')
        if scheck != -1:
            mask_metadata['ns'] = 'S'
            if scheck == 4:
                mask_metadata['lat'] = int(name_s[scheck-1])
                mask_metadata['latstr'] = '0' + name_s[scheck-1]
            elif scheck == 5:
                mask_metadata['lat'] = int(name_s[scheck-2:scheck])
                mask_metadata['latstr'] = name_s[scheck-2:scheck]

    return mask_metadata
