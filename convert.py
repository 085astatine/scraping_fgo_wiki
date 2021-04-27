#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import logging
import pathlib
import yaml
import lib


def main() -> None:
    # logger
    logger = logging.getLogger('to_yaml')
    logger.setLevel(logging.INFO)
    logger.addHandler(logging.StreamHandler())
    # option
    argument_parser = argparse.ArgumentParser()
    argument_parser.add_argument(
                '--to',
                dest='to',
                choices=['json', 'yaml'],
                help='output format')
    argument_parser.add_argument(
                '-v', '--verbose',
                dest='verbose',
                action='store_true',
                help='set log level to debug')
    option = argument_parser.parse_args()
    if option.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug('option: %s', option)
    # directory
    root_directory = pathlib.Path(__file__).resolve().parent
    json_directory = root_directory.joinpath('data')
    yaml_directory = root_directory.joinpath('yaml')
    logger.info('root directory: %s', root_directory)
    logger.info('json directory: %s', json_directory)
    logger.info('yaml directory: %s', yaml_directory)
    # convert
    if option.to == 'json':
        to_json(yaml_directory, json_directory, logger)
    if option.to == 'yaml':
        to_yaml(json_directory, yaml_directory, logger)


def to_yaml(
        source_directory: pathlib.Path,
        destination_directory: pathlib.Path,
        logger: logging.Logger) -> None:
    logger.info('to YAML')
    for source in source_directory.glob('**/*.json'):
        # path
        logger.info('source: %s', source)
        destination = (
                destination_directory
                .joinpath(source.relative_to(source_directory))
                .with_suffix('.yaml'))
        logger.info('destination: %s', destination)
        # load
        data = lib.io.load_json(source)
        logger.debug('data: %s', data)
        if data is None:
            continue
        # save
        lib.io.save_yaml(destination, data)


def to_json(
        source_directory: pathlib.Path,
        destination_directory: pathlib.Path,
        logger: logging.Logger) -> None:
    logger.info('to JSON')
    for source in source_directory.glob('**/*.yaml'):
        # path
        logger.info('source: %s', source)
        destination = (
                destination_directory
                .joinpath(source.relative_to(source_directory))
                .with_suffix('.json'))
        logger.info('destination: %s', destination)
        # load
        data = lib.io.load_yaml(source)
        logger.debug('data: %s', data)
        if data is None:
            continue
        # save
        lib.io.save_json(destination, data)


if __name__ == '__main__':
    main()
