#!/usr/bin/env python3.4
# -*- coding: utf-8 -*-
"""
==================================================
 Script for automated for putting into production
==================================================
:Author: Charles Levesque
:Date: 19/04/14
:Version: 1.0.0
Description::
    This script is used to deploy a directory or a file to a specified server
    via Secure Shell in a specified directory. Finally, it will restart Apache HTTPD Server
    on the distant server.

Attributes
==========
:Attribute local-path or l: The path to the file or directory to send.
:Attribute server or s: The name or ip address of the server.
:Attribute server-path or d: The path on the server to store the content.
:Attribute restart-apache or a: Restart or not Apache HTTPD Server
"""
import colorama
import os
import sys
import tarfile
import subprocess
import time
import pathlib
from fabric.api import local
from subprocess import Popen, call
from getopt import getopt
from pathlib import Path
from enum import Enum


class MessageTypes(Enum):
    """
    :Summary: This is an enum class for message types.
    """
    SUCCESS = 0
    ERROR = 1
    RESET = 2
class ExitCodes(Enum):
    """
    :Summary: This is an enum class for exit codes.
    """
    SUCCESS = 0
    IO_ERROR = 1
    ATTRIBUTE_ERROR = 2
    GENERAL = 3

ATTRIBUTE_CODE = 0
ARGUMENT_CODE = 1
OPTIONS_LIST_MAX = 4
OPTIONS_LIST_MIN = 3
UTF_8 = "UTF-8"
ERROR_COLORS = colorama.Fore.RED + colorama.Back.BLACK
SUCCESS_COLORS = colorama.Fore.GREEN + colorama.Back.BLACK
RESET_COLORS = colorama.Fore.WHITE + colorama.Back.BLACK


def main(argv: list=sys.argv) -> int:
    """
    :Summary: Main function of the script.

    :Type argv: `[str]`
    :Parameter argv: The list of arguments passed to the script.
    :Raises AttributeError: This is raised when an argument passed doesn't have
    a the right type.
    :ReturnType: `int`
    :Returns: An error code.
    """
    __print_message("Beginning the script...")
    try:
        __print_message("Retreiving attributes...")
        options_list, arguments = getopt(argv[1:], shortopts='l:s:u:p:d:a',
                                         longopts=[
                                             'local-path=',
                                             'server=',
                                             'server-path=',
                                             'restart-apache'
                                         ])
        __print_message("Validating the attributes...")
        if len(options_list) < OPTIONS_LIST_MIN\
            or len(options_list) > OPTIONS_LIST_MAX:
            raise AttributeError("There is not enough or too many arguments passed.")

        if not __is_attributes_valid([option[ATTRIBUTE_CODE] for option in options_list]):
            raise AttributeError("Missing one or many attributes in the call.")
        __print_message("OK!", MessageTypes.SUCCESS)

        attr_args_mapping = {option[ATTRIBUTE_CODE]: option[ARGUMENT_CODE]\
                             for option in options_list}

        local_path = Path(attr_args_mapping['--local-path']\
                              if '--local-path' in attr_args_mapping.keys()\
                              else attr_args_mapping['-l'])
        if not local_path.exists():
            raise IOError("The path to the local file doesn't exits.")

        compressed_file_path = __compress_local_file(local_path)

        server_path = attr_args_mapping['--server-path']\
            if '--server-path' in attr_args_mapping.keys()\
            else attr_args_mapping['-d']
        server_name = attr_args_mapping['--server']\
            if '--server' in attr_args_mapping.keys()\
            else attr_args_mapping['-s']

        __print_message("Copying local file to server...")
        call(['scp', compressed_file_path, "{server_name}:{server_path}".format(
            server_name=server_name,
            server_path=server_path
        )])
        __print_message("OK!", MessageTypes.SUCCESS)

        __ssh_processing(
            compressed_file_path.split("/")[-1:][0],  # Gets the string after the last slash
            server_name,
            server_path,
            '--restart-apache' in attr_args_mapping.keys()
        )

        os.remove(str(compressed_file_path))
        __print_message("New MEP done!", MessageTypes.SUCCESS)
        return ExitCodes.SUCCESS
    except IOError as io_error:
        __print_message(io_error, MessageTypes.ERROR)
        return ExitCodes.IO_ERROR
    except AttributeError as attribute_error:
        __print_message(attribute_error, MessageTypes.ERROR)
        return ExitCodes.ATTRIBUTE_ERROR
    except Exception as ex:
        __print_message(ex, MessageTypes.ERROR)
        print(ERROR_COLORS + ex)
        return ExitCodes.GENERAL


