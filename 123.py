import numpy as np
from module import inpoly



poly = np.array([[0,0],[0,1],[1,1],[1,0],[0,0]])
# 测试点
pts = np.array([[0.5,0.5], [1.0,1.0], [1.5,1.5]])

print(inpoly.inpoly2(pts, poly))
# 应该返回 [1, 1, 0]
