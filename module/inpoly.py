import numpy as np
from bisect import bisect_left


def inpoly2(vert, node, edge=None, fTOL=None):
    """
    计算点集与多边形的位置关系（内部/外部/边界）

    参数:
        vert : N×2 numpy数组
            待测试点的XY坐标
        node : M×2 numpy数组
            多边形顶点坐标
        edge : P×2 numpy数组 (可选)
            多边形边索引，默认为顺序连接顶点
        fTOL : float (可选)
            边界判断的浮点容差，默认为 eps^0.85

    返回:
        tuple: (STAT, BNDS)
            STAT : N×1 bool数组，True表示点在多边形内部
            BNDS : N×1 bool数组，True表示点在多边形边界上
    """
    # 设置默认参数
    if edge is None:
        edge = np.vstack([np.arange(len(node)),
                          np.roll(np.arange(len(node)), -1)]).T
    if fTOL is None:
        fTOL = np.finfo(float).eps ** 0.85

    # 输入验证
    if not all(isinstance(arr, np.ndarray) for arr in [vert, node, edge]):
        raise TypeError("输入必须是numpy数组")
    if vert.shape[1] != 2 or node.shape[1] != 2 or edge.shape[1] != 2:
        raise ValueError("输入数组必须是N×2格式")
    if edge.min() < 0 or edge.max() >= len(node):
        raise ValueError("边索引超出节点范围")

    # 初始化输出
    nvrt = len(vert)
    STAT = np.zeros(nvrt, dtype=bool)
    BNDS = np.zeros(nvrt, dtype=bool)

    # 使用边界框快速排除明显在外的点
    nmin, nmax = node.min(0), node.max(0)
    ddxy = nmax - nmin
    lbar = np.sum(ddxy) / 2.0
    veps = fTOL * lbar

    mask = ((vert[:, 0] >= nmin[0] - veps) &
            (vert[:, 0] <= nmax[0] + veps) &
            (vert[:, 1] >= nmin[1] - veps) &
            (vert[:, 1] <= nmax[1] + veps))

    vert_sub = vert[mask]
    if len(vert_sub) == 0:
        return STAT, BNDS

    # 如果x范围大于y范围，交换坐标使y成为长轴
    vmin, vmax = vert_sub.min(0), vert_sub.max(0)
    ddxy = vmax - vmin
    if ddxy[0] > ddxy[1]:
        vert_sub = vert_sub[:, [1, 0]]
        node = node[:, [1, 0]]

    # 按y值排序点
    sort_idx = np.argsort(vert_sub[:, 1])
    vert_sorted = vert_sub[sort_idx]

    # 调用核心算法
    stat, bnds = inpoly2_core(vert_sorted, node, edge, fTOL, lbar)

    # 恢复原始顺序
    stat_reordered = np.zeros_like(stat)
    bnds_reordered = np.zeros_like(bnds)
    stat_reordered[sort_idx] = stat
    bnds_reordered[sort_idx] = bnds

    # 将结果放回完整输出数组
    STAT[mask] = stat_reordered
    BNDS[mask] = bnds_reordered

    return STAT, BNDS


def inpoly2_core(vert, node, edge, fTOL, lbar):
    """
    核心实现 - 基于交叉数算法的点位置判断
    """
    nvrt = len(vert)
    nedg = len(edge)

    stat = np.zeros(nvrt, dtype=bool)
    bnds = np.zeros(nvrt, dtype=bool)

    feps = fTOL * (lbar ** 1)
    veps = fTOL * lbar

    # 预处理边，确保y1 <= y2
    edge_sorted = edge.copy()
    swap_mask = node[edge[:, 1], 1] < node[edge[:, 0], 1]
    edge_sorted[swap_mask, :] = edge_sorted[swap_mask, ::-1]

    # 提取所有y坐标用于二分查找
    y_coords = vert[:, 1]

    # 遍历每条边
    for e in edge_sorted:
        inod, jnod = e
        y1, y2 = node[inod, 1], node[jnod, 1]
        x1, x2 = node[inod, 0], node[jnod, 0]

        # 计算边边界框（带容差）
        xmin = min(x1, x2) - veps
        xmax = max(x1, x2) + veps
        ymin = y1 - veps
        ymax = y2 + veps

        ydel = y2 - y1
        xdel = x2 - x1
        edel = abs(xdel) + ydel

        # 使用二分查找确定y范围内的点
        start_idx = bisect_left(y_coords, ymin)

        # 检查范围内的每个点
        for j in range(start_idx, nvrt):
            if bnds[j]:
                continue

            x, y = vert[j, 0], vert[j, 1]

            if y > ymax:
                break  # 由于已排序，可以提前终止

            if x < xmin:
                # 点在边左侧，可能影响交叉数
                if y1 <= y < y2:
                    stat[j] = not stat[j]
                continue

            if x > xmax:
                continue

            # 计算边与水平线的交点关系
            mul1 = ydel * (x - x1)
            mul2 = xdel * (y - y1)

            # 检查是否在边上（考虑容差）
            if abs(mul2 - mul1) <= feps * edel:
                bnds[j] = True
                stat[j] = True
            elif (y == y1 and x == x1) or (y == y2 and x == x2):
                bnds[j] = True
                stat[j] = True
            elif mul1 < mul2:
                if y1 <= y < y2:
                    stat[j] = not stat[j]

    return stat, bnds