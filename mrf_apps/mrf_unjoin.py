#!/usr/bin/env python3

import argparse
import subprocess
import json
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed


def parse_arguments():
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed command-line arguments.
    """
    parser = argparse.ArgumentParser(description='Unjoins MRF based on parameters.')
    parser.add_argument('-r', '--rows',
                        type=int, required=True, help='Number of rows')
    parser.add_argument('-c', '--columns',
                        type=int, required=True, help='Number of columns')
    parser.add_argument('-i', '--input_file',
                        type=str, required=True, help='Input file name')
    parser.add_argument('-o', '--output_dir',
                        type=str, required=True, help='Output directory')
    parser.add_argument('--resampling',
                        type=str,
                        choices=['Avg', 'NNb', 'None'],
                        default='NNb',
                        help='Overview resampling: Avg, NNb, or None')
    parser.add_argument('-w', '--workers',
                        type=int, default=16,
                        help='Number of parallel processes')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')

    return parser.parse_args()


def process_cell(args, mrf_info, row, col, new_vrt):
    """
    Processes a cell MRF

    Parameters:
    args : argparse.Namespace:
        The arguments required for processing
    mrf_info : object
        MRF metatadata info.
    row : int
        The row index of the cell to be processed.
    col : int
        The column index of the cell to be processed.
    new_vrt : object
        The VRT used to created an empty MRF.

    Returns:
    tuple
        A tuple containing:
        - ouput_file (str): The output file name.
        - execution_time (float): The time taken to process the cell in seconds.
    """

    start_time = time.time()
    prefix = Path(args.input_file).stem
    x_size = mrf_info['size'][0]
    y_size = mrf_info['size'][1]
    x_block = mrf_info['bands'][0]['block'][0]
    y_block = mrf_info['bands'][0]['block'][1]
    bounds = mrf_info['cornerCoordinates']
    geo_x = bounds['upperRight'][0] - bounds['upperLeft'][0]
    geo_y = bounds['upperRight'][1] - bounds['lowerRight'][1]
    geo_x_block = geo_x / args.columns
    geo_y_block = geo_y / args.rows

    if args.verbose:
        print('\n' + str(bounds))
        print(f'x: {x_size}, y: {y_size}, x_block: {x_block}, y_block: {y_block}')
        print(f'x: {geo_x}, y: {geo_y}, geo_x_block: {geo_x_block}, geo_y_block: {geo_y_block}')
        print(f'row: {row}, col:{col}')

    # <ulx> <uly> <lrx> <lry>
    ulx = bounds['upperLeft'][0] + (col * geo_x_block)
    uly = (bounds['lowerLeft'][1] + geo_y_block) + (row * geo_y_block)
    lrx = (bounds['upperLeft'][0] + geo_x_block) + (col * geo_x_block)
    lry = bounds['lowerLeft'][1] + (row * geo_y_block)
    projwin = [ulx, uly, lrx, lry]
    if args.verbose:
        print(projwin)

    # create an empty MRF for inserting new cell VRT
    output_file = args.output_dir + '/' + prefix + '-c' + f'{col:02}' + 'r' + f'{row:02}' + '.mrf'
    print(f'Creating {output_file}\n')
    # delete any existing files
    Path(output_file).unlink(True)
    Path(output_file.replace('.mrf', '.idx')).unlink(True)
    Path(output_file.replace('.mrf', '.ppg')).unlink(True)

    create_mrf = ['gdal_translate', '-q',
                  '-of', 'MRF',
                  '-co', 'COMPRESS=PPNG',
                  '-co', 'BLOCKSIZE=512',
                  '-outsize', str(x_size), str(y_size),
                  '-co', 'NOCOPY=true']
    if args.resampling != 'None':
        create_mrf.append('-co',)
        create_mrf.append('UNIFORM_SCALE=2')
    create_mrf.append(new_vrt)
    create_mrf.append(output_file)

    if args.verbose:
        print(' '.join(create_mrf))
    subprocess.run(create_mrf)
    if args.verbose:
        print(f'Cell MRF created {output_file}')

    # create cell VRT with the selected window
    output_vrt = args.output_dir + '/' + prefix + '-c' + f'{col:02}' + 'r' + f'{row:02}' + '.vrt'
    Path(output_vrt).unlink(True)
    create_vrt = ['gdal_translate', '-q',
                  '-of', 'VRT',
                  '-projwin', str(ulx), str(uly), str(lrx), str(lry),
                  '-co', 'BLOCKSIZE=512',
                  args.input_file,
                  output_vrt]
    if args.verbose:
        print(' '.join(create_vrt))
    subprocess.run(create_vrt)
    if args.verbose:
        print(f'Cell VRT created {output_vrt}')

    # insert cell VRT into the MRF
    mrf_insert = ['mrf_insert']
    if args.resampling != 'None':
        mrf_insert.append('-r')
        mrf_insert.append(args.resampling)
    mrf_insert.append(output_vrt)
    mrf_insert.append(output_file)
    if args.verbose:
        print(' '.join(mrf_insert))
    subprocess.run(mrf_insert)
    if args.verbose:
        print(f'Data inserted into {output_file}')

    end_time = time.time()
    execution_time = end_time - start_time
    return output_file, execution_time


def main():
    """
    Main function that executes unjoin processes.
    """
    start_time = time.time()
    args = parse_arguments()
    print('Getting info for', args.input_file)
    prefix = Path(args.input_file).stem

    # Get size of MRF
    gdalinfo_command_list = ['gdalinfo', '-json', args.input_file]
    if args.verbose:
        print(' '.join(gdalinfo_command_list))
    gdalinfo = subprocess.Popen(gdalinfo_command_list,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    mrf_info = ''
    try:
        outs, errs_warns = gdalinfo.communicate(timeout=90)
        errs_warns = str(errs_warns, encoding='utf-8')
        # Split up any errors and warnings, log them each appropriately
        errs = []
        warns = []
        for message in errs_warns.split('\n'):
            if len(message) > 0:
                if message.lower().startswith("error"):
                    errs.append(message)
                else:
                    warns.append(message)
        if len(errs) > 0:
            print('gdalinfo errors: {0}'.format('\n'.join(errs)))
        if len(warns) > 0:
            print('gdalinfo warnings: {0}'.format('\n'.join(warns)))
        mrf_info = json.loads(outs)
    except subprocess.TimeoutExpired:
        gdalinfo.kill()
        print('gdalinfo timed out')

    if mrf_info == '':
        print('MRF is not valid.')
        exit()

    # create a VRT based on the input MRF to later create a blank cell MRF
    new_vrt = args.output_dir + '/' + prefix + '.vrt'
    create_vrt = ['gdal_translate',
                  '-of', 'VRT',
                  args.input_file,
                  new_vrt]
    if args.verbose:
        print(' '.join(create_vrt))
    subprocess.run(create_vrt)

    # Remove the source from the VRT to avoid referencing the original MRF
    tree = ET.parse(new_vrt)
    band = tree.getroot().find('VRTRasterBand')
    band.remove(band.find('SimpleSource'))
    tree.write(new_vrt, encoding='utf-8', xml_declaration=True)
    print(f'VRT created {new_vrt}')

    # Process each cell in parallel
    with ThreadPoolExecutor(max_workers=int(args.workers)) as executor:
        futures = []
        for row in reversed(range(args.rows)):
            for col in range(args.columns):
                futures.append(executor.submit(process_cell,
                                               args, mrf_info, row, col,
                                               new_vrt))

        for future in as_completed(futures):
            result, execution_time = future.result()
            print(f'Processed {result} in {str(timedelta(seconds=execution_time))} \n')

    end_time = time.time()
    run_time = end_time - start_time
    print(f'mrf_unjoin completed in {str(timedelta(seconds=run_time))}')


if __name__ == '__main__':
    main()
