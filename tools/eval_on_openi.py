#!/usr/bin/env python
"""Perform evaluation on OpenI
"""
import argparse
import os
import subprocess
import sys

try:
    import moxing as mox
except ImportError as e:
    raise ValueError("This script aims to run on the OpenI platform.") from e

from common.config import create_parser, merge_args, parse_args


def install_packages(project_dir: str) -> None:
    url = "https://pypi.tuna.tsinghua.edu.cn/simple"
    requirement_txt = os.path.join(project_dir, "requirements.txt")
    subprocess.check_call(
        [sys.executable, "-m", "pip", "install", "-i", url, "-r", requirement_txt]
    )


def download_data(s3_path: str, dest: str) -> None:
    if not os.path.isdir(dest):
        os.makedirs(dest)

    mox.file.copy_parallel(src_url=s3_path, dst_url=dest)

    print(f"Data directory: {os.listdir(dest)}")


def download_ckpt(s3_path: str, dest: str) -> str:
    if not os.path.isdir(dest):
        os.makedirs(dest)

    filename = os.path.basename(s3_path)
    dst_url = os.path.join(dest, filename)

    mox.file.copy(src_url=s3_path, dst_url=dst_url)
    return dst_url


def upload_data(src: str, s3_path: str) -> None:
    mox.file.copy_parallel(src_url=src, dst_url=s3_path)


def parse_openi_args() -> argparse.Namespace:
    parser = create_parser(description="OpenI extra arguments")
    # add arguments
    # the follow arguments are proviced by OpenI, do not change.
    parser.add_argument("--device_target", help="Device target")
    parser.add_argument("--data_url", help="Path of the data url in S3")
    parser.add_argument("--result_url", help="Path of the evaluaton output in S3")
    parser.add_argument("--ckpt_url", help="Path of the ckpt in S3")
    # dummy input
    parser.add_argument("--train_url", help="Path of the training output in S3")
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    print(os.environ)

    # locate the path of the project
    project_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    # install necessary packages
    install_packages(project_dir)

    from eval import eval

    args = parse_args(project_dir, description="Evaluation script")
    openi_args = parse_openi_args()
    args = merge_args(args, openi_args)

    # copy data from S3 to local
    download_data(s3_path=args.data_url, dest="data/")

    # copy ckpt from S3 to local
    ckpt_path = download_ckpt(s3_path=args.ckpt_url, dest="ckpt/")
    args.ckpt = ckpt_path

    # start traning job
    try:
        eval(args)
    except Exception:
        raise
    finally:
        # copy output from local to s3
        upload_data(src=args.outdir, s3_path=args.result_url)