def __is_attributes_valid(attributes: [str]) -> bool:
    """
    :Summary: This function validates the necessary attributes passed to
    the script. If one is missing, `False` is returned.

    :Type attributes: `[str]`
    :Parameter attributes: The list of the attributes passed to the script.

    :ReturnType: `bool`
    :Returns: `True` if all attributes are there, `False` otherwise.
    """
    long_attribute_code, short_attribute_code = 0, 1
    attributes_mapping = {
        'local_path': ('local-path', 'l'),
        'server': ('server', 's'),
        'server_path': ('server-path', 'd'),
        'restart_apache': ('restart-apache', 'a')
    }
    validation = [False for item in attributes]

    for attribute in attributes:
        if attributes_mapping['local_path'][long_attribute_code] in attribute\
            or attributes_mapping['local_path'][short_attribute_code] in attribute:
            validation[0] = True
        elif attributes_mapping['server'][long_attribute_code] in attribute\
            or attributes_mapping['server'][short_attribute_code] in attribute:
            validation[1] = True
        elif attributes_mapping['server_path'][long_attribute_code] in attribute\
            or attributes_mapping['server_path'][short_attribute_code] in attribute:
            validation[2] = True

        if len(attributes) == OPTIONS_LIST_MAX:
            if attributes_mapping['restart_apache'][long_attribute_code] in attribute\
                or attributes_mapping['restart_apache'][short_attribute_code] in attribute:
                validation[3] = True

    return all(is_valid_attribute for is_valid_attribute in validation)


def __compress_local_file(local_path: pathlib.PurePath) -> str:
    """
    :Summary: This function compressed a file in Bzip2 from the given path.

    :Type local_file: `PurePath`
    :Parameter local_file: A `PurePath` object containing the path to the file or
    directory to compress.
    :ReturnType: `str`
    :Returns: The path of the file compressed.
    """
    tar_file_path = str(local_path.parent/"compressed_file.tar.bz2")

    if local_path.is_dir(): __print_message("Compressing the directory...")
    else: __print_message("Compressing the file...")

    open(tar_file_path, mode="w").close()  # Creates a file
    with tarfile.open(tar_file_path, mode="w|bz2") as tar_file:
        tar_file.add(str(local_path), arcname="compressed_file")
    __print_message("OK!", MessageTypes.SUCCESS)

    return tar_file_path


def __ssh_processing(
        compressed_file_name: str,
        server_name: str,
        server_path: str,
        restart_apache: bool=False) -> None:
    """
    :Summary: This function processes all the processing done to the server
    to do the MEP.

    :Type compressed_file_name: `str`
    :Parameter compressed_file_name: Name of the compressed local file.
    :Type server_name: `str`
    :Parameter server_name: The name or IP address of the server.
    :Type server_path: `str`
    :Parameter server_path: The path on the server where is the file.
    """
    archive_name = time.strftime("%d_%m_%y") + ".tar.bz2"
    new_folder_name = compressed_file_name[:-8]

    __print_message("Connecting to the server")
    with Popen(["ssh", server_name], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as ssh_pipe:
        __print_message("OK!", MessageTypes.SUCCESS)

        __print_message("Archiving the old API...")
        ssh_pipe.stdin.write("cd {server_path}\n"\
                             .format(server_path=server_path)\
                             .encode(UTF_8))
        ssh_pipe.stdin.write("tar -cjf {archive_name} backend/\n"\
                             .format(archive_name=archive_name)\
                             .encode(UTF_8))
        ssh_pipe.stdin.write("mv ./{archive_name} ./archive\n"\
                             .format(archive_name=archive_name)\
                             .encode(UTF_8))
        ssh_pipe.stdin.write("rm -r ./backend\n"\
                             .encode(UTF_8))
        __print_message("OK!", MessageTypes.SUCCESS)

        __print_message("Updating the backend...")
        ssh_pipe.stdin.write("tar jxf ./{compressed_file_name}\n"\
                             .format(compressed_file_name=compressed_file_name)\
                             .encode(UTF_8))
        ssh_pipe.stdin.write("rm ./{compressed_file_name}\n"\
                             .format(compressed_file_name=compressed_file_name)\
                             .encode(UTF_8))
        ssh_pipe.stdin.write("mv ./{new_folder_name} backend\n"\
                             .format(new_folder_name=new_folder_name)\
                             .encode(UTF_8))
        __print_message("OK!", MessageTypes.SUCCESS)

        if restart_apache:
            __print_message("Restarting Apache...")
            ssh_pipe.stdin.write("systemctl restart httpd\n"\
                                 .encode(UTF_8))
            __print_message("OK!", MessageTypes.SUCCESS)
        ssh_pipe.stdin.flush()


def __print_message(message: str, type: MessageTypes=MessageTypes.RESET) -> None:
    """
    :Summary: This function prints an error message with the proper colors.

    :Type message: `str`
    :Parameter message: The message to print.
    :Type type: `MessageTypes`
    :Parameter type: The type of the message.
    :Default type: `MessageTypes.RESET`
    """
    if type is MessageTypes.RESET:
        print(RESET_COLORS, message)
    elif type is MessageTypes.ERROR:
        print(ERROR_COLORS, message)
    elif type is MessageTypes.SUCCESS:
        print(SUCCESS_COLORS, message, "\n")


if __name__ == '__main__':
    colorama.init(autoreset=True)
    exit_code = main()

    if exit_code.value == 0: __print_message("Exited without errors.", MessageTypes.SUCCESS)
    else: __print_message("Exited with user error.", MessageTypes.ERROR)

    sys.exit()


__author__ = 'Charles Levesque'
__copyright__ = u'Tous droits réservés 2014, Le Club ApplETS'
__credits__ = ['Philippe Cloutier']
__date__ = '19/04/14'

__version__ = '1.0.0'
__maintainer__ = 'The server maintainer'
__email__ = 'clubapplets@googlegroups.com'
__status__ = 'Development'