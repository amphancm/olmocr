import importlib.util
import logging
import subprocess
import sys
import torch

logger = logging.getLogger(__name__)


def check_poppler_version():
    try:
        result = subprocess.run(["pdftoppm", "-h"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0 and result.stderr.startswith("pdftoppm"):
            logger.info("pdftoppm is installed and working.")
        else:
            logger.error("pdftoppm is installed but returned an error.")
            sys.exit(1)
    except FileNotFoundError:
        logger.error("pdftoppm is not installed.")
        logger.error("Check the README in the https://github.com/allenai/olmocr/blob/main/README.md for installation instructions")
        sys.exit(1)


def check_sglang_version():
    if importlib.util.find_spec("sglang") is None:
        logger.error("Please make sure sglang is installed according to the latest instructions here: https://docs.sglang.ai/start/install.html")
        logger.error("Sglang needs to be installed with a separate command in order to find all dependencies properly.")
        sys.exit(1)


# def check_torch_gpu_available(min_gpu_memory: int = 15 * 1024**3):
#     try:
#         import torch
#     except:
#         logger.error("Pytorch must be installed, visit https://pytorch.org/ for installation instructions")
#         raise

#     try:
#         gpu_memory = torch.cuda.get_device_properties(0).total_memory
#         assert gpu_memory >= min_gpu_memory
#     except:
#         logger.error(f"Torch was not able to find a GPU with at least {min_gpu_memory // (1024 ** 3)} GB of RAM.")
#         raise


def check_torch_gpu_available(min_gpu_memory=24):
    """
    Check if CUDA GPUs are available and have sufficient memory.
    This patched version sums memory across all GPUs (for multi-GPU systems).
    """

    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU not available")

    num_gpus = torch.cuda.device_count()
    total_memory = 0

    print(f"Detected {num_gpus} GPU(s).")

    for i in range(num_gpus):
        props = torch.cuda.get_device_properties(i)
        mem_gb = props.total_memory / 1e9
        total_memory += mem_gb
        print(f" - GPU {i}: {props.name} with {mem_gb:.1f} GB")

    print(f"Total GPU memory across {num_gpus} GPUs: {total_memory:.1f} GB")

    if total_memory < min_gpu_memory:
        print(
            f"WARNING: Only {total_memory:.1f} GB available, "
            f"but {min_gpu_memory} GB is recommended. Continuing anyway..."
        )


if __name__ == "__main__":
    check_poppler_version()
    check_sglang_version()
