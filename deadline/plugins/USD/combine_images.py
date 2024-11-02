import subprocess
import argparse
import os
import re

OIIO = os.getenv("OIIO", "hoiiotool")


def merge_images(output_file, *input_images, delete=False):
    """
    Merges a list of input images into a single output image.

    Args:
        output_file (str): The path to the output image.
        input_images (list): A list of the input images.
        delete (bool): delete the original images

    """
    # if not OIIO or os.path.exists(OIIO):
    #     print("ERROR: Cannot file OIIO at {}".format(OIIO))
    #     return
    print("os.path.exists(OIIO)", os.path.exists(OIIO), )

    if not os.path.isdir(os.path.dirname(output_file)):
        os.makedirs(os.path.dirname(output_file))

    for input_image in input_images:
        try:
            args = [OIIO]
            args.append('-a')
            args.append('--add')  #--deep-copy
            args.append(input_image)
            if os.path.isfile(output_file):
                args.append(output_file)
            args.extend(['-o', output_file])

            print("Merging: {}".format(args))
            process = subprocess.Popen(args)
            process.wait()

            if delete:
                os.remove(input_image)
        except Exception as e:
            print("ERROR: `{}` for `{}`".format(e, input_image))


def group_files(file_list):
    """
    Groups files in the list by the common part of the name.

    Args:
        file_list (list): The list of files.

    Returns:
        dict: A dictionary of file groups.
    """

    file_groups = {}

    for file in file_list:
        pattern = re.split(r'_tile\d+\.', file)
        if len(pattern) >= 2:
            if pattern[0] not in file_groups:
                file_groups[pattern[0]] = []

            file_groups[pattern[0]].append(file)

    return file_groups


def combin_images(root_dir, delete=False):
    grps = group_files(os.listdir(root_dir))
    for grp in grps:
        files = grps[grp]
        output_file = os.path.join(root_dir, "Combine", grp + "." + files[0].rsplit('.', 1)[-1])
        files = [os.path.join(root_dir, x) for x in files]
        merge_images(output_file, *files, delete=delete)


def main():
    parser = argparse.ArgumentParser(description="To combine separate tiles images.")

    parser.add_argument("-r", "--root", type=str, help="The root path where images are located")
    parser.add_argument("-a", "--add", nargs=2, type=str, help="Add 2 images together")
    parser.add_argument("-d", "--delete", action="store_true", help="delete tile after combining")

    args = parser.parse_args()

    if args.root:
        combin_images(args.root, delete=args.delete)

    if args.add:
        tile_image, final_image = args.add
        merge_images(final_image, tile_image, delete=args.delete)


main()
