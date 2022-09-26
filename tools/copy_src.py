# Name: copy_src
# Date: 2022-09-25
# Author: Ais
# Desc: 复制源码


import os
import json
import shutil
import argparse


# 复制源码
def copy_src(src_dir, dst_dir="./src", index_path="./index.json", ALL=False):
    """
    @func: 根据索引文件复制源码
    @params: 
        * src_dir(str:path): 源码目录 
        * dst_dir(str:path): 输输出目录
        * index_path(str:path): 索引文件目录 
            exp -> 
            [
                "/templates",
                "/cmdline.py",
                "/commands/__init__.py",
                "/commands/startproject.py"
            ]
        * ALL(bool): 复制完整源码
    """
    index = []
    if ALL:
        # 复制完整源码
        index = [src_dir]
    else:
        # 根据索引文件复制源码
        if not os.path.exists(index_path):
            raise Exception(f"index({index_path}) is not exists")
        else:
            with open(index_path, "r") as f:
                index = json.loads(f.read())
    # 复制源码
    for fp in index:
        src_fp, dst_fp = f"{src_dir}{fp}", f"{dst_dir}{fp}"
        # 复制文件
        if os.path.isfile(src_fp):
            _dir, _ = os.path.split(dst_fp)
            not os.path.exists(_dir) and os.makedirs(_dir)
            shutil.copy(src_fp, dst_fp)    
        # 复制目录 
        else:
            shutil.copytree(src_fp, dst_fp)


if __name__ ==  "__main__":
    
    # 构建命令行解析器
    parser = argparse.ArgumentParser(description="copy_src")
    # 添加命令行参数
    parser.add_argument("-i", "--index", type=str, default="./index.json", help="索引文件路径")
    parser.add_argument("-o", "--out", type=str, default="./src", help="导出目录")
    parser.add_argument("-a", "--ALL", action="store_true", help="复制所有源码")
    # 解析参数
    args = parser.parse_args()
    # 执行
    copy_src(
        src_dir = "D:/AisPrograms/anaconda/envs/Rscrapy/Lib/site-packages/scrapy/",
        dst_dir = args.out,
        index_path = args.index,
        ALL = args.ALL
    )