# -*- coding: utf-8 -*-

# FOGLAMP_BEGIN
# See: http://foglamp.readthedocs.io/
# FOGLAMP_END

import time
from aiohttp import web
from foglamp import configuration_manager

__author__ = "Amarendra K. Sinha, Ashish Jabble"
__copyright__ = "Copyright (c) 2017 OSIsoft, LLC"
__license__ = "Apache 2.0"
__version__ = "${VERSION}"

__start_time = time.time()

_help = """
    -----------------------------------------------------------------------
    | GET             | /ping                                             |

    | GET             | /categories                                       |
    | GET             | /category/{category_name}                         |
    | GET DELETE      | /category/{category_name}/{config_item}           |
    | PUT             | /category/{category_name}/{config_item}/{value}   |

    -----------------------------------------------------------------------
"""


async def ping(request):
    """

    :param request:
    :return: basic health information json payload
    {'uptime': 32892} Time in seconds since FogLAMP started
    """
    since_started = time.time() - __start_time

    return web.json_response({'uptime': since_started})


#################################
#  Configuration Manager
#################################

async def get_categories(request):
    """

    :param request:
    :return: the list of known categories in the configuration database
    """
    categories = await configuration_manager.get_all_category_names()
    categories_json = [{"key": c[0], "description": c[1]} for c in categories]

    return web.json_response({'categories': categories_json})


async def get_category(request):
    """

    :param request:  category_name is required
    :return: the configuration items in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    category = await configuration_manager.get_category_all_items(category_name)
    # TODO: If category is None from configuration manager. Should we send category
    # as an empty array or error message in JSON format?
    if category is None:
        category = []

    return web.json_response(category)


async def get_category_item(request):
    """

    :param request: category_name & config_item are required
    :return:  the configuration item in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)
    category_item = await configuration_manager.get_category_item(category_name, config_item)
    # TODO: better error handling / info message
    if (category_name is None) or (config_item is None):
        category_item = []

    return web.json_response(category_item)


async def set_configuration_item(request):
    """

    :param request: category_name, config_item are required and value is required only when PUT
    :return: set the configuration item value in the given category.
    """
    category_name = request.match_info.get('category_name', None)
    config_item = request.match_info.get('config_item', None)
    if request.method == 'PUT':
        value = request.match_info.get('value', None)
    elif request.method == 'DELETE':
        value = ''

    await configuration_manager.set_category_item_value_entry(category_name, config_item, value)
    result = await configuration_manager.get_category_item(category_name, config_item)

    return web.json_response(result)


#################################
#  Scheduler Services
#################################


async def get_scheduled_processes(request):
    """Returns the list of all tasks in scheduled_processes table"""
    pass

async def get_scheduled_process(request):
    """Return the task info for the given task from scheduled_processes table"""
    pass

async def post_scheduled_process(request):
    """Create a new task in the scheduled_processes table"""
    pass

async def put_scheduled_process(request):
    """Update a task in the scheduled_processes table"""
    pass

async def delete_scheduled_process(request):
    """Delete a task from scheduled_processes table"""
    pass

async def get_schedules(request):
    """Returns a list of all the defined schedules from schedules table"""
    pass

async def get_schedule(request):
    """Return the information for the given schedule from schedules table"""
    pass

async def post_schedule(request):
    """Create a new schedule in schedules table"""
    pass

async def put_schedule(request):
    """Update a schedule in schedules table"""
    pass

async def delete_schedule(request):
    """Delete a schedule from schedules table"""
    pass

async def get_tasks(request):
    """Returns the list of all known task running or completed from tasks table"""
    pass

async def get_tasks_latest(request):
    """Returns the list of the most recent task execution for each name from tasks table"""
    pass

async def get_task(request):
    """Return the task information for the given task from tasks table"""
    pass

async def post_task(request):
    """ create a new task"""
    pass

async def cancel_task(request):
    """Cancel a running task from tasks table"""
    pass
